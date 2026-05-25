"""Agrega procedimiento para cambio administrativo de contrasena."""

from django.db import migrations


SQL = r"""
CREATE OR REPLACE PROCEDURE public.sp_update_user_password(
    IN p_user_id integer,
    IN p_password_hash text
)
LANGUAGE plpgsql
AS $$
DECLARE
    id_col text;
BEGIN
    IF p_user_id IS NULL OR p_password_hash IS NULL OR btrim(p_password_hash) = '' THEN
        RAISE EXCEPTION 'Invalid user password update payload.';
    END IF;

    id_col := public.fn_read_first_column('UserAccount', ARRAY['id', 'user_id']);
    IF id_col IS NULL THEN
        RAISE EXCEPTION 'UserAccount id column not found.';
    END IF;

    PERFORM public.fn_crud_update_json(
        'UserAccount',
        id_col,
        p_user_id::text,
        jsonb_build_object('password_hash', p_password_hash)
    );
END;
$$;
"""


REVERSE_SQL = "DROP PROCEDURE IF EXISTS public.sp_update_user_password(integer, text);"


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0009_tournament_filtered_structure"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
