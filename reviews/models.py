import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .fields import EncryptedTextField


class Review(models.Model):
    RATING_CHOICES = [
        (1, "1 étoile"),
        (2, "2 étoiles"),
        (3, "3 étoiles"),
        (4, "4 étoiles"),
        (5, "5 étoiles"),
    ]

    author = models.CharField("nom", max_length=80)
    city = models.CharField("ville", max_length=80, blank=True)
    rating = models.PositiveSmallIntegerField(
        "note",
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField("avis", max_length=1000)
    created_at = models.DateTimeField("date de publication", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "avis"
        verbose_name_plural = "avis"

    def __str__(self):
        return f"{self.author} — {self.rating}/5"


class TransferOrder(models.Model):
    class Status(models.TextChoices):
        AWAITING_PAYMENT = "awaiting_payment", "En attente de paiement"
        PAYMENT_FAILED = "payment_failed", "Paiement non confirmé"
        PAYOUT_PROCESSING = "payout_processing", "Versement en cours"
        PAID_OUT = "paid_out", "Versement effectué"
        PAYOUT_FAILED = "payout_failed", "Versement à vérifier"

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    source_amount = models.DecimalField(max_digits=16, decimal_places=2)
    source_currency = models.CharField(max_length=3)
    destination_amount = models.DecimalField(max_digits=16, decimal_places=2)
    destination_currency = models.CharField(max_length=3)
    destination_country = models.CharField(max_length=2)
    payout_method = models.CharField(max_length=10)
    recipient_data = EncryptedTextField()
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.AWAITING_PAYMENT,
    )
    payment_id = models.CharField(max_length=40, blank=True)
    payout_id = models.CharField(max_length=40, blank=True)
    last_error = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "transfert"
        verbose_name_plural = "transferts"

    def __str__(self):
        return f"{self.reference} — {self.get_status_display()}"
