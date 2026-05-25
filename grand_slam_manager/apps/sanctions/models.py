"""Modelos no gestionados de sanciones e infracciones.

Trazabilidad:
documentan las tablas base; formularios y servicios aplican la regla de un solo
sujeto sancionado antes de llamar PostgreSQL.
"""

from django.db import models


class ViolationType(models.Model):
    """Catalogo de infracciones/violaciones."""

    id = models.IntegerField(primary_key=True, db_column="id")
    code = models.CharField(max_length=80, db_column="code")
    name = models.CharField(max_length=255, db_column="name")

    class Meta:
        managed = False
        db_table = "ViolationType"


class Sanction(models.Model):
    """Sancion deportiva aplicada a jugador, equipo u oficial."""

    id = models.IntegerField(primary_key=True, db_column="id")
    tournament_id = models.IntegerField(db_column="tournament_id")
    match_id = models.IntegerField(db_column="match_id", blank=True, null=True)
    notes = models.TextField(db_column="notes", blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Sanction"
