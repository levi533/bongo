import json
import logging
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


logger = logging.getLogger(__name__)
API_ROOT = "https://api.flutterwave.com/v3"


class FlutterwaveError(Exception):
    pass


def _request(method, endpoint, payload=None, query=None):
    secret_key = getattr(settings, "FLW_SECRET_KEY", "")
    if not secret_key:
        raise FlutterwaveError(
            "Le service de transfert n’est pas configuré. Contactez l’assistance."
        )
    url = f"{API_ROOT}{endpoint}"
    if query:
        url = f"{url}?{urlencode(query)}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=12) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        logger.warning("Flutterwave API returned HTTP %s", exc.code)
        raise FlutterwaveError(
            "Flutterwave n’a pas pu traiter la demande. Vérifiez le corridor et réessayez."
        ) from exc
    except (URLError, TimeoutError) as exc:
        logger.error("Flutterwave API request failed: %s", exc)
        raise FlutterwaveError(
            "Flutterwave est momentanément inaccessible. Réessayez plus tard."
        ) from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.error("Flutterwave returned an invalid response")
        raise FlutterwaveError("Réponse Flutterwave invalide.") from exc

    if not isinstance(result, dict) or result.get("status") != "success":
        logger.warning("Flutterwave API rejected a request")
        raise FlutterwaveError(
            "Flutterwave a refusé la demande. Vérifiez la devise et le pays du bénéficiaire."
        )
    data = result.get("data")
    if not isinstance(data, dict):
        logger.error("Flutterwave returned a successful response without data")
        raise FlutterwaveError("Réponse Flutterwave incomplète.")
    return data


def quote(source_currency, destination_currency, destination_amount="1"):
    try:
        amount = Decimal(destination_amount)
    except (InvalidOperation, TypeError) as exc:
        raise FlutterwaveError("Montant de conversion invalide.") from exc
    if not amount.is_finite() or amount <= 0 or amount > Decimal("100000000"):
        raise FlutterwaveError("Le montant doit être supérieur à zéro.")
    data = _request(
        "GET",
        "/transfers/rates",
        query={
            "amount": format(amount, "f"),
            "destination_currency": destination_currency,
            "source_currency": source_currency,
        },
    )
    try:
        rate = Decimal(str(data["rate"]))
        source_amount = Decimal(str(data["source"]["amount"]))
    except (KeyError, TypeError, InvalidOperation) as exc:
        raise FlutterwaveError("Flutterwave n’a pas retourné de taux exploitable.") from exc
    if not rate.is_finite() or rate <= 0 or not source_amount.is_finite():
        raise FlutterwaveError("Flutterwave a retourné un taux invalide.")
    return {"rate": rate, "source_amount": source_amount, "data": data}


def create_checkout(reference, amount, currency, customer, meta, redirect_url):
    return _request(
        "POST",
        "/payments",
        payload={
            "tx_ref": reference,
            "amount": format(amount, "f"),
            "currency": currency,
            "redirect_url": redirect_url,
            "customer": customer,
            "meta": meta,
            "customizations": {
                "title": "BONGO",
                "description": "Paiement de votre transfert",
            },
        },
    )


def verify_transaction(transaction_id):
    return _request("GET", f"/transactions/{transaction_id}/verify")


def create_transfer(payload):
    return _request("POST", "/transfers", payload=payload)


def verify_transfer(transfer_id):
    return _request("GET", f"/transfers/{transfer_id}")
