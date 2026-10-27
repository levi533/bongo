from django import forms
from django.core.validators import RegexValidator

from .payouts import COUNTRIES, destination_currency


CURRENCY_CHOICES = [
    (code, code)
    for code in (
        "EUR", "XAF", "XOF", "USD", "GBP", "EGP", "GHS", "KES", "MWK",
        "NGN", "RWF", "TZS", "UGX", "ZAR",
    )
]


class TransferStartForm(forms.Form):
    email = forms.EmailField(max_length=254)
    amount = forms.DecimalField(
        min_value=1,
        max_value=10000000,
        max_digits=14,
        decimal_places=2,
    )
    source_currency = forms.ChoiceField(choices=CURRENCY_CHOICES)
    country = forms.ChoiceField(
        choices=[(code, name) for code, name, region in COUNTRIES if region in {"AF", "EU"}]
    )
    payout_method = forms.ChoiceField(
        choices=[("bank", "Virement bancaire"), ("mobile", "Mobile Money")]
    )
    beneficiary_name = forms.CharField(max_length=120)
    first_name = forms.CharField(max_length=60, required=False)
    last_name = forms.CharField(max_length=60, required=False)
    beneficiary_merchant_name = forms.CharField(max_length=120, required=False)
    account_number = forms.CharField(
        max_length=40,
        validators=[
            RegexValidator(
                regex=r"^[A-Za-z0-9 .+()/\-]{4,40}$",
                message="Vérifiez le numéro de compte ou de téléphone.",
            )
        ],
    )
    bank_code = forms.CharField(max_length=30)
    bank_name = forms.CharField(max_length=120, required=False)
    swift_code = forms.CharField(max_length=20, required=False)
    routing_number = forms.CharField(max_length=30, required=False)
    account_type = forms.ChoiceField(
        choices=[
            ("", "Sélectionner"),
            ("checking", "Checking"),
            ("depository", "Depository"),
            ("personal", "Personnel"),
            ("corporate", "Professionnel"),
        ],
        required=False,
    )
    city = forms.CharField(max_length=80, required=False)
    postal_code = forms.CharField(max_length=20, required=False)
    street_name = forms.CharField(max_length=100, required=False)
    street_number = forms.CharField(max_length=20, required=False)
    beneficiary_address = forms.CharField(max_length=180, required=False)

    def clean_beneficiary_name(self):
        value = self.cleaned_data["beneficiary_name"].strip()
        if not value:
            raise forms.ValidationError("Indiquez le nom complet du bénéficiaire.")
        return value

    def clean_bank_code(self):
        value = self.cleaned_data["bank_code"].strip()
        if not value:
            raise forms.ValidationError("Indiquez le code de la banque ou du réseau.")
        return value

    def clean(self):
        cleaned_data = super().clean()
        source_currency = cleaned_data.get("source_currency")
        amount = cleaned_data.get("amount")
        if source_currency in {"XAF", "XOF", "UGX", "RWF"} and amount is not None:
            if amount != amount.to_integral_value():
                self.add_error("amount", "Saisissez un montant entier pour cette devise.")
        country = cleaned_data.get("country")
        method = cleaned_data.get("payout_method")
        currency = destination_currency(country, method) if country and method else None
        if country and method and not currency:
            self.add_error(
                "country",
                "Cette destination ou ce mode de versement n’est pas disponible via Flutterwave.",
            )
            return cleaned_data

        if currency in {"EUR", "USD", "GBP"}:
            if not cleaned_data.get("bank_name"):
                self.add_error("bank_name", "Le nom de la banque est requis.")
            if currency == "EUR":
                for field in ("swift_code", "city", "postal_code", "street_name", "street_number"):
                    if not cleaned_data.get(field):
                        self.add_error(field, "Ce champ est requis pour un transfert SEPA.")
            if currency == "USD":
                for field in (
                    "swift_code", "routing_number", "beneficiary_address",
                    "postal_code", "street_number", "street_name",
                ):
                    if not cleaned_data.get(field):
                        self.add_error(field, "Ce champ est requis pour un transfert USD.")
            if currency == "USD" and cleaned_data.get("account_type") not in {"checking", "depository"}:
                self.add_error("account_type", "Pour un compte USD, choisissez Checking ou Depository.")
            if currency == "GBP" and cleaned_data.get("account_type") not in {"personal", "corporate"}:
                self.add_error("account_type", "Pour un compte GBP, choisissez Personnel ou Professionnel.")
            if currency == "GBP" and cleaned_data.get("account_type") == "personal":
                for field in ("first_name", "last_name"):
                    if not cleaned_data.get(field):
                        self.add_error(field, "Ce champ est requis pour un compte personnel.")
            if currency == "GBP" and cleaned_data.get("account_type") == "corporate":
                if not cleaned_data.get("beneficiary_merchant_name"):
                    self.add_error(
                        "beneficiary_merchant_name",
                        "Indiquez le nom de l’entreprise bénéficiaire.",
                    )
        cleaned_data["destination_currency"] = currency
        return cleaned_data
