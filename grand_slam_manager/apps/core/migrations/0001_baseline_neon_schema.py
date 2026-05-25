"""Baseline: declara que Django conoce el esquema Neon ya existente."""

from django.db import migrations


class Migration(migrations.Migration):
    """Marca el punto de partida del esquema existente en Neon.

    No crea ni modifica tablas. Sirve como base para que futuras migraciones
    SQL versionen cambios de esquema, procedimientos y triggers.
    """

    initial = True

    dependencies = []

    operations = []
