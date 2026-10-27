from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["author", "city", "rating", "comment"]
        widgets = {
            "author": forms.TextInput(
                attrs={"autocomplete": "name", "placeholder": "Votre nom"}
            ),
            "city": forms.TextInput(
                attrs={"autocomplete": "address-level2", "placeholder": "Ex. Paris"}
            ),
            "rating": forms.Select(),
            "comment": forms.Textarea(
                attrs={
                    "rows": 4,
                    "maxlength": 1000,
                    "placeholder": "Racontez votre expérience…",
                }
            ),
        }

    def clean_author(self):
        author = self.cleaned_data["author"].strip()
        if not author:
            raise forms.ValidationError("Indiquez votre nom.")
        return author

    def clean_comment(self):
        comment = self.cleaned_data["comment"].strip()
        if not comment:
            raise forms.ValidationError("Votre avis ne peut pas être vide.")
        return comment
