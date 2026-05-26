"""Primera ronda visual, avance automatico y torneo demo pequeno."""

from django.db import migrations


SQL = r"""
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
          AND p.proname IN ('sp_generate_first_round_matches', 'sp_create_first_round_pairing')
    LOOP
        EXECUTE format('DROP PROCEDURE IF EXISTS %s', procedure_signature);
    END LOOP;
END
$drop$;

CREATE OR REPLACE FUNCTION public.fn_team_display_name(p_team_id integer)
RETURNS text
LANGUAGE sql
STABLE
AS $$
    SELECT COALESCE(
        NULLIF(string_agg(NULLIF(btrim(p.first_name || ' ' || p.last_name), ''), ' / ' ORDER BY p.last_name, p.first_name), ''),
        (SELECT name FROM "Team" WHERE id = p_team_id),
        'Equipo ' || p_team_id::text
    )
    FROM "TeamMember" tm
    JOIN "Player" p ON p.id = tm.player_id
    WHERE tm.team_id = p_team_id
      AND tm.end_date IS NULL
$$;

CREATE OR REPLACE FUNCTION public.sp_first_round_entries_json(
    p_tournament_id integer,
    p_category_id integer DEFAULT NULL,
    p_subcategory_id integer DEFAULT NULL
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
            c.tournament_id,
            c.id AS category_id,
            c.name AS categoria,
            sc.id AS subcategory_id,
            sc.name AS cuadro,
            sc.draw_size,
            e.id AS entry_id,
            e.team_id,
            public.fn_team_display_name(e.team_id) AS equipo,
            e.seed,
            EXISTS (
                SELECT 1
                FROM "Round" r
                JOIN "Match" m ON m.round_id = r.id
                JOIN "MatchParticipant" mp ON mp.match_id = m.id
                WHERE r.subcategory_id = sc.id
                  AND r.round_number = (
                      SELECT MIN(r2.round_number) FROM "Round" r2 WHERE r2.subcategory_id = sc.id
                  )
                  AND mp.team_id = e.team_id
            ) AS paired
        FROM "Entry" e
        JOIN "SubCategory" sc ON sc.id = e.subcategory_id
        JOIN "Category" c ON c.id = sc.category_id
        WHERE c.tournament_id = p_tournament_id
          AND (p_category_id IS NULL OR c.id = p_category_id)
          AND (p_subcategory_id IS NULL OR sc.id = p_subcategory_id)
        ORDER BY c.name, sc.name, COALESCE(e.seed, 999999), e.id
    ) row_data;
END;
$$;

CREATE OR REPLACE FUNCTION public.sp_first_round_matches_json(
    p_tournament_id integer,
    p_category_id integer DEFAULT NULL,
    p_subcategory_id integer DEFAULT NULL
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
            c.tournament_id,
            c.id AS category_id,
            c.name AS categoria,
            sc.id AS subcategory_id,
            sc.name AS cuadro,
            sc.draw_size,
            m.id AS match_id,
            m.status::text AS status,
            m.scheduled_datetime,
            m.notes,
            mpa.team_id AS team_a_id,
            public.fn_team_display_name(mpa.team_id) AS team_a,
            mpb.team_id AS team_b_id,
            public.fn_team_display_name(mpb.team_id) AS team_b,
            public.fn_team_display_name(m.winning_team_id) AS winner
        FROM "Match" m
        JOIN "Round" r ON r.id = m.round_id
        JOIN "SubCategory" sc ON sc.id = r.subcategory_id
        JOIN "Category" c ON c.id = sc.category_id
        LEFT JOIN "MatchParticipant" mpa ON mpa.match_id = m.id AND upper(mpa.side) = 'A'
        LEFT JOIN "MatchParticipant" mpb ON mpb.match_id = m.id AND upper(mpb.side) = 'B'
        WHERE c.tournament_id = p_tournament_id
          AND (p_category_id IS NULL OR c.id = p_category_id)
          AND (p_subcategory_id IS NULL OR sc.id = p_subcategory_id)
          AND r.round_number = (
              SELECT MIN(r2.round_number) FROM "Round" r2 WHERE r2.subcategory_id = sc.id
          )
        ORDER BY c.name, sc.name, m.id
    ) row_data;
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_create_first_round_pairing(
    IN p_subcategory_id integer,
    IN p_team_a_id integer,
    IN p_team_b_id integer
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_round_id integer;
    v_match_id integer;
    v_tournament_id integer;
    v_court_id integer;
    v_pair_index integer;
BEGIN
    IF p_subcategory_id IS NULL OR p_team_a_id IS NULL OR p_team_b_id IS NULL THEN
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

    SELECT id
    INTO v_round_id
    FROM "Round"
    WHERE subcategory_id = p_subcategory_id
    ORDER BY round_number
    LIMIT 1;

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

    SELECT id INTO v_court_id FROM "Court" WHERE tournament_id = v_tournament_id ORDER BY id LIMIT 1;
    SELECT COUNT(*) + 1 INTO v_pair_index FROM "Match" WHERE round_id = v_round_id;

    INSERT INTO "Match" (round_id, scheduled_datetime, court_id, status, winning_team_id, notes)
    VALUES (
        v_round_id,
        CURRENT_DATE + TIME '10:00' + ((v_pair_index - 1) * INTERVAL '2 hours'),
        v_court_id,
        'Scheduled',
        NULL,
        'Partido de primera ronda creado por seleccion manual.'
    )
    RETURNING id INTO v_match_id;

    INSERT INTO "MatchParticipant" (match_id, team_id, side, sets_won, games_won, points_won, is_winner)
    VALUES
        (v_match_id, p_team_a_id, 'A', 0, 0, 0, false),
        (v_match_id, p_team_b_id, 'B', 0, 0, 0, false);
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
    SELECT id INTO v_court_id FROM "Court" WHERE tournament_id = p_tournament_id ORDER BY id LIMIT 1;

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

        IF p_mode = 'random' THEN
            SELECT array_agg(team_id)
            INTO v_teams
            FROM (SELECT team_id FROM "Entry" WHERE subcategory_id = sc_rec.subcategory_id ORDER BY random()) q;
        ELSE
            SELECT array_agg(team_id)
            INTO v_teams
            FROM (
                SELECT team_id
                FROM "Entry"
                WHERE subcategory_id = sc_rec.subcategory_id
                ORDER BY COALESCE(seed, 999999), id
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
    v_court_id integer;
BEGIN
    IF NEW.status::text NOT IN ('Completed', 'Retired', 'Walkover', 'Disqualified')
       OR NEW.winning_team_id IS NULL
       OR (TG_OP = 'UPDATE' AND OLD.winning_team_id IS NOT DISTINCT FROM NEW.winning_team_id AND OLD.status IS NOT DISTINCT FROM NEW.status) THEN
        RETURN NEW;
    END IF;

    SELECT r.subcategory_id, r.round_number
    INTO v_subcategory_id, v_round_number
    FROM "Round" r
    WHERE r.id = NEW.round_id;

    SELECT id
    INTO v_next_round_id
    FROM "Round"
    WHERE subcategory_id = v_subcategory_id
      AND round_number = v_round_number + 1
    LIMIT 1;

    IF v_next_round_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT source_index
    INTO v_source_index
    FROM (
        SELECT m.id, row_number() OVER (ORDER BY m.id) AS source_index
        FROM "Match" m
        WHERE m.round_id = NEW.round_id
    ) ordered_matches
    WHERE id = NEW.id;

    v_target_position := CEIL(v_source_index::numeric / 2)::integer;
    v_target_side := CASE WHEN v_source_index % 2 = 1 THEN 'A' ELSE 'B' END;
    v_court_id := NEW.court_id;

    SELECT id
    INTO v_target_match_id
    FROM (
        SELECT m.id, row_number() OVER (ORDER BY m.id) AS target_position
        FROM "Match" m
        WHERE m.round_id = v_next_round_id
    ) next_matches
    WHERE target_position = v_target_position;

    IF v_target_match_id IS NULL THEN
        INSERT INTO "Match" (round_id, scheduled_datetime, court_id, status, winning_team_id, notes)
        VALUES (
            v_next_round_id,
            COALESCE(NEW.scheduled_datetime::date + 1, CURRENT_DATE + 1) + TIME '10:00' + ((v_target_position - 1) * INTERVAL '2 hours'),
            v_court_id,
            'Scheduled',
            NULL,
            'Partido generado automaticamente por avance de ganador.'
        )
        RETURNING id INTO v_target_match_id;
    END IF;

    DELETE FROM "MatchParticipant"
    WHERE match_id = v_target_match_id
      AND (upper(side) = v_target_side OR team_id = NEW.winning_team_id);

    INSERT INTO "MatchParticipant" (match_id, team_id, side, sets_won, games_won, points_won, is_winner)
    VALUES (v_target_match_id, NEW.winning_team_id, v_target_side, 0, 0, 0, false);

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS au_match_advance_winner ON "Match";
CREATE TRIGGER au_match_advance_winner
AFTER UPDATE OF status, winning_team_id ON "Match"
FOR EACH ROW EXECUTE FUNCTION public.trg_advance_winner_to_next_round();

DO $seed$
DECLARE
    today date := CURRENT_DATE;
    v_tournament_id integer;
    v_court_id integer;
    v_category_id integer;
    v_subcategory_id integer;
    v_round1_id integer;
    v_round2_id integer;
    player_ids text[] := ARRAY['P-MC-001', 'P-MC-002', 'P-MC-003', 'P-MC-004'];
    first_names text[] := ARRAY['Adrian', 'Baltazar', 'Cesar', 'Dario'];
    last_names text[] := ARRAY['Vega', 'Rincon', 'Solano', 'Pardo'];
    v_team_id integer;
    i integer;
BEGIN
    INSERT INTO "Tournament" (name, year, start_date, end_date, location, surface, description, status)
    SELECT 'Match Center Demo - Seleccion Primera Ronda', EXTRACT(YEAR FROM today)::integer, today + 2, today + 6, 'Victory Tennis Park, Medellin, COL', 'Hard', 'Torneo pequeno con un solo cuadro para probar seleccion manual de primera ronda.', 'Pendiente por inscripciones'
    WHERE NOT EXISTS (SELECT 1 FROM "Tournament" WHERE name = 'Match Center Demo - Seleccion Primera Ronda')
    RETURNING id INTO v_tournament_id;
    IF v_tournament_id IS NULL THEN
        SELECT id INTO v_tournament_id FROM "Tournament" WHERE name = 'Match Center Demo - Seleccion Primera Ronda' LIMIT 1;
    END IF;

    INSERT INTO "Court" (tournament_id, name, capacity, surface, indoor, location)
    SELECT v_tournament_id, 'Demo Court Primera Ronda', 900, 'Hard', false, 'Medellin'
    WHERE NOT EXISTS (SELECT 1 FROM "Court" WHERE tournament_id = v_tournament_id AND name = 'Demo Court Primera Ronda')
    RETURNING id INTO v_court_id;
    IF v_court_id IS NULL THEN
        SELECT id INTO v_court_id FROM "Court" WHERE tournament_id = v_tournament_id AND name = 'Demo Court Primera Ronda' LIMIT 1;
    END IF;

    INSERT INTO "Category" (tournament_id, name, gender, mode, description)
    SELECT v_tournament_id, 'Demo Singles', 'M', 'Singles', 'Categoria pequena para Match Center.'
    WHERE NOT EXISTS (SELECT 1 FROM "Category" WHERE tournament_id = v_tournament_id AND name = 'Demo Singles')
    RETURNING id INTO v_category_id;
    IF v_category_id IS NULL THEN
        SELECT id INTO v_category_id FROM "Category" WHERE tournament_id = v_tournament_id AND name = 'Demo Singles' LIMIT 1;
    END IF;

    INSERT INTO "SubCategory" (category_id, name, draw_size, description)
    SELECT v_category_id, 'Mini Draw 4 - Manual', 4, 'Cuadro pequeno listo para seleccionar partidos manualmente.'
    WHERE NOT EXISTS (SELECT 1 FROM "SubCategory" WHERE category_id = v_category_id AND name = 'Mini Draw 4 - Manual')
    RETURNING id INTO v_subcategory_id;
    IF v_subcategory_id IS NULL THEN
        SELECT id INTO v_subcategory_id FROM "SubCategory" WHERE category_id = v_category_id AND name = 'Mini Draw 4 - Manual' LIMIT 1;
    END IF;

    INSERT INTO "Round" (subcategory_id, round_name, round_number, best_of_sets, description)
    SELECT v_subcategory_id, 'Semifinal', 1, 3, 'Primera ronda del cuadro demo.'
    WHERE NOT EXISTS (SELECT 1 FROM "Round" WHERE subcategory_id = v_subcategory_id AND round_number = 1)
    RETURNING id INTO v_round1_id;
    INSERT INTO "Round" (subcategory_id, round_name, round_number, best_of_sets, description)
    SELECT v_subcategory_id, 'Final', 2, 3, 'Ronda automatica tras semifinales.'
    WHERE NOT EXISTS (SELECT 1 FROM "Round" WHERE subcategory_id = v_subcategory_id AND round_number = 2)
    RETURNING id INTO v_round2_id;

    FOR i IN 1..4 LOOP
        INSERT INTO "Player" (
            id, document_type, issuer_country, first_name, last_name, gender, birth_date,
            country_code, height_cm, weight_kg, hand, turned_pro_year, biography
        )
        SELECT player_ids[i], 'Passport', 'COL', first_names[i], last_names[i], 'M', DATE '2000-01-01' + (i * 300),
               'COL', 178 + i, 72 + i, 'R', 2020, 'Jugador demo para probar el Match Center.'
        WHERE NOT EXISTS (SELECT 1 FROM "Player" WHERE id = player_ids[i]);

        INSERT INTO "Team" (name, notes)
        SELECT first_names[i] || ' ' || last_names[i], 'Equipo singles para seleccion manual Match Center.'
        WHERE NOT EXISTS (
            SELECT 1 FROM "TeamMember" tm WHERE tm.player_id = player_ids[i] AND tm.end_date IS NULL
        )
        RETURNING id INTO v_team_id;

        IF v_team_id IS NULL THEN
            SELECT tm.team_id INTO v_team_id
            FROM "TeamMember" tm
            WHERE tm.player_id = player_ids[i]
              AND tm.end_date IS NULL
            LIMIT 1;
        ELSE
            INSERT INTO "TeamMember" (team_id, player_id, role, start_date)
            VALUES (v_team_id, player_ids[i], 'Player', today - 3);
        END IF;

        INSERT INTO "Entry" (subcategory_id, team_id, seed, ranking_at_entry, qualifying_method)
        SELECT v_subcategory_id, v_team_id, i, NULL, 'Direct'
        WHERE NOT EXISTS (
            SELECT 1 FROM "Entry" WHERE subcategory_id = v_subcategory_id AND team_id = v_team_id
        );
    END LOOP;

    DELETE FROM "Match"
    WHERE round_id IN (
        SELECT id FROM "Round" WHERE subcategory_id = v_subcategory_id
    );

    UPDATE "Tournament"
    SET status = 'Activo'
    WHERE id = v_tournament_id;

    PERFORM setval(pg_get_serial_sequence('"Tournament"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Tournament"), true);
    PERFORM setval(pg_get_serial_sequence('"Court"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Court"), true);
    PERFORM setval(pg_get_serial_sequence('"Category"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Category"), true);
    PERFORM setval(pg_get_serial_sequence('"SubCategory"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "SubCategory"), true);
    PERFORM setval(pg_get_serial_sequence('"Round"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Round"), true);
    PERFORM setval(pg_get_serial_sequence('"Team"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Team"), true);
    PERFORM setval(pg_get_serial_sequence('"Entry"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Entry"), true);
END
$seed$;
"""


REVERSE_SQL = r"""
DROP TRIGGER IF EXISTS au_match_advance_winner ON "Match";
DROP FUNCTION IF EXISTS public.trg_advance_winner_to_next_round();
DROP PROCEDURE IF EXISTS public.sp_create_first_round_pairing(integer, integer, integer);
DROP PROCEDURE IF EXISTS public.sp_generate_first_round_matches(integer, integer, integer, text);
DROP FUNCTION IF EXISTS public.sp_first_round_matches_json(integer, integer, integer);
DROP FUNCTION IF EXISTS public.sp_first_round_entries_json(integer, integer, integer);
DROP FUNCTION IF EXISTS public.fn_team_display_name(integer);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0025_auto_seed_and_current_entry_player_date"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
