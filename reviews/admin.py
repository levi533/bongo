from django.contrib import admin

from .models import Review, TransferOrder


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("author", "city", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("author", "city", "comment")
    ordering = ("-created_at",)


@admin.register(TransferOrder)
class TransferOrderAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "source_amount",
        "source_currency",
        "destination_amount",
        "destination_currency",
        "destination_country",
        "status",
        "created_at",
    )
    list_filter = ("status", "destination_country", "payout_method")
    search_fields = ("payment_id", "payout_id")
    readonly_fields = (
        "reference",
        "source_amount",
        "source_currency",
        "destination_amount",
        "destination_currency",
        "destination_country",
        "payout_method",
        "recipient_data",
        "status",
        "payment_id",
        "payout_id",
        "last_error",
        "created_at",
        "updated_at",
    )
