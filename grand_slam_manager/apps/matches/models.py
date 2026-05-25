"""Modelos no gestionados para partidos y marcador.

Trazabilidad:
representan tablas operativas existentes; `match_service` concentra la lectura
y las escrituras hacia procedimientos de marcador/programacion.
"""

from django.db import models


class Match(models.Model):
    """Partido programable dentro de una ronda."""

    id = models.IntegerField(primary_key=True, db_column="id")
    round_id = models.IntegerField(db_column="round_id")
    scheduled_datetime = models.DateTimeField(db_column="scheduled_datetime")
    court_id = models.IntegerField(db_column="court_id")
    status = models.CharField(max_length=40, db_column="status")

    class Meta:
        managed = False
        db_table = "Match"


class MatchParticipant(models.Model):
    """Equipo asignado a un lado del partido."""

    id = models.IntegerField(primary_key=True, db_column="id")
    match_id = models.IntegerField(db_column="match_id")
    team_id = models.IntegerField(db_column="team_id")
    side = models.CharField(max_length=10, db_column="side")

    class Meta:
        managed = False
        db_table = "MatchParticipant"


class MatchSet(models.Model):
    """Set registrado para un partido."""

    id = models.IntegerField(primary_key=True, db_column="id")
    match_id = models.IntegerField(db_column="match_id")
    set_number = models.IntegerField(db_column="set_number")

    class Meta:
        managed = False
        db_table = "MatchSet"
