from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models


def _fernet():
    key = getattr(settings, "FLW_DATA_ENCRYPTION_KEY", "")
    if not key:
        raise ImproperlyConfigured(
            "FLW_DATA_ENCRYPTION_KEY doit être défini pour conserver les coordonnées."
        )
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise ImproperlyConfigured(
            "FLW_DATA_ENCRYPTION_KEY doit être une clé Fernet valide."
        ) from exc


class EncryptedTextField(models.TextField):
    def get_prep_value(self, value):
        if value is None:
            return None
        return _fernet().encrypt(str(value).encode("utf-8")).decode("ascii")

    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        try:
            return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeEncodeError) as exc:
            raise ValidationError(
                "Impossible de déchiffrer les coordonnées du bénéficiaire."
            ) from exc
