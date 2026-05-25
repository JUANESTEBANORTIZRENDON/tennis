"""Modelos no gestionados de jugadores, lesiones, equipos e inscripciones.

Trazabilidad:
sirven como mapa de lectura del esquema; altas y cambios pasan por
`player_service` y procedimientos almacenados.
"""

from django.db import models


class Player(models.Model):
    """Jugador profesional registrado en Neon."""

    id = models.CharField(primary_key=True, max_length=80, db_column="id")
    first_name = models.CharField(max_length=120, db_column="first_name")
    last_name = models.CharField(max_length=120, db_column="last_name")
    gender = models.CharField(max_length=30, db_column="gender")
    country_code = models.CharField(max_length=3, db_column="country_code")

    class Meta:
        managed = False
        db_table = "Player"


class Injury(models.Model):
    """Lesion individual con estado activo/recuperado."""

    id = models.IntegerField(primary_key=True, db_column="id")
    injury_type_id = models.IntegerField(db_column="injury_type_id")
    injury_date = models.DateField(db_column="injury_date")
    recovery_date = models.DateField(db_column="recovery_date", blank=True, null=True)
    active = models.BooleanField(db_column="active")

    class Meta:
        managed = False
        db_table = "Injury"


class Team(models.Model):
    """Unidad competitiva: un jugador en singles o pareja en doubles."""

    id = models.IntegerField(primary_key=True, db_column="id")
    name = models.CharField(max_length=255, db_column="name")
    notes = models.TextField(db_column="notes", blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Team"


class Entry(models.Model):
    """Inscripcion de un equipo en un cuadro."""

    id = models.IntegerField(primary_key=True, db_column="id")
    subcategory_id = models.IntegerField(db_column="subcategory_id")
    team_id = models.IntegerField(db_column="team_id")
    seed = models.IntegerField(db_column="seed", blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Entry"
