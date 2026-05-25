"""Modelos no gestionados de la estructura competitiva en Neon.

Trazabilidad:
Django consulta estas tablas, pero `managed = False` deja el DDL y reglas en
Neon/migraciones SQL; las vistas usan servicios antes de llegar a la base.
"""

from django.db import models


class Tournament(models.Model):
    """Torneo principal; Django solo lo consulta, no lo migra."""

    id = models.IntegerField(primary_key=True, db_column="id")
    name = models.CharField(max_length=255, db_column="name")
    year = models.IntegerField(db_column="year")
    start_date = models.DateField(db_column="start_date")
    end_date = models.DateField(db_column="end_date")
    location = models.TextField(db_column="location", blank=True, null=True)
    surface = models.CharField(max_length=60, db_column="surface")
    description = models.TextField(db_column="description", blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Tournament"


class Court(models.Model):
    """Cancha fisica asociada a un torneo."""

    id = models.IntegerField(primary_key=True, db_column="id")
    tournament = models.ForeignKey(Tournament, db_column="tournament_id", on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=120, db_column="name")
    capacity = models.IntegerField(db_column="capacity")
    surface = models.CharField(max_length=60, db_column="surface")
    indoor = models.BooleanField(db_column="indoor")
    location = models.TextField(db_column="location", blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Court"


class Category(models.Model):
    """Categoria por torneo, genero y modalidad."""

    id = models.IntegerField(primary_key=True, db_column="id")
    tournament = models.ForeignKey(Tournament, db_column="tournament_id", on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=120, db_column="name")
    gender = models.CharField(max_length=40, db_column="gender")
    mode = models.CharField(max_length=40, db_column="mode")

    class Meta:
        managed = False
        db_table = "Category"


class SubCategory(models.Model):
    """Cuadro competitivo dentro de una categoria."""

    id = models.IntegerField(primary_key=True, db_column="id")
    category = models.ForeignKey(Category, db_column="category_id", on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=120, db_column="name")
    draw_size = models.IntegerField(db_column="draw_size")

    class Meta:
        managed = False
        db_table = "SubCategory"


class Round(models.Model):
    """Ronda/fase dentro de un cuadro."""

    id = models.IntegerField(primary_key=True, db_column="id")
    subcategory = models.ForeignKey(SubCategory, db_column="subcategory_id", on_delete=models.DO_NOTHING)
    round_name = models.CharField(max_length=120, db_column="round_name")
    round_number = models.IntegerField(db_column="round_number")
    best_of_sets = models.IntegerField(db_column="best_of_sets")

    class Meta:
        managed = False
        db_table = "Round"
