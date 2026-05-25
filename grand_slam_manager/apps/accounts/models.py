"""Modelos no gestionados de cuentas y roles internos.

Trazabilidad:
estos modelos documentan tablas existentes en Neon; las escrituras reales se
hacen por procedimientos desde `accounts.services.user_service`.
"""

from django.db import models


class UserAccount(models.Model):
    """Cuenta interna usada para login del panel."""

    id = models.IntegerField(primary_key=True, db_column="id")
    email = models.EmailField(db_column="email")
    password_hash = models.CharField(max_length=255, db_column="password_hash")
    full_name = models.CharField(max_length=255, db_column="full_name")
    phone = models.CharField(max_length=50, db_column="phone", blank=True, null=True)
    is_active = models.BooleanField(db_column="is_active")

    class Meta:
        managed = False
        db_table = "UserAccount"


class Role(models.Model):
    """Rol asignable a cuentas internas."""

    id = models.IntegerField(primary_key=True, db_column="id")
    name = models.CharField(max_length=120, db_column="name")

    class Meta:
        managed = False
        db_table = "Role"


class UserRole(models.Model):
    """Relacion uno-a-uno entre cuenta y rol."""

    user = models.OneToOneField(UserAccount, primary_key=True, db_column="user_id", on_delete=models.DO_NOTHING)
    role = models.ForeignKey(Role, db_column="role_id", on_delete=models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "UserRole"
