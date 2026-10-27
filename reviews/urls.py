from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("api/transfers/quote/", views.transfer_quote, name="transfer_quote"),
    path("api/transfers/start/", views.start_transfer, name="start_transfer"),
    path("api/transfers/return/", views.transfer_return, name="transfer_return"),
    path("api/flutterwave/webhook/", views.flutterwave_webhook, name="flutterwave_webhook"),
]
