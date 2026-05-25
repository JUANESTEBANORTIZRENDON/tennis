from django.db import migrations


SQL = r"""
ALTER TABLE "Tournament"
ADD COLUMN IF NOT EXISTS status character varying(40) NOT NULL DEFAULT 'Pendiente por inscripciones';

UPDATE "Tournament"
SET status = 'Pendiente por inscripciones'
WHERE status IS NULL OR btrim(status) = '';

CREATE OR REPLACE FUNCTION public.fn_tournament_entries_complete(p_tournament_id integer)
RETURNS boolean
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_subcategories integer := 0;
    v_incomplete integer := 0;
BEGIN
    SELECT COUNT(*)
    INTO v_subcategories
    FROM "SubCategory" sc
    JOIN "Category" c ON c.id = sc.category_id
    WHERE c.tournament_id = p_tournament_id;

    IF v_subcategories = 0 THEN
        RETURN false;
    END IF;

    SELECT COUNT(*)
    INTO v_incomplete
    FROM "SubCategory" sc
    JOIN "Category" c ON c.id = sc.category_id
    LEFT JOIN "Entry" e ON e.subcategory_id = sc.id
    WHERE c.tournament_id = p_tournament_id
    GROUP BY sc.id, sc.draw_size
    HAVING COUNT(e.id) <> sc.draw_size
    LIMIT 1;

    RETURN COALESCE(v_incomplete, 0) = 0;
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_validate_tournament_dates()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    open_matches integer := 0;
BEGIN
    IF NEW.start_date IS NOT NULL AND NEW.end_date IS NOT NULL AND NEW.start_date > NEW.end_date THEN
        RAISE EXCEPTION 'invalid_tournament_dates';
    END IF;

    IF NEW.status IS NULL OR NEW.status NOT IN ('Pendiente por inscripciones', 'Activo', 'En proceso', 'Finalizado') THEN
        RAISE EXCEPTION 'invalid_tournament_status';
    END IF;

    IF NEW.status IN ('Activo', 'En proceso') AND NOT public.fn_tournament_entries_complete(NEW.id) THEN
        RAISE EXCEPTION 'tournament_entries_incomplete';
    END IF;

    IF NEW.status = 'Finalizado' THEN
        SELECT COUNT(*)
        INTO open_matches
        FROM "Match" m
        JOIN "Round" r ON r.id = m.round_id
        JOIN "SubCategory" sc ON sc.id = r.subcategory_id
        JOIN "Category" c ON c.id = sc.category_id
        WHERE c.tournament_id = NEW.id
          AND m.status::text NOT IN ('Completed', 'Retired', 'Walkover', 'Cancelled', 'Disqualified');

        IF open_matches > 0 THEN
            RAISE EXCEPTION 'tournament_has_open_matches';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_validate_subcategory()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.draw_size IS NULL OR NEW.draw_size NOT IN (2, 4, 8, 16, 32, 64, 128) THEN
        RAISE EXCEPTION 'invalid_grand_slam_draw_size';
    END IF;
    RETURN NEW;
END;
$$;

DROP PROCEDURE IF EXISTS public.sp_create_tournament(character varying, integer, date, date, text, surface_type, text);
DROP PROCEDURE IF EXISTS public.sp_update_tournament(integer, character varying, integer, date, date, text, surface_type, text);

CREATE OR REPLACE PROCEDURE public.sp_create_tournament(
    IN p_name character varying,
    IN p_year integer,
    IN p_start_date date,
    IN p_end_date date,
    IN p_location text,
    IN p_surface surface_type,
    IN p_description text,
    IN p_status character varying DEFAULT 'Pendiente por inscripciones'
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM public.fn_crud_insert_json('Tournament', jsonb_build_object(
        'name', p_name,
        'year', p_year,
        'start_date', p_start_date,
        'end_date', p_end_date,
        'location', p_location,
        'surface', p_surface,
        'description', p_description,
        'status', COALESCE(NULLIF(p_status, ''), 'Pendiente por inscripciones')
    ));
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_update_tournament(
    IN p_id integer,
    IN p_name character varying,
    IN p_year integer,
    IN p_start_date date,
    IN p_end_date date,
    IN p_location text,
    IN p_surface surface_type,
    IN p_description text,
    IN p_status character varying DEFAULT 'Pendiente por inscripciones'
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM public.fn_crud_update_json('Tournament', 'id', p_id::text, jsonb_build_object(
        'name', p_name,
        'year', p_year,
        'start_date', p_start_date,
        'end_date', p_end_date,
        'location', p_location,
        'surface', p_surface,
        'description', p_description,
        'status', COALESCE(NULLIF(p_status, ''), 'Pendiente por inscripciones')
    ));
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_set_tournament_status(
    IN p_tournament_id integer,
    IN p_status character varying
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM public.fn_crud_update_json('Tournament', 'id', p_tournament_id::text, jsonb_build_object('status', p_status));
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_generate_rounds_for_tournament(IN p_tournament_id integer)
LANGUAGE plpgsql
AS $$
DECLARE
    sc_rec record;
    v_entries integer;
    v_rounds integer;
    v_round_number integer;
    v_remaining integer;
    v_round_name text;
    v_best_of_sets integer;
BEGIN
    IF p_tournament_id IS NULL THEN
        RAISE EXCEPTION 'tournament_required';
    END IF;

    FOR sc_rec IN
        SELECT sc.id AS subcategory_id, sc.draw_size, c.gender::text AS gender, c.mode::text AS mode
        FROM "SubCategory" sc
        JOIN "Category" c ON c.id = sc.category_id
        WHERE c.tournament_id = p_tournament_id
        ORDER BY sc.id
    LOOP
        SELECT COUNT(*) INTO v_entries
        FROM "Entry"
        WHERE subcategory_id = sc_rec.subcategory_id;

        IF v_entries <> sc_rec.draw_size THEN
            RAISE EXCEPTION 'draw_not_full';
        END IF;

        v_rounds := CEIL(LN(sc_rec.draw_size::numeric) / LN(2::numeric))::integer;
        v_best_of_sets := CASE WHEN sc_rec.gender = 'M' AND sc_rec.mode = 'Singles' THEN 5 ELSE 3 END;

        FOR v_round_number IN 1..v_rounds LOOP
            v_remaining := sc_rec.draw_size / POWER(2, v_round_number - 1)::integer;
            v_round_name := CASE
                WHEN v_remaining = 2 THEN 'Final'
                WHEN v_remaining = 4 THEN 'Semifinal'
                WHEN v_remaining = 8 THEN 'Quarterfinal'
                ELSE 'Round of ' || v_remaining::text
            END;

            INSERT INTO "Round" (subcategory_id, round_name, round_number, best_of_sets, description)
            SELECT sc_rec.subcategory_id, v_round_name, v_round_number, v_best_of_sets, 'Ronda generada segun tamano de cuadro Grand Slam.'
            WHERE NOT EXISTS (
                SELECT 1 FROM "Round" r
                WHERE r.subcategory_id = sc_rec.subcategory_id
                  AND r.round_number = v_round_number
            );
        END LOOP;
    END LOOP;

    UPDATE "Tournament"
    SET status = 'Activo'
    WHERE id = p_tournament_id
      AND status = 'Pendiente por inscripciones';
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_generate_first_round_matches(
    IN p_tournament_id integer,
    IN p_category_id integer DEFAULT NULL,
    IN p_mode text DEFAULT 'ordered'
)
LANGUAGE plpgsql
AS $$
DECLARE
    sc_rec record;
    v_entries integer;
    v_round_id integer;
    v_court_id integer;
    v_start_date date;
    v_teams integer[];
    v_team_a integer;
    v_team_b integer;
    v_match_id integer;
    v_pair_index integer;
    v_total integer;
BEGIN
    IF p_tournament_id IS NULL THEN
        RAISE EXCEPTION 'tournament_required';
    END IF;
    IF COALESCE(p_mode, 'ordered') NOT IN ('ordered', 'random') THEN
        RAISE EXCEPTION 'invalid_pairing_mode';
    END IF;

    SELECT start_date INTO v_start_date FROM "Tournament" WHERE id = p_tournament_id;
    SELECT id INTO v_court_id FROM "Court" WHERE tournament_id = p_tournament_id ORDER BY id LIMIT 1;

    FOR sc_rec IN
        SELECT sc.id AS subcategory_id, sc.draw_size
        FROM "SubCategory" sc
        JOIN "Category" c ON c.id = sc.category_id
        WHERE c.tournament_id = p_tournament_id
          AND (p_category_id IS NULL OR c.id = p_category_id)
        ORDER BY sc.id
    LOOP
        SELECT COUNT(*) INTO v_entries FROM "Entry" WHERE subcategory_id = sc_rec.subcategory_id;
        IF v_entries <> sc_rec.draw_size THEN
            RAISE EXCEPTION 'draw_not_full';
        END IF;

        SELECT id INTO v_round_id
        FROM "Round"
        WHERE subcategory_id = sc_rec.subcategory_id
        ORDER BY round_number
        LIMIT 1;

        IF v_round_id IS NULL THEN
            RAISE EXCEPTION 'first_round_missing';
        END IF;

        IF EXISTS (SELECT 1 FROM "Match" WHERE round_id = v_round_id) THEN
            RAISE EXCEPTION 'round_matches_already_exist';
        END IF;

        IF p_mode = 'random' THEN
            SELECT array_agg(team_id)
            INTO v_teams
            FROM (
                SELECT team_id
                FROM "Entry"
                WHERE subcategory_id = sc_rec.subcategory_id
                ORDER BY random()
            ) q;
        ELSE
            SELECT array_agg(team_id)
            INTO v_teams
            FROM (
                SELECT team_id
                FROM "Entry"
                WHERE subcategory_id = sc_rec.subcategory_id
                ORDER BY COALESCE(seed, 999999), COALESCE(ranking_at_entry, 999999), id
            ) q;
        END IF;

        v_total := array_length(v_teams, 1);
        v_pair_index := 1;
        WHILE v_pair_index <= v_total / 2 LOOP
            IF p_mode = 'ordered' THEN
                v_team_a := v_teams[v_pair_index];
                v_team_b := v_teams[v_total - v_pair_index + 1];
            ELSE
                v_team_a := v_teams[(v_pair_index * 2) - 1];
                v_team_b := v_teams[v_pair_index * 2];
            END IF;

            INSERT INTO "Match" (round_id, scheduled_datetime, court_id, status, winning_team_id, notes)
            VALUES (
                v_round_id,
                COALESCE(v_start_date, CURRENT_DATE)::timestamp + TIME '10:00' + ((v_pair_index - 1) * INTERVAL '2 hours'),
                v_court_id,
                'Scheduled',
                NULL,
                CASE WHEN p_mode = 'random' THEN 'Partido de primera ronda generado por sorteo.' ELSE 'Partido de primera ronda generado por siembra/ranking.' END
            )
            RETURNING id INTO v_match_id;

            INSERT INTO "MatchParticipant" (match_id, team_id, side, sets_won, games_won, points_won, is_winner)
            VALUES
                (v_match_id, v_team_a, 'A', 0, 0, 0, false),
                (v_match_id, v_team_b, 'B', 0, 0, 0, false);

            v_pair_index := v_pair_index + 1;
        END LOOP;
    END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION public.sp_tournament_bracket_json(p_tournament_id integer)
RETURNS jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    result jsonb;
BEGIN
    IF p_tournament_id IS NULL THEN
        SELECT id INTO p_tournament_id FROM "Tournament" ORDER BY year DESC, start_date DESC, id DESC LIMIT 1;
    END IF;

    WITH selected_tournament AS (
        SELECT *
        FROM "Tournament"
        WHERE id = p_tournament_id
    ),
    bracket_rows AS (
        SELECT jsonb_build_object(
            'subcategory_id', sc.id,
            'cuadro', sc.name,
            'category_id', c.id,
            'categoria', c.name,
            'draw_size', sc.draw_size,
            'entry_count', COUNT(DISTINCT e.id),
            'available_slots', sc.draw_size - COUNT(DISTINCT e.id),
            'entries', COALESCE((
                SELECT jsonb_agg(jsonb_build_object(
                    'team_id', ent.team_id,
                    'equipo', tm.name,
                    'seed', ent.seed,
                    'ranking', ent.ranking_at_entry,
                    'method', ent.qualifying_method
                ) ORDER BY COALESCE(ent.seed, 999999), COALESCE(ent.ranking_at_entry, 999999), ent.id)
                FROM "Entry" ent
                JOIN "Team" tm ON tm.id = ent.team_id
                WHERE ent.subcategory_id = sc.id
            ), '[]'::jsonb),
            'rounds', COALESCE((
                SELECT jsonb_agg(jsonb_build_object(
                    'round_id', r.id,
                    'round_name', r.round_name,
                    'round_number', r.round_number,
                    'matches', COALESCE((
                        SELECT jsonb_agg(jsonb_build_object(
                            'match_id', m.id,
                            'status', m.status::text,
                            'scheduled_datetime', m.scheduled_datetime,
                            'team_a', ta.name,
                            'team_b', tb.name,
                            'winner', tw.name
                        ) ORDER BY m.id)
                        FROM "Match" m
                        LEFT JOIN "MatchParticipant" mpa ON mpa.match_id = m.id AND upper(mpa.side) = 'A'
                        LEFT JOIN "Team" ta ON ta.id = mpa.team_id
                        LEFT JOIN "MatchParticipant" mpb ON mpb.match_id = m.id AND upper(mpb.side) = 'B'
                        LEFT JOIN "Team" tb ON tb.id = mpb.team_id
                        LEFT JOIN "Team" tw ON tw.id = m.winning_team_id
                        WHERE m.round_id = r.id
                    ), '[]'::jsonb)
                ) ORDER BY r.round_number)
                FROM "Round" r
                WHERE r.subcategory_id = sc.id
            ), '[]'::jsonb)
        ) AS bracket
        FROM "SubCategory" sc
        JOIN "Category" c ON c.id = sc.category_id
        LEFT JOIN "Entry" e ON e.subcategory_id = sc.id
        WHERE c.tournament_id = p_tournament_id
        GROUP BY sc.id, sc.name, sc.draw_size, c.id, c.name
        ORDER BY c.name, sc.name
    )
    SELECT jsonb_build_object(
        'tournament', COALESCE((SELECT to_jsonb(t) FROM selected_tournament t), '{}'::jsonb),
        'brackets', COALESCE((SELECT jsonb_agg(bracket) FROM bracket_rows), '[]'::jsonb)
    )
    INTO result;

    RETURN result;
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_sync_tournament_status_from_match()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_tournament_id integer;
    v_open_matches integer;
    v_total_matches integer;
BEGIN
    SELECT c.tournament_id
    INTO v_tournament_id
    FROM "Round" r
    JOIN "SubCategory" sc ON sc.id = r.subcategory_id
    JOIN "Category" c ON c.id = sc.category_id
    WHERE r.id = NEW.round_id;

    IF v_tournament_id IS NULL THEN
        RETURN NEW;
    END IF;

    IF NEW.status::text = 'InProgress' THEN
        UPDATE "Tournament"
        SET status = 'En proceso'
        WHERE id = v_tournament_id
          AND status <> 'Finalizado';
    END IF;

    SELECT COUNT(*),
           COUNT(*) FILTER (WHERE m.status::text NOT IN ('Completed', 'Retired', 'Walkover', 'Cancelled', 'Disqualified'))
    INTO v_total_matches, v_open_matches
    FROM "Match" m
    JOIN "Round" r ON r.id = m.round_id
    JOIN "SubCategory" sc ON sc.id = r.subcategory_id
    JOIN "Category" c ON c.id = sc.category_id
    WHERE c.tournament_id = v_tournament_id;

    IF v_total_matches > 0 AND v_open_matches = 0 THEN
        UPDATE "Tournament"
        SET status = 'Finalizado'
        WHERE id = v_tournament_id;
    END IF;

    RETURN NEW;
END;
$$;

DO $$
BEGIN
    IF public.fn_crud_table_exists('Tournament') THEN
        DROP TRIGGER IF EXISTS biu_tournament_dates ON "Tournament";
        CREATE TRIGGER biu_tournament_dates
        BEFORE INSERT OR UPDATE ON "Tournament"
        FOR EACH ROW EXECUTE FUNCTION public.trg_validate_tournament_dates();
    END IF;

    IF public.fn_crud_table_exists('SubCategory') THEN
        DROP TRIGGER IF EXISTS biu_subcategory_integrity ON "SubCategory";
        CREATE TRIGGER biu_subcategory_integrity
        BEFORE INSERT OR UPDATE ON "SubCategory"
        FOR EACH ROW EXECUTE FUNCTION public.trg_validate_subcategory();
    END IF;

    IF public.fn_crud_table_exists('Match') THEN
        DROP TRIGGER IF EXISTS aiu_match_sync_tournament_status ON "Match";
        CREATE TRIGGER aiu_match_sync_tournament_status
        AFTER INSERT OR UPDATE OF status ON "Match"
        FOR EACH ROW EXECUTE FUNCTION public.trg_sync_tournament_status_from_match();
    END IF;
END $$;
"""


REVERSE_SQL = r"""
DO $$
BEGIN
    IF public.fn_crud_table_exists('Match') THEN
        DROP TRIGGER IF EXISTS aiu_match_sync_tournament_status ON "Match";
    END IF;
END $$;
DROP FUNCTION IF EXISTS public.trg_sync_tournament_status_from_match();
DROP FUNCTION IF EXISTS public.sp_tournament_bracket_json(integer);
DROP PROCEDURE IF EXISTS public.sp_generate_first_round_matches(integer, integer, text);
DROP PROCEDURE IF EXISTS public.sp_generate_rounds_for_tournament(integer);
DROP PROCEDURE IF EXISTS public.sp_set_tournament_status(integer, character varying);
DROP FUNCTION IF EXISTS public.fn_tournament_entries_complete(integer);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0018_match_detail_completed_score"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
