from decimal import Decimal
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.db import connection
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from .models import Review, TransferOrder


class ReviewPageTests(TestCase):
    def test_home_displays_reviews_and_form(self):
        review = Review.objects.create(
            author="Amina",
            city="Paris",
            rating=5,
            comment="Service simple et rapide.",
        )

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, review.comment)
        self.assertContains(response, "Publier mon avis")
        self.assertContains(response, "Convertisseur de transfert")
        self.assertContains(response, "République du Congo — indisponible")

    def test_valid_review_is_saved_and_shown_after_redirect(self):
        response = self.client.post(
            reverse("home"),
            {
                "author": "  Amina  ",
                "city": "Paris",
                "rating": "5",
                "comment": "  Service simple et rapide.  ",
            },
        )

        self.assertRedirects(response, reverse("home"))
        review = Review.objects.get()
        self.assertEqual(review.author, "Amina")
        self.assertEqual(review.comment, "Service simple et rapide.")
        self.assertContains(self.client.get(reverse("home")), review.comment)

    def test_invalid_rating_is_rejected(self):
        response = self.client.post(
            reverse("home"),
            {"author": "Amina", "city": "", "rating": "6", "comment": "Super."},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Review.objects.count(), 0)


@override_settings(
    FLW_SECRET_KEY="test-secret",
    FLW_WEBHOOK_SECRET_HASH="test-webhook-hash",
    FLW_DATA_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"),
    FLW_TRANSFERS_ENABLED=True,
)
class TransferTests(TestCase):
    def test_quote_returns_an_indicative_provider_rate(self):
        with patch(
            "reviews.views.flutterwave.quote",
            return_value={"rate": Decimal("655.957"), "source_amount": Decimal("0.0015")},
        ):
            response = self.client.get(
                reverse("transfer_quote"),
                {"from": "EUR", "to": "XAF", "amount": "100"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["destination_amount"], "65596")
        self.assertTrue(response.json()["indicative"])

    def test_quote_rejects_unknown_currencies(self):
        response = self.client.get(
            reverse("transfer_quote"),
            {"from": "ABC", "to": "XAF", "amount": "100"},
        )

        self.assertEqual(response.status_code, 400)

    @override_settings(FLW_SECRET_KEY="")
    def test_quote_reports_missing_provider_configuration(self):
        response = self.client.get(
            reverse("transfer_quote"),
            {"from": "EUR", "to": "XAF", "amount": "100"},
        )

        self.assertEqual(response.status_code, 503)

    def test_unsupported_destination_is_rejected_before_payment(self):
        response = self.client.post(
            reverse("start_transfer"),
            {
                "email": "client@example.com",
                "amount": "100",
                "source_currency": "EUR",
                "country": "CG",
                "payout_method": "bank",
                "beneficiary_name": "Amina Client",
                "account_number": "12345678",
                "bank_code": "BANK",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(TransferOrder.objects.count(), 0)

    @override_settings(FLW_TRANSFERS_ENABLED=False)
    def test_transfer_start_is_disabled_until_explicitly_enabled(self):
        response = self.client.post(
            reverse("start_transfer"),
            {
                "email": "client@example.com",
                "amount": "100",
                "source_currency": "EUR",
                "country": "CI",
                "payout_method": "mobile",
                "beneficiary_name": "Amina Client",
                "account_number": "22501020304",
                "bank_code": "WAVE",
            },
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(TransferOrder.objects.count(), 0)

    def test_checkout_is_created_and_recipient_data_is_encrypted(self):
        with (
            patch(
                "reviews.views.flutterwave.quote",
                return_value={"rate": Decimal("655.957"), "source_amount": Decimal("0.0015")},
            ),
            patch(
                "reviews.views.flutterwave.create_checkout",
                return_value={"link": "https://checkout.flutterwave.com/v3/hosted/pay/example"},
            ),
        ):
            response = self.client.post(
                reverse("start_transfer"),
                {
                    "email": "client@example.com",
                    "amount": "100",
                    "source_currency": "EUR",
                    "country": "CI",
                    "payout_method": "mobile",
                    "beneficiary_name": "Amina Client",
                    "account_number": "22501020304",
                    "bank_code": "WAVE",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("checkout_url", response.json())
        order = TransferOrder.objects.get()
        self.assertEqual(order.destination_currency, "XOF")
        self.assertEqual(order.destination_amount, Decimal("65596"))
        table = connection.ops.quote_name(TransferOrder._meta.db_table)
        column = connection.ops.quote_name("recipient_data")
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {column} FROM {table} WHERE id = %s",
                [order.pk],
            )
            stored_data = cursor.fetchone()[0]
        self.assertNotIn("22501020304", stored_data)
        self.assertIn("22501020304", order.recipient_data)

    def test_webhook_verifies_payment_before_creating_payout(self):
        order = TransferOrder.objects.create(
            source_amount=Decimal("100"),
            source_currency="EUR",
            destination_amount=Decimal("65596"),
            destination_currency="XOF",
            destination_country="CI",
            payout_method="mobile",
            recipient_data=(
                '{"beneficiary_name":"Amina Client","account_number":"22501020304",'
                '"account_bank":"WAVE"}'
            ),
        )
        with (
            patch(
                "reviews.views.flutterwave.verify_transaction",
                return_value={
                    "tx_ref": str(order.reference),
                    "status": "successful",
                    "currency": "EUR",
                    "amount": "100",
                },
            ),
            patch(
                "reviews.views.flutterwave.create_transfer",
                return_value={"id": 12345, "status": "NEW"},
            ) as create_transfer,
        ):
            response = self.client.post(
                reverse("flutterwave_webhook"),
                data={
                    "event": "charge.completed",
                    "data": {"id": 123, "tx_ref": str(order.reference)},
                },
                content_type="application/json",
                HTTP_VERIF_HASH="test-webhook-hash",
            )

        self.assertEqual(response.status_code, 200)
        create_transfer.assert_called_once()
        order.refresh_from_db()
        self.assertEqual(order.status, TransferOrder.Status.PAYOUT_PROCESSING)
        self.assertEqual(order.payout_id, "12345")

    def test_webhook_rejects_invalid_signature(self):
        response = self.client.post(
            reverse("flutterwave_webhook"),
            data="{}",
            content_type="application/json",
            HTTP_VERIF_HASH="wrong",
        )

        self.assertEqual(response.status_code, 401)

    def test_transfer_webhook_verifies_provider_status(self):
        order = TransferOrder.objects.create(
            source_amount=Decimal("100"),
            source_currency="EUR",
            destination_amount=Decimal("65596"),
            destination_currency="XOF",
            destination_country="CI",
            payout_method="mobile",
            recipient_data='{"beneficiary_name":"Amina","account_number":"22501020304","account_bank":"WAVE"}',
            status=TransferOrder.Status.PAYOUT_PROCESSING,
            payout_id="12345",
        )
        with patch(
            "reviews.views.flutterwave.verify_transfer",
            return_value={
                "reference": f"BGO{order.reference.hex}",
                "status": "SUCCESSFUL",
            },
        ):
            response = self.client.post(
                reverse("flutterwave_webhook"),
                data={"event": "transfer.completed", "data": {"id": 12345}},
                content_type="application/json",
                HTTP_VERIF_HASH="test-webhook-hash",
            )

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, TransferOrder.Status.PAID_OUT)
