from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Review",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("author", models.CharField(max_length=80, verbose_name="nom")),
                ("city", models.CharField(blank=True, max_length=80, verbose_name="ville")),
                (
                    "rating",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "1 étoile"),
                            (2, "2 étoiles"),
                            (3, "3 étoiles"),
                            (4, "4 étoiles"),
                            (5, "5 étoiles"),
                        ],
                        validators=[MinValueValidator(1), MaxValueValidator(5)],
                        verbose_name="note",
                    ),
                ),
                ("comment", models.TextField(max_length=1000, verbose_name="avis")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="date de publication")),
            ],
            options={
                "verbose_name": "avis",
                "verbose_name_plural": "avis",
                "ordering": ["-created_at"],
            },
        ),
    ]
