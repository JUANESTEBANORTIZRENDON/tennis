"""Modelo no gestionado de oficiales.

Trazabilidad:
la tabla real vive en Neon; `official_service` lee y escribe por procedimientos.
"""

from django.db import models


class Official(models.Model):
    """Juez/oficial registrado en Neon."""

    id = models.IntegerField(primary_key=True, db_column="id")
    first_name = models.CharField(max_length=120, db_column="first_name")
    last_name = models.CharField(max_length=120, db_column="last_name")
    license_number = models.CharField(max_length=120, db_column="license_number", blank=True, null=True)
    is_active = models.BooleanField(db_column="is_active")

    class Meta:
        managed = False
        db_table = "Official"
