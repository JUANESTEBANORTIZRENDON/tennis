"""Excluye partidos cerrados de lectura de programacion."""

from django.db import migrations


SQL = r"""
CREATE OR REPLACE FUNCTION public.sp_schedule_matches_by_structure_json(
    p_tournament_id integer DEFAULT NULL,
    p_category_id integer DEFAULT NULL,
    p_subcategory_id integer DEFAULT NULL,
    p_limit integer DEFAULT 300
)
RETURNS SETOF jsonb
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT to_jsonb(row_data)
    FROM (
        SELECT
            m.id AS match_id,
            c.tournament_id,
            t.name AS torneo,
            c.id AS category_id,
            c.name AS categoria,
            sc.id AS subcategory_id,
            sc.name AS cuadro,
            r.id AS round_id,
            r.round_name AS ronda,
            m.scheduled_datetime AS fecha_partido,
            co.name AS cancha,
            m.court_id,
            m.status::text AS estado,
            public.fn_team_display_name(mpa.team_id) AS jugador_a,
            public.fn_team_display_name(mpb.team_id) AS jugador_b,
            public.fn_team_display_name(m.winning_team_id) AS ganador,
            m.notes AS notas
        FROM "Match" m
        JOIN "Round" r ON r.id = m.round_id
        JOIN "SubCategory" sc ON sc.id = r.subcategory_id
        JOIN "Category" c ON c.id = sc.category_id
        JOIN "Tournament" t ON t.id = c.tournament_id
        LEFT JOIN "Court" co ON co.id = m.court_id
        LEFT JOIN "MatchParticipant" mpa ON mpa.match_id = m.id AND upper(mpa.side) = 'A'
        LEFT JOIN "MatchParticipant" mpb ON mpb.match_id = m.id AND upper(mpb.side) = 'B'
        WHERE (p_tournament_id IS NULL OR c.tournament_id = p_tournament_id)
          AND (p_category_id IS NULL OR c.id = p_category_id)
          AND (p_subcategory_id IS NULL OR sc.id = p_subcategory_id)
          AND m.status::text NOT IN ('Completed', 'Retired', 'Walkover', 'Cancelled', 'Disqualified')
        ORDER BY m.scheduled_datetime NULLS LAST, t.start_date DESC, c.name, sc.name, r.round_number, m.id
        LIMIT COALESCE(p_limit, 300)
    ) row_data;
END;
$$;
"""


REVERSE_SQL = migrations.RunSQL.noop


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0027_schedule_structure_filters"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
