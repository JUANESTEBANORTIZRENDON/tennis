"""Agrega lectura enriquecida para proximos partidos del dashboard."""

from django.db import migrations


SQL = r"""
CREATE OR REPLACE FUNCTION public.sp_dashboard_upcoming_matches_json(p_limit integer DEFAULT 8)
RETURNS SETOF jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    safe_limit integer := LEAST(GREATEST(COALESCE(p_limit, 8), 1), 50);
BEGIN
    IF NOT public.fn_crud_table_exists('Match') THEN
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
        ),
        sides AS (
            SELECT
                mp.match_id,
                max(CASE WHEN upper(mp.side) = ''A'' THEN COALESCE(NULLIF(tp.player_names, ''''), t.name) END) AS jugador_a,
                max(CASE WHEN upper(mp.side) = ''B'' THEN COALESCE(NULLIF(tp.player_names, ''''), t.name) END) AS jugador_b
            FROM %3$I mp
            LEFT JOIN %4$I t ON t.id = mp.team_id
            LEFT JOIN team_players tp ON tp.team_id = mp.team_id
            GROUP BY mp.match_id
        )
        SELECT to_jsonb(row_data)
        FROM (
            SELECT
                m.id AS match_id,
                COALESCE(s.jugador_a, ''Por definir'') AS jugador_a,
                COALESCE(s.jugador_b, ''Por definir'') AS jugador_b,
                m.scheduled_datetime AS fecha_partido,
                COALESCE(c.location, t.location, ''Por definir'') AS lugar,
                COALESCE(c.name, ''Por definir'') AS cancha,
                m.status AS status
            FROM %5$I m
            LEFT JOIN sides s ON s.match_id = m.id
            LEFT JOIN %6$I c ON c.id = m.court_id
            LEFT JOIN %7$I r ON r.id = m.round_id
            LEFT JOIN %8$I sc ON sc.id = r.subcategory_id
            LEFT JOIN %9$I cat ON cat.id = sc.category_id
            LEFT JOIN %10$I t ON t.id = COALESCE(cat.tournament_id, c.tournament_id)
            WHERE COALESCE(m.status::text, '''') NOT IN (''Completed'', ''Finalizado'', ''Cancelled'', ''Cancelado'')
            ORDER BY m.scheduled_datetime NULLS LAST, m.id
            LIMIT %11$s
        ) row_data',
        'TeamMember',
        'Player',
        'MatchParticipant',
        'Team',
        'Match',
        'Court',
        'Round',
        'SubCategory',
        'Category',
        'Tournament',
        safe_limit
    );
END;
$$;
"""


REVERSE_SQL = "DROP FUNCTION IF EXISTS public.sp_dashboard_upcoming_matches_json(integer);"


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_read_routines"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
