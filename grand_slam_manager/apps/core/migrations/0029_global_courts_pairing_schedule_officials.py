"""Canchas globales, emparejamiento manual con agenda y oficiales."""

from django.db import migrations


SQL = r"""
ALTER TABLE "Court" ALTER COLUMN tournament_id DROP NOT NULL;

DO $drop$
DECLARE
    procedure_signature text;
BEGIN
    FOR procedure_signature IN
        SELECT p.oid::regprocedure::text
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = current_schema()
          AND p.prokind = 'p'
          AND p.proname IN ('sp_create_court', 'sp_create_first_round_pairing', 'sp_generate_first_round_matches')
    LOOP
        EXECUTE format('DROP PROCEDURE IF EXISTS %s', procedure_signature);
    END LOOP;
END
$drop$;

CREATE OR REPLACE PROCEDURE public.sp_create_court(
    IN p_name character varying,
    IN p_capacity integer,
    IN p_surface surface_type,
    IN p_indoor boolean,
    IN p_location text
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM public.fn_crud_insert_json('Court', jsonb_build_object(
        'tournament_id', NULL,
        'name', p_name,
        'capacity', p_capacity,
        'surface', p_surface,
        'indoor', p_indoor,
        'location', p_location
    ));
END;
$$;

CREATE OR REPLACE FUNCTION public.fn_assign_random_official_to_match(p_match_id integer)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    v_official_id integer;
BEGIN
    IF p_match_id IS NULL OR NOT EXISTS (SELECT 1 FROM "Official" WHERE is_active = true) THEN
        RETURN;
    END IF;

    SELECT o.id
    INTO v_official_id
    FROM "Official" o
    WHERE o.is_active = true
      AND NOT EXISTS (
          SELECT 1
          FROM "MatchOfficial" mo
          WHERE mo.match_id = p_match_id
            AND mo.official_id = o.id
      )
    ORDER BY random()
    LIMIT 1;

    IF v_official_id IS NULL THEN
        RETURN;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM "MatchOfficial"
        WHERE match_id = p_match_id
          AND role = 'Oficial principal'
    ) THEN
        INSERT INTO "MatchOfficial" (match_id, official_id, role, assigned_by_user_id, assigned_at)
        VALUES (p_match_id, v_official_id, 'Oficial principal', NULL, CURRENT_TIMESTAMP);
    END IF;
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_create_first_round_pairing(
    IN p_subcategory_id integer,
    IN p_team_a_id integer,
    IN p_team_b_id integer,
    IN p_scheduled_datetime timestamp with time zone,
    IN p_court_id integer
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_round_id integer;
    v_match_id integer;
    v_tournament_id integer;
BEGIN
    IF p_subcategory_id IS NULL OR p_team_a_id IS NULL OR p_team_b_id IS NULL OR p_scheduled_datetime IS NULL OR p_court_id IS NULL THEN
        RAISE EXCEPTION 'invalid_pairing_payload';
    END IF;
    IF p_team_a_id = p_team_b_id THEN
        RAISE EXCEPTION 'same_team_pairing';
    END IF;

    SELECT c.tournament_id
    INTO v_tournament_id
    FROM "SubCategory" sc
    JOIN "Category" c ON c.id = sc.category_id
    WHERE sc.id = p_subcategory_id;

    SELECT id INTO v_round_id
    FROM "Round"
    WHERE subcategory_id = p_subcategory_id
    ORDER BY round_number
    LIMIT 1;

    IF v_round_id IS NULL THEN
        CALL public.sp_generate_rounds_for_tournament(v_tournament_id);
        SELECT id INTO v_round_id
        FROM "Round"
        WHERE subcategory_id = p_subcategory_id
        ORDER BY round_number
        LIMIT 1;
    END IF;
    IF v_round_id IS NULL THEN
        RAISE EXCEPTION 'first_round_missing';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM "Entry" WHERE subcategory_id = p_subcategory_id AND team_id = p_team_a_id)
       OR NOT EXISTS (SELECT 1 FROM "Entry" WHERE subcategory_id = p_subcategory_id AND team_id = p_team_b_id) THEN
        RAISE EXCEPTION 'team_not_entered';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM "Match" m
        JOIN "MatchParticipant" mp ON mp.match_id = m.id
        WHERE m.round_id = v_round_id
          AND mp.team_id IN (p_team_a_id, p_team_b_id)
    ) THEN
        RAISE EXCEPTION 'team_already_paired';
    END IF;

    INSERT INTO "Match" (round_id, scheduled_datetime, court_id, status, winning_team_id, notes)
    VALUES (v_round_id, p_scheduled_datetime, p_court_id, 'Scheduled', NULL, 'Partido de primera ronda creado por seleccion manual.')
    RETURNING id INTO v_match_id;

    INSERT INTO "MatchParticipant" (match_id, team_id, side, sets_won, games_won, points_won, is_winner)
    VALUES
        (v_match_id, p_team_a_id, 'A', 0, 0, 0, false),
        (v_match_id, p_team_b_id, 'B', 0, 0, 0, false);

    PERFORM public.fn_assign_random_official_to_match(v_match_id);
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_generate_first_round_matches(
    IN p_tournament_id integer,
    IN p_category_id integer DEFAULT NULL,
    IN p_subcategory_id integer DEFAULT NULL,
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
    CALL public.sp_generate_rounds_for_tournament(p_tournament_id);

    FOR sc_rec IN
        SELECT sc.id AS subcategory_id, sc.draw_size
        FROM "SubCategory" sc
        JOIN "Category" c ON c.id = sc.category_id
        WHERE c.tournament_id = p_tournament_id
          AND (p_category_id IS NULL OR c.id = p_category_id)
          AND (p_subcategory_id IS NULL OR sc.id = p_subcategory_id)
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

        SELECT id INTO v_court_id FROM "Court" ORDER BY id LIMIT 1;

        SELECT array_agg(team_id)
        INTO v_teams
        FROM (
            SELECT team_id
            FROM "Entry"
            WHERE subcategory_id = sc_rec.subcategory_id
            ORDER BY CASE WHEN p_mode = 'random' THEN random() ELSE COALESCE(seed, 999999)::double precision END, id
        ) q;

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
                COALESCE(v_start_date, CURRENT_DATE) + TIME '10:00' + ((v_pair_index - 1) * INTERVAL '2 hours'),
                v_court_id,
                'Scheduled',
                NULL,
                CASE WHEN p_mode = 'random' THEN 'Partido de primera ronda generado por sorteo.' ELSE 'Partido de primera ronda generado por siembra.' END
            )
            RETURNING id INTO v_match_id;

            INSERT INTO "MatchParticipant" (match_id, team_id, side, sets_won, games_won, points_won, is_winner)
            VALUES
                (v_match_id, v_team_a, 'A', 0, 0, 0, false),
                (v_match_id, v_team_b, 'B', 0, 0, 0, false);

            PERFORM public.fn_assign_random_official_to_match(v_match_id);
            v_pair_index := v_pair_index + 1;
        END LOOP;
    END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_advance_winner_to_next_round()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_subcategory_id integer;
    v_round_number integer;
    v_next_round_id integer;
    v_source_index integer;
    v_target_position integer;
    v_target_side text;
    v_target_match_id integer;
BEGIN
    IF NEW.status::text NOT IN ('Completed', 'Retired', 'Walkover', 'Disqualified')
       OR NEW.winning_team_id IS NULL
       OR (TG_OP = 'UPDATE' AND OLD.winning_team_id IS NOT DISTINCT FROM NEW.winning_team_id AND OLD.status IS NOT DISTINCT FROM NEW.status) THEN
        RETURN NEW;
    END IF;

    SELECT r.subcategory_id, r.round_number INTO v_subcategory_id, v_round_number
    FROM "Round" r WHERE r.id = NEW.round_id;

    SELECT id INTO v_next_round_id
    FROM "Round"
    WHERE subcategory_id = v_subcategory_id AND round_number = v_round_number + 1
    LIMIT 1;

    IF v_next_round_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT source_index INTO v_source_index
    FROM (
        SELECT m.id, row_number() OVER (ORDER BY m.id) AS source_index
        FROM "Match" m WHERE m.round_id = NEW.round_id
    ) ordered_matches
    WHERE id = NEW.id;

    v_target_position := CEIL(v_source_index::numeric / 2)::integer;
    v_target_side := CASE WHEN v_source_index % 2 = 1 THEN 'A' ELSE 'B' END;

    SELECT id INTO v_target_match_id
    FROM (
        SELECT m.id, row_number() OVER (ORDER BY m.id) AS target_position
        FROM "Match" m WHERE m.round_id = v_next_round_id
    ) next_matches
    WHERE target_position = v_target_position;

    IF v_target_match_id IS NULL THEN
        INSERT INTO "Match" (round_id, scheduled_datetime, court_id, status, winning_team_id, notes)
        VALUES (
            v_next_round_id,
            COALESCE(NEW.scheduled_datetime::date + 1, CURRENT_DATE + 1) + TIME '10:00' + ((v_target_position - 1) * INTERVAL '2 hours'),
            NEW.court_id,
            'Scheduled',
            NULL,
            'Partido generado automaticamente por avance de ganador.'
        )
        RETURNING id INTO v_target_match_id;
        PERFORM public.fn_assign_random_official_to_match(v_target_match_id);
    END IF;

    DELETE FROM "MatchParticipant"
    WHERE match_id = v_target_match_id
      AND (upper(side) = v_target_side OR team_id = NEW.winning_team_id);

    INSERT INTO "MatchParticipant" (match_id, team_id, side, sets_won, games_won, points_won, is_winner)
    VALUES (v_target_match_id, NEW.winning_team_id, v_target_side, 0, 0, 0, false);

    RETURN NEW;
END;
$$;
"""


REVERSE_SQL = migrations.RunSQL.noop


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0028_schedule_exclude_closed_status"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
