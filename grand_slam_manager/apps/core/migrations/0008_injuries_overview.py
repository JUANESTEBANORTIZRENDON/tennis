"""Agrega lectura enriquecida para el panel de lesiones."""

from django.db import migrations


SQL = r"""
CREATE OR REPLACE FUNCTION public.sp_injuries_overview_json(p_limit integer DEFAULT 300)
RETURNS SETOF jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    safe_limit integer := LEAST(GREATEST(COALESCE(p_limit, 300), 1), 1000);
    assignment_table text;
    type_table text;
BEGIN
    IF NOT public.fn_crud_table_exists('Injury') THEN
        RETURN;
    END IF;

    assignment_table := public.fn_crud_first_table(ARRAY['PlayerInjury', 'Player_Injury']);
    type_table := public.fn_crud_first_table(ARRAY['InjuryType', 'InjuryCategory']);

    IF assignment_table IS NOT NULL AND type_table IS NOT NULL THEN
        RETURN QUERY EXECUTE format(
            'SELECT to_jsonb(row_data)
            FROM (
                SELECT
                    i.id AS injury_id,
                    pi.player_id,
                    COALESCE(NULLIF(trim(concat_ws('' '', p.first_name, p.last_name)), ''''), pi.player_id::text, ''-'') AS jugador,
                    i.injury_type_id,
                    COALESCE(it.name, i.injury_type_id::text, ''-'') AS tipo_lesion,
                    i.injury_date,
                    i.recovery_date,
                    i.active,
                    pi.assigned_at,
                    i.description
                FROM %1$I pi
                JOIN %2$I i ON i.id = pi.injury_id
                LEFT JOIN %3$I p ON p.id = pi.player_id
                LEFT JOIN %4$I it ON it.id = i.injury_type_id
                ORDER BY i.active DESC, i.injury_date NULLS LAST, i.id
                LIMIT %5$s
            ) row_data',
            assignment_table,
            'Injury',
            'Player',
            type_table,
            safe_limit
        );
        RETURN;
    END IF;

    IF assignment_table IS NOT NULL THEN
        RETURN QUERY EXECUTE format(
            'SELECT to_jsonb(row_data)
            FROM (
                SELECT
                    i.id AS injury_id,
                    pi.player_id,
                    COALESCE(NULLIF(trim(concat_ws('' '', p.first_name, p.last_name)), ''''), pi.player_id::text, ''-'') AS jugador,
                    i.injury_type_id,
                    COALESCE(i.injury_type_id::text, ''-'') AS tipo_lesion,
                    i.injury_date,
                    i.recovery_date,
                    i.active,
                    pi.assigned_at,
                    i.description
                FROM %1$I pi
                JOIN %2$I i ON i.id = pi.injury_id
                LEFT JOIN %3$I p ON p.id = pi.player_id
                ORDER BY i.active DESC, i.injury_date NULLS LAST, i.id
                LIMIT %4$s
            ) row_data',
            assignment_table,
            'Injury',
            'Player',
            safe_limit
        );
        RETURN;
    END IF;

    IF type_table IS NOT NULL THEN
        RETURN QUERY EXECUTE format(
            'SELECT to_jsonb(row_data)
            FROM (
                SELECT
                    i.id AS injury_id,
                    i.injury_type_id,
                    COALESCE(it.name, i.injury_type_id::text, ''-'') AS tipo_lesion,
                    i.injury_date,
                    i.recovery_date,
                    i.active,
                    i.description
                FROM %1$I i
                LEFT JOIN %2$I it ON it.id = i.injury_type_id
                ORDER BY i.active DESC, i.injury_date NULLS LAST, i.id
                LIMIT %3$s
            ) row_data',
            'Injury',
            type_table,
            safe_limit
        );
        RETURN;
    END IF;

    RETURN QUERY EXECUTE format(
        'SELECT to_jsonb(row_data)
        FROM (
            SELECT
                i.id AS injury_id,
                i.injury_type_id,
                COALESCE(i.injury_type_id::text, ''-'') AS tipo_lesion,
                i.injury_date,
                i.recovery_date,
                i.active,
                i.description
            FROM %1$I i
            ORDER BY i.active DESC, i.injury_date NULLS LAST, i.id
            LIMIT %2$s
        ) row_data',
        'Injury',
        safe_limit
    );
END;
$$;
"""


REVERSE_SQL = "DROP FUNCTION IF EXISTS public.sp_injuries_overview_json(integer);"


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_competition_structure_overview"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
