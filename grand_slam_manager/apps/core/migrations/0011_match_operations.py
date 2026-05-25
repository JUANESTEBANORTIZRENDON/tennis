"""Agrega rutinas para trazabilidad y desarrollo operativo de partidos."""

from django.db import migrations


SQL = r"""
CREATE OR REPLACE FUNCTION public.sp_matches_by_structure_json(
    p_tournament_id integer DEFAULT NULL,
    p_category_id integer DEFAULT NULL,
    p_round_id integer DEFAULT NULL,
    p_limit integer DEFAULT 300
)
RETURNS SETOF jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    safe_limit integer := LEAST(GREATEST(COALESCE(p_limit, 300), 1), 1000);
BEGIN
    IF NOT public.fn_crud_table_exists('Match') THEN
        RETURN;
    END IF;

    RETURN QUERY EXECUTE format(
        'WITH team_players AS (
            SELECT
                tm.team_id,
                string_agg(trim(concat_ws('' '', p.first_name, p.last_name)), '', '' ORDER BY p.last_name, p.first_name) AS player_names
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
                t.id AS tournament_id,
                t.name AS torneo,
                c.id AS category_id,
                c.name AS categoria,
                sc.id AS subcategory_id,
                sc.name AS cuadro,
                r.id AS round_id,
                r.round_name AS ronda,
                m.scheduled_datetime AS fecha_partido,
                co.name AS cancha,
                m.status AS estado,
                COALESCE(s.jugador_a, ''Por definir'') AS jugador_a,
                COALESCE(s.jugador_b, ''Por definir'') AS jugador_b,
                (m.scheduled_datetime::date = CURRENT_DATE) AS can_open_today,
                m.winning_team_id AS winning_team_id,
                m.notes AS notes
            FROM %5$I m
            LEFT JOIN %6$I r ON r.id = m.round_id
            LEFT JOIN %7$I sc ON sc.id = r.subcategory_id
            LEFT JOIN %8$I c ON c.id = sc.category_id
            LEFT JOIN %9$I t ON t.id = c.tournament_id
            LEFT JOIN %10$I co ON co.id = m.court_id
            LEFT JOIN sides s ON s.match_id = m.id
            WHERE ($1 IS NULL OR t.id = $1)
              AND ($2 IS NULL OR c.id = $2)
              AND ($3 IS NULL OR r.id = $3)
            ORDER BY m.scheduled_datetime NULLS LAST, m.id
            LIMIT %11$s
        ) row_data',
        'TeamMember',
        'Player',
        'MatchParticipant',
        'Team',
        'Match',
        'Round',
        'SubCategory',
        'Category',
        'Tournament',
        'Court',
        safe_limit
    )
    USING p_tournament_id, p_category_id, p_round_id;
END;
$$;

CREATE OR REPLACE FUNCTION public.sp_entry_options_by_round_json(p_round_id integer)
RETURNS SETOF jsonb
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    IF p_round_id IS NULL OR NOT public.fn_crud_table_exists('Entry') THEN
        RETURN;
    END IF;

    RETURN QUERY EXECUTE format(
        'WITH target_round AS (
            SELECT r.subcategory_id
            FROM %1$I r
            WHERE r.id = $1
            LIMIT 1
        ),
        team_players AS (
            SELECT
                tm.team_id,
                string_agg(trim(concat_ws('' '', p.first_name, p.last_name)), '', '' ORDER BY p.last_name, p.first_name) AS player_names
            FROM %2$I tm
            JOIN %3$I p ON p.id = tm.player_id
            GROUP BY tm.team_id
        )
        SELECT to_jsonb(row_data)
        FROM (
            SELECT
                e.team_id,
                COALESCE(NULLIF(tp.player_names, ''''), t.name, ''Equipo '' || e.team_id::text) AS equipo,
                e.seed,
                e.ranking_at_entry,
                e.qualifying_method
            FROM %4$I e
            JOIN target_round tr ON tr.subcategory_id = e.subcategory_id
            LEFT JOIN %5$I t ON t.id = e.team_id
            LEFT JOIN team_players tp ON tp.team_id = e.team_id
            ORDER BY e.seed NULLS LAST, equipo
        ) row_data',
        'Round',
        'TeamMember',
        'Player',
        'Entry',
        'Team'
    )
    USING p_round_id;
END;
$$;

CREATE OR REPLACE FUNCTION public.sp_entries_by_structure_json(
    p_tournament_id integer DEFAULT NULL,
    p_category_id integer DEFAULT NULL,
    p_subcategory_id integer DEFAULT NULL,
    p_limit integer DEFAULT 300
)
RETURNS SETOF jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    safe_limit integer := LEAST(GREATEST(COALESCE(p_limit, 300), 1), 1000);
BEGIN
    IF NOT public.fn_crud_table_exists('Entry') THEN
        RETURN;
    END IF;

    RETURN QUERY EXECUTE format(
        'WITH counts AS (
            SELECT subcategory_id, COUNT(*) AS used_slots
            FROM %1$I
            GROUP BY subcategory_id
        ),
        team_players AS (
            SELECT
                tm.team_id,
                string_agg(trim(concat_ws('' '', p.first_name, p.last_name)), '', '' ORDER BY p.last_name, p.first_name) AS player_names
            FROM %2$I tm
            JOIN %3$I p ON p.id = tm.player_id
            GROUP BY tm.team_id
        )
        SELECT to_jsonb(row_data)
        FROM (
            SELECT
                e.id,
                trn.id AS tournament_id,
                trn.name AS torneo,
                c.id AS category_id,
                c.name AS categoria,
                sc.id AS subcategory_id,
                sc.name AS cuadro,
                e.team_id,
                COALESCE(NULLIF(tp.player_names, ''''), t.name, ''Equipo '' || e.team_id::text) AS equipo,
                e.seed,
                e.ranking_at_entry,
                e.qualifying_method,
                sc.draw_size,
                (sc.draw_size - COALESCE(counts.used_slots, 0)) AS available_slots
            FROM %1$I e
            LEFT JOIN %4$I sc ON sc.id = e.subcategory_id
            LEFT JOIN %5$I c ON c.id = sc.category_id
            LEFT JOIN %6$I trn ON trn.id = c.tournament_id
            LEFT JOIN %7$I t ON t.id = e.team_id
            LEFT JOIN team_players tp ON tp.team_id = e.team_id
            LEFT JOIN counts ON counts.subcategory_id = e.subcategory_id
            WHERE ($1 IS NULL OR trn.id = $1)
              AND ($2 IS NULL OR c.id = $2)
              AND ($3 IS NULL OR sc.id = $3)
            ORDER BY trn.name NULLS LAST, c.id, sc.id, e.seed NULLS LAST, equipo
            LIMIT %8$s
        ) row_data',
        'Entry',
        'TeamMember',
        'Player',
        'SubCategory',
        'Category',
        'Tournament',
        'Team',
        safe_limit
    )
    USING p_tournament_id, p_category_id, p_subcategory_id;
END;
$$;

CREATE OR REPLACE FUNCTION public.sp_match_development_detail_json(p_match_id integer)
RETURNS jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    result jsonb;
BEGIN
    IF p_match_id IS NULL OR NOT public.fn_crud_table_exists('Match') THEN
        RETURN NULL;
    END IF;

    EXECUTE format(
        'WITH match_base AS (
            SELECT *
            FROM public.sp_matches_by_structure_json(NULL, NULL, NULL, 1000) AS item
            WHERE (item ->> ''match_id'')::integer = $1
            LIMIT 1
        ),
        sets AS (
            SELECT
                COALESCE(jsonb_agg(to_jsonb(ms) ORDER BY ms.set_number), ''[]''::jsonb) AS rows,
                COUNT(*) FILTER (WHERE mp_a.team_id = ms.winner_team_id) AS sets_a,
                COUNT(*) FILTER (WHERE mp_b.team_id = ms.winner_team_id) AS sets_b,
                COALESCE(MAX(ms.set_number), 0) + 1 AS next_set
            FROM %1$I ms
            LEFT JOIN %2$I mp_a ON mp_a.match_id = ms.match_id AND upper(mp_a.side) = ''A''
            LEFT JOIN %2$I mp_b ON mp_b.match_id = ms.match_id AND upper(mp_b.side) = ''B''
            WHERE ms.match_id = $1
        ),
        participants AS (
            SELECT jsonb_object_agg(upper(mp.side), mp.team_id) AS teams
            FROM %2$I mp
            WHERE mp.match_id = $1
        )
        SELECT jsonb_build_object(
            ''match'', (SELECT item FROM match_base),
            ''sets'', COALESCE((SELECT rows FROM sets), ''[]''::jsonb),
            ''sets_a'', COALESCE((SELECT sets_a FROM sets), 0),
            ''sets_b'', COALESCE((SELECT sets_b FROM sets), 0),
            ''next_set'', COALESCE((SELECT next_set FROM sets), 1),
            ''teams'', COALESCE((SELECT teams FROM participants), ''{}''::jsonb)
        )',
        'MatchSet',
        'MatchParticipant'
    )
    INTO result
    USING p_match_id;

    RETURN result;
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_start_match(IN p_match_id integer)
LANGUAGE plpgsql
AS $$
DECLARE
    scheduled_day date;
    current_status text;
BEGIN
    IF p_match_id IS NULL THEN
        RAISE EXCEPTION 'Match id is required.';
    END IF;

    EXECUTE format('SELECT scheduled_datetime::date, status::text FROM %I WHERE id = $1', 'Match')
    INTO scheduled_day, current_status
    USING p_match_id;

    IF scheduled_day IS NULL THEN
        RAISE EXCEPTION 'Match not found.';
    END IF;
    IF scheduled_day <> CURRENT_DATE THEN
        RAISE EXCEPTION 'Match can only be opened on scheduled date.';
    END IF;
    IF current_status NOT IN ('Scheduled', 'Suspended', 'InProgress') THEN
        RAISE EXCEPTION 'Match status does not allow start.';
    END IF;

    PERFORM public.fn_crud_update_json('Match', 'id', p_match_id::text, jsonb_build_object('status', 'InProgress'));
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_update_match_status(
    IN p_match_id integer,
    IN p_status text
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_match_id IS NULL OR p_status NOT IN ('Scheduled', 'InProgress', 'Completed', 'Retired', 'Walkover', 'Suspended', 'Cancelled', 'Disqualified') THEN
        RAISE EXCEPTION 'Invalid match status payload.';
    END IF;

    PERFORM public.fn_crud_update_json('Match', 'id', p_match_id::text, jsonb_build_object('status', p_status));
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_match_set_requires_in_progress()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    match_status text;
BEGIN
    EXECUTE format('SELECT status::text FROM %I WHERE id = $1', 'Match')
    INTO match_status
    USING NEW.match_id;

    IF match_status IS NULL THEN
        RAISE EXCEPTION 'Match not found for set registration.';
    END IF;
    IF match_status <> 'InProgress' THEN
        RAISE EXCEPTION 'Sets can only be registered while match is InProgress.';
    END IF;
    RETURN NEW;
END;
$$;

DO $$
BEGIN
    IF public.fn_crud_table_exists('MatchSet') THEN
        DROP TRIGGER IF EXISTS bi_match_set_requires_in_progress ON "MatchSet";
        CREATE TRIGGER bi_match_set_requires_in_progress
        BEFORE INSERT ON "MatchSet"
        FOR EACH ROW EXECUTE FUNCTION public.trg_match_set_requires_in_progress();
    END IF;
END;
$$;
"""


REVERSE_SQL = r"""
DO $$
BEGIN
    IF public.fn_crud_table_exists('MatchSet') THEN
        DROP TRIGGER IF EXISTS bi_match_set_requires_in_progress ON "MatchSet";
    END IF;
END;
$$;
DROP FUNCTION IF EXISTS public.trg_match_set_requires_in_progress();
DROP PROCEDURE IF EXISTS public.sp_update_match_status(integer, text);
DROP PROCEDURE IF EXISTS public.sp_start_match(integer);
DROP FUNCTION IF EXISTS public.sp_match_development_detail_json(integer);
DROP FUNCTION IF EXISTS public.sp_entries_by_structure_json(integer, integer, integer, integer);
DROP FUNCTION IF EXISTS public.sp_entry_options_by_round_json(integer);
DROP FUNCTION IF EXISTS public.sp_matches_by_structure_json(integer, integer, integer, integer);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0010_user_password_procedure"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
