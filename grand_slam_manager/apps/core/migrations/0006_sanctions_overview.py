"""Agrega lectura enriquecida para el panel de sanciones."""

from django.db import migrations


SQL = r"""
CREATE OR REPLACE FUNCTION public.sp_categories_overview_json(p_limit integer DEFAULT 300)
RETURNS SETOF jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    safe_limit integer := LEAST(GREATEST(COALESCE(p_limit, 300), 1), 1000);
BEGIN
    IF NOT public.fn_crud_table_exists('Category') THEN
        RETURN;
    END IF;

    IF public.fn_crud_table_exists('Tournament') THEN
        RETURN QUERY EXECUTE format(
            'SELECT to_jsonb(row_data)
            FROM (
                SELECT
                    c.id,
                    c.name,
                    c.gender,
                    c.mode,
                    COALESCE(t.name, ''-'') AS torneo,
                    c.description
                FROM %1$I c
                LEFT JOIN %2$I t ON t.id = c.tournament_id
                ORDER BY c.tournament_id, c.name, c.id
                LIMIT %3$s
            ) row_data',
            'Category',
            'Tournament',
            safe_limit
        );
        RETURN;
    END IF;

    RETURN QUERY SELECT * FROM public.sp_select_table_json('Category', '{}'::jsonb, NULL, ARRAY['tournament_id', 'name', 'id'], safe_limit);
END;
$$;

CREATE OR REPLACE FUNCTION public.sp_sanctions_overview_json(p_limit integer DEFAULT 300)
RETURNS SETOF jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    safe_limit integer := LEAST(GREATEST(COALESCE(p_limit, 300), 1), 1000);
BEGIN
    IF NOT public.fn_crud_table_exists('Sanction') THEN
        RETURN;
    END IF;

    RETURN QUERY EXECUTE format(
        'WITH team_players AS (
            SELECT
                tm.team_id,
                string_agg(
                    trim(concat_ws('' '', p.first_name, p.last_name)),
                    '', '' ORDER BY p.last_name, p.first_name
                ) AS player_names
            FROM %1$I tm
            JOIN %2$I p ON p.id = tm.player_id
            GROUP BY tm.team_id
        )
        SELECT to_jsonb(row_data)
        FROM (
            SELECT
                s.id,
                CASE
                    WHEN s.match_id IS NULL THEN ''-''
                    ELSE ''M-'' || lpad(s.match_id::text, 4, ''0'')
                END AS codigo_partido,
                s.sanction_type,
                COALESCE(
                    NULLIF(trim(concat_ws('' '', p.first_name, p.last_name)), ''''),
                    NULLIF(tp.player_names, ''''),
                    NULLIF(t.name, ''''),
                    ''-''
                ) AS jugador,
                COALESCE(vt.code, vt.name, s.violation_type_id::text, ''-'') AS infraccion,
                s.penalty_points,
                s.penalty_games,
                s.fine_amount,
                s.currency,
                s.is_active,
                s.issued_at,
                s.notes
            FROM %3$I s
            LEFT JOIN %2$I p ON p.id = s.player_id
            LEFT JOIN %4$I t ON t.id = s.team_id
            LEFT JOIN team_players tp ON tp.team_id = s.team_id
            LEFT JOIN %5$I vt ON vt.id = s.violation_type_id
            ORDER BY s.issued_at NULLS LAST, s.id
            LIMIT %6$s
        ) row_data',
        public.fn_crud_first_table(ARRAY['TeamMember', 'TeamPlayer', 'PlayerTeam']),
        'Player',
        'Sanction',
        'Team',
        public.fn_crud_first_table(ARRAY['ViolationType', 'InfractionType']),
        safe_limit
    );
END;
$$;
"""


REVERSE_SQL = r"""
DROP FUNCTION IF EXISTS public.sp_sanctions_overview_json(integer);
DROP FUNCTION IF EXISTS public.sp_categories_overview_json(integer);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_dashboard_upcoming_matches"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
