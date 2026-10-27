import json
import logging
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import urlencode
from uuid import UUID

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from . import flutterwave
from .flutterwave import FlutterwaveError
from .forms import ReviewForm
from .models import Review, TransferOrder
from .payouts import destination_currency, payout_options
from .transfer_forms import CURRENCY_CHOICES, TransferStartForm


logger = logging.getLogger(__name__)
SUPPORTED_CURRENCIES = {currency for currency, _ in CURRENCY_CHOICES}
ZERO_DECIMAL_CURRENCIES = {"XAF", "XOF", "UGX", "RWF"}
MOBILE_NETWORKS = {
    "CI": {
        "FMM": "FMM", "MOOV": "Moov", "ORANGEMONEY": "orangemoney", "WAVE": "WAVE",
    },
    "EG": {"EGPWALLETS": "EGPWALLETS"},
    "GH": {
        "AIRTELTIGO": "AIRTELTIGO", "MTN": "MTN", "TELECEL": "TELECEL",
        "VODAFONE": "VODAFONE",
    },
    "KE": {
        "SAFARICOM": "SAFARICOM", "T-KASH": "T-Kash", "AIRTEL": "Airtel", "MPS": "MPS",
    },
    "RW": {"MPS": "MPS", "MTN": "MTN"},
    "SN": {
        "FREEMONEY": "freemoney", "ORANGEMONEY": "orangemoney", "WAVE": "WAVE",
    },
    "UG": {"AIRTEL": "Airtel", "MPS": "MPS", "MTN": "MTN"},
}


def _rounded(value, currency):
    precision = Decimal("1") if currency in ZERO_DECIMAL_CURRENCIES else Decimal("0.01")
    return value.quantize(precision, rounding=ROUND_HALF_UP)


def _quote(source_currency, destination_currency_code, source_amount):
    if source_currency == destination_currency_code:
        return {
            "rate": Decimal("1"),
            "destination_amount": _rounded(source_amount, destination_currency_code),
        }

    cache_key = f"flw-rate:{source_currency}:{destination_currency_code}"
    rate = cache.get(cache_key)
    if rate is None:
        result = flutterwave.quote(
            source_currency,
            destination_currency_code,
            destination_amount="1",
        )
        rate = result["rate"]
        cache.set(cache_key, rate, 30)

    destination_amount = _rounded(source_amount * rate, destination_currency_code)
    if destination_amount <= 0:
        raise FlutterwaveError("Montant trop faible pour cette devise de réception.")
    return {"rate": rate, "destination_amount": destination_amount}


def _valid_currency_pair(source_currency, destination_currency_code):
    return (
        source_currency in SUPPORTED_CURRENCIES
        and destination_currency_code in SUPPORTED_CURRENCIES
    )


def home(request):
    form = ReviewForm()
    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Merci ! Votre avis a bien été publié.")
            return redirect("home")

    transfer_order = None
    transfer_reference = request.GET.get("transfer")
    if transfer_reference:
        try:
            reference = UUID(transfer_reference)
        except ValueError:
            reference = None
        if reference:
            transfer_order = TransferOrder.objects.filter(reference=reference).first()

    context = {
        "form": form,
        "reviews": Review.objects.all()[:50],
        "payout_options": payout_options(),
        "currency_choices": CURRENCY_CHOICES,
        "transfer_order": transfer_order,
        "flutterwave_configured": bool(
            settings.FLW_TRANSFERS_ENABLED
            and settings.FLW_SECRET_KEY
            and settings.FLW_DATA_ENCRYPTION_KEY
            and settings.FLW_WEBHOOK_SECRET_HASH
        ),
    }
    response_status = 400 if request.method == "POST" else 200
    return render(request, "reviews/home.html", context, status=response_status)


@require_GET
def transfer_quote(request):
    source_currency = request.GET.get("from", "").upper()
    destination_currency_code = request.GET.get("to", "").upper()
    amount_text = request.GET.get("amount", "")

    if not _valid_currency_pair(source_currency, destination_currency_code):
        return JsonResponse({"error": "Sélectionnez deux devises prises en charge."}, status=400)
    try:
        amount = Decimal(amount_text)
    except InvalidOperation:
        return JsonResponse({"error": "Montant invalide."}, status=400)
    if not amount.is_finite() or amount <= 0 or amount > Decimal("10000000"):
        return JsonResponse({"error": "Le montant doit être supérieur à zéro."}, status=400)

    try:
        result = _quote(source_currency, destination_currency_code, amount)
    except FlutterwaveError as exc:
        status = 503 if not settings.FLW_SECRET_KEY else 502
        return JsonResponse({"error": str(exc)}, status=status)

    return JsonResponse(
        {
            "source_currency": source_currency,
            "destination_currency": destination_currency_code,
            "source_amount": format(amount, "f"),
            "destination_amount": format(result["destination_amount"], "f"),
            "rate": format(result["rate"], "f"),
            "indicative": True,
            "note": "Taux indicatif Flutterwave, hors frais. Le taux final est confirmé au paiement.",
        }
    )


@require_POST
def start_transfer(request):
    form = TransferStartForm(request.POST)
    if not form.is_valid():
        return JsonResponse(
            {"error": "Vérifiez les informations saisies.", "errors": form.errors},
            status=400,
        )
    if not settings.FLW_TRANSFERS_ENABLED:
        return JsonResponse(
            {"error": "Les transferts restent désactivés tant que l’intégration n’a pas été testée."},
            status=503,
        )
    if not settings.FLW_SECRET_KEY or not settings.FLW_DATA_ENCRYPTION_KEY:
        return JsonResponse(
            {
                "error": (
                    "Le paiement n’est pas encore configuré. "
                    "Les clés Flutterwave doivent être installées côté serveur."
                )
            },
            status=503,
        )
    if not settings.FLW_WEBHOOK_SECRET_HASH:
        return JsonResponse(
            {"error": "Le secret de signature du webhook Flutterwave n’est pas configuré."},
            status=503,
        )

    data = form.cleaned_data
    country = data["country"]
    payout_method = data["payout_method"]
    destination_currency_code = data["destination_currency"]
    source_currency = data["source_currency"]
    if payout_method == "mobile":
        network = MOBILE_NETWORKS.get(country, {}).get(data["bank_code"].strip().upper())
        if not network:
            return JsonResponse(
                {"error": "Ce réseau Mobile Money n’est pas documenté pour ce pays."},
                status=400,
            )
    else:
        network = data["bank_code"].strip()

    try:
        quote = _quote(source_currency, destination_currency_code, data["amount"])
    except FlutterwaveError as exc:
        return JsonResponse({"error": str(exc)}, status=502)

    recipient_data = {
        "beneficiary_name": data["beneficiary_name"].strip(),
        "first_name": data["first_name"].strip(),
        "last_name": data["last_name"].strip(),
        "beneficiary_merchant_name": data["beneficiary_merchant_name"].strip(),
        "account_number": data["account_number"].strip(),
        "account_bank": network,
        "bank_name": data["bank_name"].strip(),
        "swift_code": data["swift_code"].strip(),
        "routing_number": data["routing_number"].strip(),
        "account_type": data["account_type"],
        "city": data["city"].strip(),
        "postal_code": data["postal_code"].strip(),
        "street_name": data["street_name"].strip(),
        "street_number": data["street_number"].strip(),
        "beneficiary_address": data["beneficiary_address"].strip(),
    }
    order = TransferOrder.objects.create(
        source_amount=data["amount"],
        source_currency=source_currency,
        destination_amount=quote["destination_amount"],
        destination_currency=destination_currency_code,
        destination_country=country,
        payout_method=payout_method,
        recipient_data=json.dumps(recipient_data),
    )

    try:
        checkout = flutterwave.create_checkout(
            reference=str(order.reference),
            amount=order.source_amount,
            currency=source_currency,
            customer={
                "email": data["email"],
            },
            meta={"bongo_reference": str(order.reference)},
            redirect_url=request.build_absolute_uri(reverse("transfer_return")),
        )
        checkout_url = checkout["link"]
        if not checkout_url.startswith("https://checkout.flutterwave.com/"):
            raise FlutterwaveError("Flutterwave a retourné un lien de paiement invalide.")
    except (FlutterwaveError, KeyError, TypeError) as exc:
        order.status = TransferOrder.Status.PAYMENT_FAILED
        order.last_error = str(exc)[:240]
        order.save(update_fields=["status", "last_error", "updated_at"])
        message = str(exc) if isinstance(exc, FlutterwaveError) else "Lien de paiement invalide."
        return JsonResponse({"error": message}, status=502)

    return JsonResponse({"checkout_url": checkout_url})


def _process_payment(order, transaction_id):
    transaction_data = flutterwave.verify_transaction(transaction_id)
    try:
        paid_amount = Decimal(str(transaction_data["amount"]))
    except (KeyError, TypeError, InvalidOperation) as exc:
        raise FlutterwaveError("Flutterwave n’a pas confirmé le montant payé.") from exc

    verified = (
        paid_amount.is_finite()
        and str(transaction_data.get("tx_ref")) == str(order.reference)
        and transaction_data.get("status") == "successful"
        and transaction_data.get("currency") == order.source_currency
        and paid_amount >= order.source_amount
    )
    if not verified:
        order.status = TransferOrder.Status.PAYMENT_FAILED
        order.last_error = "Le paiement n’a pas pu être vérifié."
        order.save(update_fields=["status", "last_error", "updated_at"])
        return

    with transaction.atomic():
        locked_order = TransferOrder.objects.select_for_update().get(pk=order.pk)
        if locked_order.status not in {
            TransferOrder.Status.AWAITING_PAYMENT,
            TransferOrder.Status.PAYMENT_FAILED,
        }:
            return
        locked_order.status = TransferOrder.Status.PAYOUT_PROCESSING
        locked_order.payment_id = str(transaction_id)
        locked_order.save(update_fields=["status", "payment_id", "updated_at"])

    recipient_data = json.loads(order.recipient_data)
    transfer_meta = {
        key: recipient_data[key]
        for key in (
            "bank_name", "swift_code", "routing_number", "account_type",
            "city", "postal_code", "street_name", "street_number",
            "beneficiary_address", "first_name", "last_name",
            "beneficiary_merchant_name",
        )
        if recipient_data.get(key)
    }
    transfer_meta["beneficiary_country"] = order.destination_country
    transfer_payload = {
        "amount": format(order.destination_amount, "f"),
        "account_bank": recipient_data["account_bank"],
        "account_number": recipient_data["account_number"],
        "beneficiary_name": recipient_data["beneficiary_name"],
        "currency": order.destination_currency,
        "debit_currency": order.source_currency,
        "reference": f"BGO{order.reference.hex}",
        "narration": "Transfert BONGO",
        "meta": [transfer_meta],
    }
    try:
        payout = flutterwave.create_transfer(transfer_payload)
        payout_id = payout.get("id")
        payout_status = str(payout.get("status", "")).upper()
        if not payout_id or not payout_status:
            raise FlutterwaveError("Flutterwave n’a pas retourné le statut du versement.")
        order.payout_id = str(payout_id)
        order.status = (
            TransferOrder.Status.PAID_OUT
            if payout_status == "SUCCESSFUL"
            else TransferOrder.Status.PAYOUT_PROCESSING
        )
        if payout_status in {"FAILED", "REVERSED"}:
            order.status = TransferOrder.Status.PAYOUT_FAILED
            order.last_error = "Flutterwave n’a pas pu effectuer le versement."
        order.save(update_fields=["payout_id", "status", "last_error", "updated_at"])
    except FlutterwaveError as exc:
        logger.error("Payout failed for transfer %s: %s", order.reference, exc)
        order.status = TransferOrder.Status.PAYOUT_FAILED
        order.last_error = str(exc)[:240]
        order.save(update_fields=["status", "last_error", "updated_at"])


@require_GET
def transfer_return(request):
    reference_text = request.GET.get("tx_ref", "")
    transaction_id = request.GET.get("transaction_id", "")
    try:
        if not isinstance(reference_text, str) or not isinstance(transaction_id, str):
            raise ValueError
        reference = UUID(reference_text)
        if not transaction_id.isascii() or not transaction_id.isdecimal():
            raise ValueError
    except ValueError:
        return redirect("home")

    order = get_object_or_404(TransferOrder, reference=reference)
    try:
        _process_payment(order, transaction_id)
    except FlutterwaveError as exc:
        logger.warning("Payment verification failed for transfer %s: %s", reference, exc)
        order.status = TransferOrder.Status.PAYMENT_FAILED
        order.last_error = str(exc)[:240]
        order.save(update_fields=["status", "last_error", "updated_at"])
    query = urlencode({"transfer": str(reference)})
    return redirect(f"{reverse('home')}?{query}#transferts")


@csrf_exempt
@require_POST
def flutterwave_webhook(request):
    expected_hash = settings.FLW_WEBHOOK_SECRET_HASH
    if not expected_hash:
        return HttpResponse("Webhook non configuré.", status=503)
    if request.headers.get("verif-hash") != expected_hash:
        return HttpResponse("Signature invalide.", status=401)
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse("Corps JSON invalide.", status=400)
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        return HttpResponse("Événement invalide.", status=400)

    event = payload.get("event")
    event_data = payload["data"]
    if event == "charge.completed" and event_data.get("id"):
        reference_text = event_data.get("tx_ref", "")
        try:
            if not isinstance(reference_text, str):
                raise ValueError
            reference = UUID(reference_text)
            transaction_id = str(event_data["id"])
            if not transaction_id.isascii() or not transaction_id.isdecimal():
                raise ValueError
            order = TransferOrder.objects.get(reference=reference)
            _process_payment(order, transaction_id)
        except (ValueError, TransferOrder.DoesNotExist):
            return HttpResponse("Transfert introuvable.", status=404)
        except FlutterwaveError:
            return HttpResponse("Vérification temporairement indisponible.", status=503)
    elif event == "transfer.completed" and event_data.get("id"):
        transfer_id = str(event_data["id"])
        if not transfer_id.isascii() or not transfer_id.isdecimal():
            return HttpResponse("Identifiant de transfert invalide.", status=400)
        order = TransferOrder.objects.filter(payout_id=transfer_id).first()
        if order:
            try:
                status_data = flutterwave.verify_transfer(event_data["id"])
            except FlutterwaveError:
                return HttpResponse("Vérification temporairement indisponible.", status=503)
            expected_reference = f"BGO{order.reference.hex}"
            if status_data.get("reference") != expected_reference:
                logger.error("Flutterwave transfer reference mismatch for %s", order.reference)
                return HttpResponse("Référence de versement invalide.", status=400)
            payout_status = str(status_data.get("status", "")).upper()
            if payout_status == "SUCCESSFUL":
                order.status = TransferOrder.Status.PAID_OUT
                order.last_error = ""
            elif payout_status in {"FAILED", "REVERSED"}:
                order.status = TransferOrder.Status.PAYOUT_FAILED
                order.last_error = "Flutterwave n’a pas pu effectuer le versement."
            order.save(update_fields=["status", "last_error", "updated_at"])
    return HttpResponse(status=200)
