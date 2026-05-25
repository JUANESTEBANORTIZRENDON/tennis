# Procedimientos almacenados y funciones

Generado el 2026-05-25 desde PostgreSQL/Neon. Se organizan por area funcional para facilitar la lectura.

## Procedimientos almacenados

### Seguridad y usuarios

#### sp_create_user
```sql
CREATE OR REPLACE PROCEDURE public.sp_create_user(IN p_email character varying, IN p_password_hash character varying, IN p_full_name character varying, IN p_phone character varying, IN p_role_id integer)
 LANGUAGE plpgsql
AS $procedure$
DECLARE
    new_user_id INT;
BEGIN
    INSERT INTO "UserAccount" (
        "email", "password_hash", "full_name", "phone"
    )
    VALUES (
        p_email, p_password_hash, p_full_name, p_phone
    )
    RETURNING "id" INTO new_user_id;

    INSERT INTO "UserRole" ("user_id", "role_id")
    VALUES (new_user_id, p_role_id);
END;
$procedure$
```

#### sp_create_user_account
```sql
CREATE OR REPLACE PROCEDURE public.sp_create_user_account(IN p_email character varying, IN p_full_name character varying, IN p_phone character varying, IN p_password_hash character varying, IN p_role_id integer, IN p_is_active boolean)
 LANGUAGE plpgsql
AS $procedure$
DECLARE
    created_user_id text;
BEGIN
    created_user_id := public.fn_crud_insert_json('UserAccount', jsonb_build_object(
        'email', lower(btrim(p_email)),
        'user_email', lower(btrim(p_email)),
        'full_name', p_full_name,
        'name', p_full_name,
        'phone', p_phone,
        'password_hash', p_password_hash,
        'password', p_password_hash,
        'is_active', COALESCE(p_is_active, TRUE),
        'active', COALESCE(p_is_active, TRUE)
    ));

    IF p_role_id IS NOT NULL
       AND created_user_id IS NOT NULL
       AND public.fn_crud_table_exists('UserRole') THEN
        PERFORM public.fn_crud_insert_json('UserRole', jsonb_build_object(
            'user_id', created_user_id,
            'account_id', created_user_id,
            'role_id', p_role_id
        ), NULL);
    END IF;
END;
$procedure$
```

#### sp_deactivate_user
```sql
CREATE OR REPLACE PROCEDURE public.sp_deactivate_user(IN p_user_id integer)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    UPDATE "UserAccount"
    SET "is_active" = FALSE
    WHERE "id" = p_user_id;
END;
$procedure$
```

#### sp_update_user_password
```sql
CREATE OR REPLACE PROCEDURE public.sp_update_user_password(IN p_user_id integer, IN p_password_hash text)
 LANGUAGE plpgsql
AS $procedure$
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
$procedure$
```

#### sp_update_user_role
```sql
CREATE OR REPLACE PROCEDURE public.sp_update_user_role(IN p_user_id integer, IN p_role_id integer)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    INSERT INTO "UserRole" ("user_id", "role_id")
    VALUES (p_user_id, p_role_id)
    ON CONFLICT ("user_id")
    DO UPDATE SET "role_id" = EXCLUDED."role_id", "assigned_at" = CURRENT_TIMESTAMP;
END;
$procedure$
```

### Torneos y estructura competitiva

#### sp_create_category
```sql
CREATE OR REPLACE PROCEDURE public.sp_create_category(IN p_tournament_id integer, IN p_name character varying, IN p_gender character varying, IN p_mode character varying, IN p_description text)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    PERFORM public.fn_crud_insert_json('Category', jsonb_build_object(
        'tournament_id', p_tournament_id,
        'name', p_name,
        'gender', p_gender,
        'mode', p_mode,
        'description', p_description
    ));
END;
$procedure$
```

#### sp_create_round
```sql
CREATE OR REPLACE PROCEDURE public.sp_create_round(IN p_round_name character varying, IN p_subcategory_id integer, IN p_round_number integer, IN p_best_of_sets integer, IN p_description text)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    PERFORM public.fn_crud_insert_json('Round', jsonb_build_object(
        'round_name', p_round_name,
        'subcategory_id', p_subcategory_id,
        'round_number', p_round_number,
        'best_of_sets', p_best_of_sets,
        'description', p_description
    ));
END;
$procedure$
```

#### sp_create_subcategory
```sql
CREATE OR REPLACE PROCEDURE public.sp_create_subcategory(IN p_category_id integer, IN p_name character varying, IN p_draw_size integer, IN p_description text)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    PERFORM public.fn_crud_insert_json('SubCategory', jsonb_build_object(
        'category_id', p_category_id,
        'name', p_name,
        'draw_size', p_draw_size,
        'description', p_description
    ));
END;
$procedure$
```

#### sp_create_tournament
```sql
CREATE OR REPLACE PROCEDURE public.sp_create_tournament(IN p_name character varying, IN p_year integer, IN p_start_date date, IN p_end_date date, IN p_location text, IN p_surface surface_type, IN p_description text, IN p_status character varying DEFAULT 'Pendiente por inscripciones'::character varying)
 LANGUAGE plpgsql
AS $procedure$
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
$procedure$
```

#### sp_delete_tournament
```sql
CREATE OR REPLACE PROCEDURE public.sp_delete_tournament(IN p_id integer)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    DELETE FROM "Tournament" WHERE "id" = p_id;
END;
$procedure$
```

#### sp_generate_first_round_matches
```sql
CREATE OR REPLACE PROCEDURE public.sp_generate_first_round_matches(IN p_tournament_id integer, IN p_category_id integer DEFAULT NULL::integer, IN p_mode text DEFAULT 'ordered'::text)
 LANGUAGE plpgsql
AS $procedure$
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
$procedure$
```

#### sp_generate_rounds_for_tournament
```sql
CREATE OR REPLACE PROCEDURE public.sp_generate_rounds_for_tournament(IN p_tournament_id integer)
 LANGUAGE plpgsql
AS $procedure$
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
$procedure$
```

#### sp_seed_incomplete_bracket_demo
```sql
CREATE OR REPLACE PROCEDURE public.sp_seed_incomplete_bracket_demo()
 LANGUAGE plpgsql
AS $procedure$
DECLARE
    v_tournament_id integer;
    v_category_id integer;
    v_subcategory_id integer;
    v_court_id integer;
    v_team_id integer;
    player_ids text[] := ARRAY[
        'P-DEMO-101',
        'P-DEMO-102',
        'P-DEMO-103',
        'P-DEMO-104',
        'P-DEMO-105',
        'P-DEMO-106',
        'P-DEMO-107',
        'P-DEMO-108'
    ];
    first_names text[] := ARRAY['Mateo','Lucas','Nicolas','Samuel','Tomas','Emiliano','Sebastian','Martin'];
    last_names text[] := ARRAY['Rivera','Morales','Cortes','Vargas','Herrera','Rojas','Navarro','Salazar'];
    i integer;
BEGIN
    SELECT id INTO v_tournament_id
    FROM "Tournament"
    WHERE name = 'Grand Slam Demo Pendiente - Inscripciones'
      AND year = EXTRACT(YEAR FROM CURRENT_DATE)::integer;

    IF v_tournament_id IS NULL THEN
        INSERT INTO "Tournament" (name, year, start_date, end_date, location, surface, description, status)
        VALUES (
            'Grand Slam Demo Pendiente - Inscripciones',
            EXTRACT(YEAR FROM CURRENT_DATE)::integer,
            CURRENT_DATE + 10,
            CURRENT_DATE + 23,
            'Victory Tennis Park, Medellin, COL',
            'Hard'::surface_type,
            'Torneo demo con cuadro de 8 y cupos pendientes para probar inscripciones.',
            'Pendiente por inscripciones'
        )
        RETURNING id INTO v_tournament_id;
    END IF;

    SELECT id INTO v_court_id
    FROM "Court"
    WHERE tournament_id = v_tournament_id
      AND name = 'Victory Central Court'
    LIMIT 1;

    IF v_court_id IS NULL THEN
        INSERT INTO "Court" (tournament_id, name, capacity, surface, indoor, location)
        VALUES (v_tournament_id, 'Victory Central Court', 6500, 'Hard'::surface_type, false, 'Medellin')
        RETURNING id INTO v_court_id;
    END IF;

    SELECT id INTO v_category_id
    FROM "Category"
    WHERE tournament_id = v_tournament_id
      AND name = 'Men Singles'
    LIMIT 1;

    IF v_category_id IS NULL THEN
        INSERT INTO "Category" (tournament_id, name, gender, mode, description)
        VALUES (v_tournament_id, 'Men Singles', 'M'::gender_type, 'Singles'::mode_type, 'Categoria masculina demo.')
        RETURNING id INTO v_category_id;
    END IF;

    SELECT id INTO v_subcategory_id
    FROM "SubCategory"
    WHERE category_id = v_category_id
      AND name = 'Main Draw Demo 8'
    LIMIT 1;

    IF v_subcategory_id IS NULL THEN
        INSERT INTO "SubCategory" (category_id, name, draw_size, description)
        VALUES (v_category_id, 'Main Draw Demo 8', 8, 'Cuadro de 8: seis inscritos y dos cupos pendientes.')
        RETURNING id INTO v_subcategory_id;
    END IF;

    FOR i IN 1..array_length(player_ids, 1) LOOP
        INSERT INTO "Player" (
            id, document_type, issuer_country, first_name, last_name, gender, birth_date,
            country_code, height_cm, weight_kg, hand, turned_pro_year, biography
        )
        VALUES (
            player_ids[i], 'Passport', 'COL', first_names[i], last_names[i], 'M'::gender_type,
            DATE '1998-01-01' + (i * 410),
            'COL', 178 + i, 70 + i, (CASE WHEN i % 3 = 0 THEN 'L' ELSE 'R' END)::hand_type,
            2018 + (i % 4), 'Jugador demo para completar inscripciones.'
        )
        ON CONFLICT (id) DO NOTHING;

        SELECT tm.team_id INTO v_team_id
        FROM "TeamMember" tm
        WHERE tm.player_id = player_ids[i]
        LIMIT 1;

        IF v_team_id IS NULL THEN
            INSERT INTO "Team" (name, notes)
            VALUES (first_names[i] || ' ' || last_names[i], 'Equipo singles demo')
            RETURNING id INTO v_team_id;

            INSERT INTO "TeamMember" (team_id, player_id, role, start_date)
            VALUES (v_team_id, player_ids[i], 'Player', CURRENT_DATE);
        END IF;

        IF i <= 6 THEN
            INSERT INTO "Entry" (subcategory_id, team_id, seed, ranking_at_entry, qualifying_method)
            SELECT v_subcategory_id, v_team_id, i, 80 + i, 'Direct'
            WHERE NOT EXISTS (
                SELECT 1 FROM "Entry"
                WHERE subcategory_id = v_subcategory_id
                  AND team_id = v_team_id
            );
        END IF;
    END LOOP;
END;
$procedure$
```

#### sp_set_tournament_status
```sql
CREATE OR REPLACE PROCEDURE public.sp_set_tournament_status(IN p_tournament_id integer, IN p_status character varying)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    PERFORM public.fn_crud_update_json('Tournament', 'id', p_tournament_id::text, jsonb_build_object('status', p_status));
END;
$procedure$
```

#### sp_update_tournament
```sql
CREATE OR REPLACE PROCEDURE public.sp_update_tournament(IN p_id integer, IN p_name character varying, IN p_year integer, IN p_start_date date, IN p_end_date date, IN p_location text, IN p_surface surface_type, IN p_description text, IN p_status character varying DEFAULT 'Pendiente por inscripciones'::character varying)
 LANGUAGE plpgsql
AS $procedure$
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
$procedure$
```

### Canchas y programacion

#### sp_add_match_to_session
```sql
CREATE OR REPLACE PROCEDURE public.sp_add_match_to_session(IN p_session_id integer, IN p_match_id integer, IN p_order_in_session integer)
 LANGUAGE plpgsql
AS $procedure$
DECLARE
    target_table text;
BEGIN
    target_table := public.fn_crud_first_table(ARRAY['SessionMatch', 'MatchSession']);
    IF target_table IS NULL THEN
        RAISE EXCEPTION 'Session match table not found.';
    END IF;
    PERFORM public.fn_crud_insert_json(target_table, jsonb_build_object(
        'session_id', p_session_id,
        'match_id', p_match_id,
        'order_in_session', p_order_in_session
    ));
END;
$procedure$
```

#### sp_create_court
```sql
CREATE OR REPLACE PROCEDURE public.sp_create_court(IN p_tournament_id integer, IN p_name character varying, IN p_capacity integer, IN p_surface surface_type, IN p_indoor boolean, IN p_location text)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    PERFORM public.fn_crud_insert_json('Court', jsonb_build_object(
        'tournament_id', p_tournament_id,
        'name', p_name,
        'capacity', p_capacity,
        'surface', p_surface,
        'indoor', p_indoor,
        'location', p_location
    ));
END;
$procedure$
```

#### sp_create_session
```sql
CREATE OR REPLACE PROCEDURE public.sp_create_session(IN p_tournament_id integer, IN p_name character varying, IN p_start_datetime timestamp with time zone, IN p_end_datetime timestamp with time zone, IN p_status character varying, IN p_notes text)
 LANGUAGE plpgsql
AS $procedure$
DECLARE
    target_table text;
BEGIN
    target_table := public.fn_crud_first_table(ARRAY['Session', 'TournamentSession']);
    IF target_table IS NULL THEN
        RAISE EXCEPTION 'Session table not found.';
    END IF;
    PERFORM public.fn_crud_insert_json(target_table, jsonb_build_object(
        'tournament_id', p_tournament_id,
        'name', p_name,
        'start_datetime', p_start_datetime,
        'end_datetime', p_end_datetime,
        'status', p_status,
        'notes', p_notes
    ));
END;
$procedure$
```

#### sp_reschedule_match
```sql
CREATE OR REPLACE PROCEDURE public.sp_reschedule_match(IN p_match_id integer, IN p_user_id integer, IN p_new_datetime timestamp with time zone, IN p_new_court_id integer, IN p_reason text)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    PERFORM public.fn_crud_update_json('Match', 'id', p_match_id::text, jsonb_build_object(
        'scheduled_datetime', p_new_datetime,
        'court_id', p_new_court_id,
        'status', 'Scheduled',
        'rescheduled_by', p_user_id,
        'reschedule_reason', p_reason,
        'updated_at', CURRENT_TIMESTAMP
    ));
END;
$procedure$
```

#### sp_schedule_match
```sql
CREATE OR REPLACE PROCEDURE public.sp_schedule_match(IN p_match_id integer, IN p_round_id integer, IN p_scheduled_datetime timestamp with time zone, IN p_court_id integer, IN p_created_by integer)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    PERFORM public.fn_crud_update_json('Match', 'id', p_match_id::text, jsonb_build_object(
        'round_id', p_round_id,
        'scheduled_datetime', p_scheduled_datetime,
        'court_id', p_court_id,
        'status', 'Scheduled',
        'scheduled_by', p_created_by,
        'updated_at', CURRENT_TIMESTAMP
    ));
END;
$procedure$
```

### Jugadores, equipos e inscripciones

#### sp_add_team_member
```sql
CREATE OR REPLACE PROCEDURE public.sp_add_team_member(IN p_team_id integer, IN p_player_id character varying, IN p_role character varying, IN p_start_date date)
 LANGUAGE plpgsql
AS $procedure$
DECLARE
    target_table text;
BEGIN
    target_table := public.fn_crud_first_table(ARRAY['TeamMember', 'TeamPlayer', 'PlayerTeam']);
    IF target_table IS NULL THEN
        RAISE EXCEPTION 'Team member table not found.';
    END IF;
    PERFORM public.fn_crud_insert_json(target_table, jsonb_build_object(
        'team_id', p_team_id,
        'player_id', p_player_id,
        'role', p_role,
        'start_date', p_start_date
    ));
END;
$procedure$
```

#### sp_assign_coach_to_player
```sql
CREATE OR REPLACE PROCEDURE public.sp_assign_coach_to_player(IN p_player_id character varying, IN p_coach_id integer, IN p_start_date date)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    INSERT INTO "PlayerCoach" (
        "player_id", "coach_id", "start_date"
    )
    VALUES (
        p_player_id, p_coach_id, p_start_date
    );
END;
$procedure$
```

#### sp_assign_injury_to_player
```sql
CREATE OR REPLACE PROCEDURE public.sp_assign_injury_to_player(IN p_player_id character varying, IN p_injury_id integer)
 LANGUAGE plpgsql
AS $procedure$
DECLARE
    target_table text;
BEGIN
    target_table := public.fn_crud_first_table(ARRAY['PlayerInjury', 'Player_Injury']);
    IF target_table IS NULL THEN
        RETURN;
    END IF;
    PERFORM public.fn_crud_insert_json(target_table, jsonb_build_object(
        'player_id', p_player_id,
        'injury_id', p_injury_id,
        'active', TRUE
    ));
END;
$procedure$
```

#### sp_create_coach
```sql
CREATE OR REPLACE PROCEDURE public.sp_create_coach(IN p_first_name character varying, IN p_last_name character varying, IN p_nationality character varying, IN p_birth_date date, IN p_license_number character varying)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    INSERT INTO "Coach" (
        "first_name", "last_name", "nationality", "birth_date", "license_number"
    )
    VALUES (
        p_first_name, p_last_name, p_nationality, p_birth_date, p_license_number
    );
END;
$procedure$
```

#### sp_create_entry
```sql
CREATE OR REPLACE PROCEDURE public.sp_create_entry(IN p_subcategory_id integer, IN p_team_id integer, IN p_seed integer, IN p_ranking_at_entry integer, IN p_qualifying_method character varying)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    PERFORM public.fn_crud_insert_json('Entry', jsonb_build_object(
        'subcategory_id', p_subcategory_id,
        'team_id', p_team_id,
        'seed', p_seed,
        'ranking_at_entry', p_ranking_at_entry,
        'qualifying_method', p_qualifying_method
    ));
END;
$procedure$
```

#### sp_create_player
```sql
CREATE OR REPLACE PROCEDURE public.sp_create_player(IN p_id character varying, IN p_doc_type character varying, IN p_issuer_country character varying, IN p_first_name character varying, IN p_last_name character varying, IN p_gender character varying, IN p_birth_date date, IN p_country_code character varying, IN p_height_cm integer, IN p_weight_kg integer, IN p_hand character varying, IN p_turned_pro_year integer, IN p_bio text)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    PERFORM public.fn_crud_insert_json('Player', jsonb_build_object(
        'id', p_id,
        'doc_type', p_doc_type,
        'document_type', p_doc_type,
        'issuer_country', p_issuer_country,
        'first_name', p_first_name,
        'last_name', p_last_name,
        'gender', p_gender,
        'birth_date', p_birth_date,
        'country_code', p_country_code,
        'height_cm', p_height_cm,
        'weight_kg', p_weight_kg,
        'hand', p_hand,
        'playing_hand', p_hand,
        'turned_pro_year', p_turned_pro_year,
        'bio', p_bio,
        'biography', p_bio
    ), 'id');
END;
$procedure$
```

#### sp_create_player_ranking
```sql
CREATE OR REPLACE PROCEDURE public.sp_create_player_ranking(IN p_player_id character varying, IN p_ranking_date date, IN p_rank_value integer, IN p_ranking_points integer)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    INSERT INTO "PlayerRanking" (
        "player_id", "ranking_date", "rank_value", "ranking_points"
    )
    VALUES (
        p_player_id, p_ranking_date, p_rank_value, p_ranking_points
    );
END;
$procedure$
```

#### sp_create_team
```sql
CREATE OR REPLACE PROCEDURE public.sp_create_team(IN p_name character varying, IN p_notes text)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    PERFORM public.fn_crud_insert_json('Team', jsonb_build_object(
        'name', p_name,
        'notes', p_notes
    ));
END;
$procedure$
```

### Partidos y marcador

#### sp_add_match_participant
```sql
CREATE OR REPLACE PROCEDURE public.sp_add_match_participant(IN p_match_id integer, IN p_team_id integer, IN p_side character varying)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    PERFORM public.fn_crud_insert_json('MatchParticipant', jsonb_build_object(
        'match_id', p_match_id,
        'team_id', p_team_id,
        'side', p_side
    ));
END;
$procedure$
```

#### sp_assign_official_to_match
```sql
CREATE OR REPLACE PROCEDURE public.sp_assign_official_to_match(IN p_match_id integer, IN p_official_id integer, IN p_role character varying, IN p_assigned_by_user_id integer)
 LANGUAGE plpgsql
AS $procedure$
DECLARE
    target_table text;
BEGIN
    target_table := public.fn_crud_first_table(ARRAY['OfficialAssignment', 'MatchOfficial']);
    IF target_table IS NULL THEN
        RAISE EXCEPTION 'Official assignment table not found.';
    END IF;
    PERFORM public.fn_crud_insert_json(target_table, jsonb_build_object(
        'match_id', p_match_id,
        'official_id', p_official_id,
        'role', p_role,
        'assigned_by_user_id', p_assigned_by_user_id,
        'assigned_by', p_assigned_by_user_id
    ));
END;
$procedure$
```

#### sp_create_match
```sql
CREATE OR REPLACE PROCEDURE public.sp_create_match(IN p_round_id integer, IN p_scheduled_datetime timestamp with time zone, IN p_court_id integer, IN p_status character varying)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    PERFORM public.fn_crud_insert_json('Match', jsonb_build_object(
        'round_id', p_round_id,
        'scheduled_datetime', p_scheduled_datetime,
        'court_id', p_court_id,
        'status', p_status
    ));
END;
$procedure$
```

#### sp_finish_match
```sql
CREATE OR REPLACE PROCEDURE public.sp_finish_match(IN p_match_id integer, IN p_winning_team_id integer)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    PERFORM public.fn_crud_update_json('Match', 'id', p_match_id::text, jsonb_build_object(
        'status', 'Completed',
        'winning_team_id', p_winning_team_id,
        'winner_team_id', p_winning_team_id,
        'finished_at', CURRENT_TIMESTAMP
    ));
END;
$procedure$
```

#### sp_register_match_point
```sql
CREATE OR REPLACE PROCEDURE public.sp_register_match_point(IN p_match_id integer, IN p_side text)
 LANGUAGE plpgsql
AS $procedure$
DECLARE
    normalized_side text := upper(btrim(COALESCE(p_side, '')));
    match_status text;
    best_of_sets integer := 3;
    sets_to_win integer := 2;
    team_a integer;
    team_b integer;
    winner_team integer;
    winner_player text;
    server_team integer;
    server_player text;
    receiver_player text;
    current_set_id integer;
    current_set_number integer;
    current_game_id integer;
    current_game_number integer;
    points_a integer := 0;
    points_b integer := 0;
    total_points_a integer := 0;
    total_points_b integer := 0;
    games_a integer := 0;
    games_b integer := 0;
    sets_a integer := 0;
    sets_b integer := 0;
BEGIN
    IF p_match_id IS NULL OR normalized_side NOT IN ('A', 'B') THEN
        RAISE EXCEPTION 'invalid_point_request';
    END IF;

    SELECT m.status::text, COALESCE(r.best_of_sets, 3)
    INTO match_status, best_of_sets
    FROM "Match" m
    LEFT JOIN "Round" r ON r.id = m.round_id
    WHERE m.id = p_match_id;

    IF match_status IS NULL THEN
        RAISE EXCEPTION 'match_not_found';
    END IF;
    IF match_status <> 'InProgress' THEN
        RAISE EXCEPTION 'points_require_in_progress_match';
    END IF;

    SELECT
        MAX(team_id) FILTER (WHERE upper(side) = 'A'),
        MAX(team_id) FILTER (WHERE upper(side) = 'B')
    INTO team_a, team_b
    FROM "MatchParticipant"
    WHERE match_id = p_match_id;

    IF team_a IS NULL OR team_b IS NULL THEN
        RAISE EXCEPTION 'match_requires_two_participants';
    END IF;

    winner_team := CASE WHEN normalized_side = 'A' THEN team_a ELSE team_b END;

    SELECT player_id
    INTO winner_player
    FROM "TeamMember"
    WHERE team_id = winner_team
    ORDER BY player_id
    LIMIT 1;

    IF winner_player IS NULL THEN
        RAISE EXCEPTION 'winner_team_without_player';
    END IF;

    SELECT id, set_number
    INTO current_set_id, current_set_number
    FROM "MatchSet"
    WHERE match_id = p_match_id
      AND winner_team_id IS NULL
    ORDER BY set_number DESC, id DESC
    LIMIT 1;

    IF current_set_id IS NULL THEN
        SELECT COALESCE(MAX(set_number), 0) + 1
        INTO current_set_number
        FROM "MatchSet"
        WHERE match_id = p_match_id;

        INSERT INTO "MatchSet" (match_id, set_number, team_a_games, team_b_games, tie_break_a, tie_break_b, winner_team_id)
        VALUES (p_match_id, current_set_number, 0, 0, NULL, NULL, NULL)
        RETURNING id INTO current_set_id;
    END IF;

    SELECT id, game_number, server_team_id
    INTO current_game_id, current_game_number, server_team
    FROM "MatchGame"
    WHERE match_set_id = current_set_id
      AND winner_team_id IS NULL
    ORDER BY game_number DESC, id DESC
    LIMIT 1;

    IF current_game_id IS NULL THEN
        SELECT COALESCE(MAX(game_number), 0) + 1
        INTO current_game_number
        FROM "MatchGame"
        WHERE match_set_id = current_set_id;

        server_team := CASE WHEN MOD(current_game_number, 2) = 1 THEN team_a ELSE team_b END;

        INSERT INTO "MatchGame" (match_set_id, game_number, server_team_id, winner_team_id, break_occurred)
        VALUES (current_set_id, current_game_number, server_team, NULL, false)
        RETURNING id INTO current_game_id;
    END IF;

    SELECT player_id
    INTO server_player
    FROM "TeamMember"
    WHERE team_id = server_team
    ORDER BY player_id
    LIMIT 1;

    SELECT player_id
    INTO receiver_player
    FROM "TeamMember"
    WHERE team_id = CASE WHEN server_team = team_a THEN team_b ELSE team_a END
    ORDER BY player_id
    LIMIT 1;

    INSERT INTO "MatchPoint" (
        match_set_id,
        game_id,
        point_number,
        server_player_id,
        receiver_player_id,
        winner_player_id,
        rally_length,
        point_type
    )
    VALUES (
        current_set_id,
        current_game_id,
        NULL,
        server_player,
        receiver_player,
        winner_player,
        NULL,
        'Rally'
    );

    SELECT
        COUNT(*) FILTER (WHERE tm.team_id = team_a),
        COUNT(*) FILTER (WHERE tm.team_id = team_b)
    INTO points_a, points_b
    FROM "MatchPoint" p
    JOIN "TeamMember" tm ON tm.player_id = p.winner_player_id
    WHERE p.game_id = current_game_id;

    SELECT
        COUNT(*) FILTER (WHERE tm.team_id = team_a),
        COUNT(*) FILTER (WHERE tm.team_id = team_b)
    INTO total_points_a, total_points_b
    FROM "MatchPoint" p
    JOIN "MatchSet" ms ON ms.id = p.match_set_id
    JOIN "TeamMember" tm ON tm.player_id = p.winner_player_id
    WHERE ms.match_id = p_match_id;

    UPDATE "MatchParticipant"
    SET points_won = CASE
        WHEN team_id = team_a THEN total_points_a
        WHEN team_id = team_b THEN total_points_b
        ELSE points_won
    END
    WHERE match_id = p_match_id;

    IF (points_a >= 4 OR points_b >= 4) AND ABS(points_a - points_b) >= 2 THEN
        UPDATE "MatchGame"
        SET winner_team_id = CASE WHEN points_a > points_b THEN team_a ELSE team_b END,
            break_occurred = CASE
                WHEN server_team_id IS NULL THEN false
                ELSE server_team_id <> CASE WHEN points_a > points_b THEN team_a ELSE team_b END
            END
        WHERE id = current_game_id;

        SELECT
            COUNT(*) FILTER (WHERE winner_team_id = team_a),
            COUNT(*) FILTER (WHERE winner_team_id = team_b)
        INTO games_a, games_b
        FROM "MatchGame"
        WHERE match_set_id = current_set_id;

        UPDATE "MatchSet"
        SET team_a_games = games_a,
            team_b_games = games_b
        WHERE id = current_set_id;

        UPDATE "MatchParticipant"
        SET games_won = CASE
            WHEN team_id = team_a THEN games_a
            WHEN team_id = team_b THEN games_b
            ELSE games_won
        END
        WHERE match_id = p_match_id;

        IF ((games_a >= 6 OR games_b >= 6) AND ABS(games_a - games_b) >= 2)
           OR ((games_a >= 7 OR games_b >= 7) AND ABS(games_a - games_b) >= 1) THEN
            UPDATE "MatchSet"
            SET winner_team_id = CASE WHEN games_a > games_b THEN team_a ELSE team_b END
            WHERE id = current_set_id;

            SELECT
                COUNT(*) FILTER (WHERE winner_team_id = team_a),
                COUNT(*) FILTER (WHERE winner_team_id = team_b)
            INTO sets_a, sets_b
            FROM "MatchSet"
            WHERE match_id = p_match_id;

            sets_to_win := FLOOR(COALESCE(best_of_sets, 3)::numeric / 2)::integer + 1;

            UPDATE "MatchParticipant"
            SET sets_won = CASE
                WHEN team_id = team_a THEN sets_a
                WHEN team_id = team_b THEN sets_b
                ELSE sets_won
            END
            WHERE match_id = p_match_id;

            IF sets_a >= sets_to_win OR sets_b >= sets_to_win THEN
                UPDATE "Match"
                SET status = 'Completed',
                    winning_team_id = CASE WHEN sets_a > sets_b THEN team_a ELSE team_b END
                WHERE id = p_match_id;

                UPDATE "MatchParticipant"
                SET is_winner = CASE
                    WHEN team_id = CASE WHEN sets_a > sets_b THEN team_a ELSE team_b END THEN true
                    ELSE false
                END
                WHERE match_id = p_match_id;
            END IF;
        END IF;
    END IF;
END;
$procedure$
```

#### sp_register_match_set
```sql
CREATE OR REPLACE PROCEDURE public.sp_register_match_set(IN p_match_id integer, IN p_set_number integer, IN p_team_a_games integer, IN p_team_b_games integer, IN p_tie_break_a integer, IN p_tie_break_b integer, IN p_winner_team_id integer)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    PERFORM public.fn_crud_insert_json('MatchSet', jsonb_build_object(
        'match_id', p_match_id,
        'set_number', p_set_number,
        'team_a_games', p_team_a_games,
        'team_b_games', p_team_b_games,
        'tie_break_a', p_tie_break_a,
        'tie_break_b', p_tie_break_b,
        'winner_team_id', p_winner_team_id
    ));
END;
$procedure$
```

#### sp_start_match
```sql
CREATE OR REPLACE PROCEDURE public.sp_start_match(IN p_match_id integer)
 LANGUAGE plpgsql
AS $procedure$
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
$procedure$
```

#### sp_update_match_status
```sql
CREATE OR REPLACE PROCEDURE public.sp_update_match_status(IN p_match_id integer, IN p_status text)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    IF p_match_id IS NULL OR p_status NOT IN ('Scheduled', 'InProgress', 'Completed', 'Retired', 'Walkover', 'Suspended', 'Cancelled', 'Disqualified') THEN
        RAISE EXCEPTION 'Invalid match status payload.';
    END IF;

    PERFORM public.fn_crud_update_json('Match', 'id', p_match_id::text, jsonb_build_object('status', p_status));
END;
$procedure$
```

### Oficiales, sanciones y lesiones

#### sp_close_injury
```sql
CREATE OR REPLACE PROCEDURE public.sp_close_injury(IN p_injury_id integer, IN p_recovery_date date)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    PERFORM public.fn_crud_update_json('Injury', 'id', p_injury_id::text, jsonb_build_object(
        'recovery_date', p_recovery_date,
        'active', FALSE
    ));
END;
$procedure$
```

#### sp_create_injury
```sql
CREATE OR REPLACE PROCEDURE public.sp_create_injury(IN p_injury_type_id integer, IN p_injury_date date, IN p_description text)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    PERFORM public.fn_crud_insert_json('Injury', jsonb_build_object(
        'injury_type_id', p_injury_type_id,
        'injury_date', p_injury_date,
        'description', p_description,
        'active', TRUE
    ));
END;
$procedure$
```

#### sp_create_official
```sql
CREATE OR REPLACE PROCEDURE public.sp_create_official(IN p_first_name character varying, IN p_last_name character varying, IN p_nationality character varying, IN p_official_type character varying, IN p_certification_level character varying, IN p_license_number character varying)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    PERFORM public.fn_crud_insert_json('Official', jsonb_build_object(
        'first_name', p_first_name,
        'last_name', p_last_name,
        'nationality', p_nationality,
        'official_type', p_official_type,
        'certification_level', p_certification_level,
        'license_number', p_license_number,
        'is_active', TRUE
    ));
END;
$procedure$
```

#### sp_create_sanction
```sql
CREATE OR REPLACE PROCEDURE public.sp_create_sanction(IN p_tournament_id integer, IN p_match_id integer, IN p_violation_type_id integer, IN p_team_id integer, IN p_player_id character varying, IN p_official_id integer, IN p_sanction_type character varying, IN p_penalty_points integer, IN p_penalty_games integer, IN p_fine_amount numeric, IN p_currency character varying, IN p_notes text, IN p_created_by integer)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    PERFORM public.fn_crud_insert_json('Sanction', jsonb_build_object(
        'tournament_id', p_tournament_id,
        'match_id', p_match_id,
        'violation_type_id', p_violation_type_id,
        'team_id', p_team_id,
        'player_id', NULLIF(p_player_id, ''),
        'official_id', p_official_id,
        'sanction_type', p_sanction_type,
        'penalty_points', p_penalty_points,
        'penalty_games', p_penalty_games,
        'fine_amount', p_fine_amount,
        'currency', p_currency,
        'notes', p_notes,
        'created_by', p_created_by,
        'issued_by', p_created_by
    ));
END;
$procedure$
```

#### sp_create_sanction_appeal
```sql
CREATE OR REPLACE PROCEDURE public.sp_create_sanction_appeal(IN p_sanction_id integer, IN p_filed_by_player_id character varying, IN p_status character varying, IN p_notes text, IN p_created_by integer)
 LANGUAGE plpgsql
AS $procedure$
DECLARE
    target_table text;
BEGIN
    target_table := public.fn_crud_first_table(ARRAY['SanctionAppeal', 'Appeal']);
    IF target_table IS NULL THEN
        RAISE EXCEPTION 'Sanction appeal table not found.';
    END IF;
    PERFORM public.fn_crud_insert_json(target_table, jsonb_build_object(
        'sanction_id', p_sanction_id,
        'filed_by_player_id', NULLIF(p_filed_by_player_id, ''),
        'status', p_status,
        'notes', p_notes,
        'created_by', p_created_by,
        'filed_by_user_id', p_created_by
    ));
END;
$procedure$
```

### Auditoria y semillas/demo

#### sp_create_audit_log
```sql
CREATE OR REPLACE PROCEDURE public.sp_create_audit_log(IN p_user_id integer, IN p_tournament_id integer, IN p_action character varying, IN p_entity_table character varying, IN p_entity_id integer, IN p_entity_pk character varying, IN p_details jsonb, IN p_ip_address character varying)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    IF public.fn_crud_table_exists('AuditLog') THEN
        PERFORM public.fn_crud_insert_json('AuditLog', jsonb_build_object(
            'user_id', p_user_id,
            'tournament_id', p_tournament_id,
            'action', p_action,
            'entity_table', p_entity_table,
            'entity_id', p_entity_id,
            'entity_pk', p_entity_pk,
            'details', COALESCE(p_details, '{}'::jsonb),
            'ip_address', p_ip_address,
            'created_at', CURRENT_TIMESTAMP
        ));
    END IF;
END;
$procedure$
```

#### sp_seed_competition_demo_only
```sql
CREATE OR REPLACE PROCEDURE public.sp_seed_competition_demo_only()
 LANGUAGE plpgsql
AS $procedure$
DECLARE
    today date := CURRENT_DATE;
    pid text;
    tid integer;
    i integer;
    first_names text[] := ARRAY[
        'Mateo','Lucas','Nicolas','Samuel','Tomas','Emiliano','Sebastian','Martin',
        'Valeria','Camila','Isabella','Luciana','Sofia','Mariana','Renata','Gabriela',
        'Adrian','Daniel','Felipe','Joaquin','Andres','Bruno','Cristian','David'
    ];
    last_names text[] := ARRAY[
        'Rivera','Morales','Cortes','Vargas','Herrera','Rojas','Navarro','Salazar',
        'Torres','Castro','Mendoza','Pineda','Mejia','Arias','Lopez','Ramirez',
        'Ortega','Vega','Molina','Suarez','Peña','Muñoz','Cárdenas','Niño'
    ];
    genders text[] := ARRAY[
        'M','M','M','M','M','M','M','M',
        'F','F','F','F','F','F','F','F',
        'M','M','M','M','M','M','M','M'
    ];
BEGIN
    TRUNCATE
        "AuditLog",
        "SessionMatch",
        "MatchPlayerStat",
        "MatchTeamStat",
        "MatchPoint",
        "MatchGame",
        "MatchSet",
        "MatchOfficial",
        "MatchSchedule",
        "MatchRescheduleLog",
        "MatchParticipant",
        "SanctionAppeal",
        "Sanction",
        "MedicalReport",
        "PlayerInjury",
        "Injury",
        "InjuryType",
        "PlayerRanking",
        "PlayerCoach",
        "Coach",
        "PrizeRule",
        "RankingPointsRule",
        "Standing",
        "Session",
        "Match",
        "Entry",
        "Round",
        "SubCategory",
        "Category",
        "Court",
        "Event",
        "Tournament",
        "TeamMember",
        "Team",
        "Official",
        "ViolationType",
        "Player"
    RESTART IDENTITY CASCADE;

    INSERT INTO "Tournament" (id, name, year, start_date, end_date, location, surface, description, status)
    VALUES
        (8, 'Grand Slam Demo Pendiente - Inscripciones', EXTRACT(YEAR FROM today)::integer, today + 10, today + 23, 'Victory Tennis Park, Medellín, COL', 'Hard', 'Torneo demo con cuadros completos e incompletos para probar inscripciones.', 'Pendiente por inscripciones'),
        (9, 'Victory Grand Slam Completo - Resultados', EXTRACT(YEAR FROM today)::integer, today - 20, today - 7, 'Victory Tennis Park, Medellín, COL', 'Clay', 'Torneo demo completo con resultados y bracket finalizado.', 'Finalizado');

    INSERT INTO "Court" (id, tournament_id, name, capacity, surface, indoor, location)
    VALUES
        (1, 8, 'Victory Central Court', 6500, 'Hard', false, 'Medellín'),
        (2, 8, 'Victory Court 2', 1800, 'Hard', false, 'Medellín'),
        (3, 9, 'Championship Court', 7200, 'Clay', false, 'Medellín');

    FOR i IN 1..array_length(first_names, 1) LOOP
        pid := 'P-DEMO-' || lpad(i::text, 3, '0');
        INSERT INTO "Player" (
            id, document_type, issuer_country, first_name, last_name, gender, birth_date,
            country_code, height_cm, weight_kg, hand, turned_pro_year, biography
        )
        VALUES (
            pid,
            'Passport',
            'COL',
            first_names[i],
            last_names[i],
            genders[i]::gender_type,
            DATE '1996-01-01' + (i * 280),
            'COL',
            174 + (i % 18),
            66 + (i % 22),
            CASE WHEN i % 4 = 0 THEN 'L'::hand_type ELSE 'R'::hand_type END,
            2016 + (i % 7),
            'Jugador demo para pruebas de torneo.'
        );

        INSERT INTO "Team" (id, name, notes)
        VALUES (i, first_names[i] || ' ' || last_names[i], 'Equipo singles demo')
        RETURNING id INTO tid;

        INSERT INTO "TeamMember" (team_id, player_id, role, start_date)
        VALUES (tid, pid, 'Player', today - 30);
    END LOOP;

    INSERT INTO "Category" (id, tournament_id, name, gender, mode, description)
    VALUES
        (10, 8, 'Men Singles', 'M', 'Singles', 'Categoría masculina demo.'),
        (11, 8, 'Women Singles', 'F', 'Singles', 'Categoría femenina demo.'),
        (12, 9, 'Men Singles', 'M', 'Singles', 'Categoría masculina completa.');

    INSERT INTO "SubCategory" (id, category_id, name, draw_size, description)
    VALUES
        (10, 10, 'Main Draw Demo 8', 8, 'Cuadro principal incompleto: faltan dos equipos.'),
        (11, 10, 'Qualifying Demo 4', 4, 'Cuadro clasificatorio completo.'),
        (12, 11, 'Women Main Draw Demo 8', 8, 'Cuadro femenino incompleto: faltan tres equipos.'),
        (13, 11, 'Women Mini Draw 4', 4, 'Cuadro femenino completo.'),
        (20, 12, 'Championship Draw 8', 8, 'Cuadro completo con resultados.');

    INSERT INTO "Entry" (id, subcategory_id, team_id, seed, ranking_at_entry, qualifying_method)
    VALUES
        (1, 10, 1, 1, 11, 'Direct'),
        (2, 10, 2, 2, 14, 'Direct'),
        (3, 10, 3, 3, 18, 'Wildcard'),
        (4, 10, 4, 4, 22, 'Qualifier'),
        (5, 10, 5, 5, 31, 'Direct'),
        (6, 10, 6, 6, 39, 'Qualifier'),
        (7, 11, 7, 1, 48, 'Direct'),
        (8, 11, 8, 2, 52, 'Direct'),
        (9, 11, 17, 3, 67, 'Qualifier'),
        (10, 11, 18, 4, 72, 'Wildcard'),
        (11, 12, 9, 1, 9, 'Direct'),
        (12, 12, 10, 2, 15, 'Direct'),
        (13, 12, 11, 3, 20, 'Wildcard'),
        (14, 12, 12, 4, 26, 'Qualifier'),
        (15, 12, 13, 5, 33, 'Direct'),
        (16, 13, 14, 1, 41, 'Direct'),
        (17, 13, 15, 2, 45, 'Direct'),
        (18, 13, 16, 3, 58, 'Wildcard'),
        (19, 13, 9, 4, 62, 'Qualifier'),
        (20, 20, 19, 1, 4, 'Direct'),
        (21, 20, 20, 2, 8, 'Direct'),
        (22, 20, 21, 3, 12, 'Direct'),
        (23, 20, 22, 4, 16, 'Direct'),
        (24, 20, 23, 5, 21, 'Wildcard'),
        (25, 20, 24, 6, 25, 'Qualifier'),
        (26, 20, 1, 7, 30, 'Direct'),
        (27, 20, 2, 8, 36, 'Qualifier');

    INSERT INTO "Round" (id, subcategory_id, round_name, round_number, best_of_sets, description)
    VALUES
        (20, 20, 'Quarterfinal', 1, 5, 'Cuartos de final.'),
        (21, 20, 'Semifinal', 2, 5, 'Semifinal.'),
        (22, 20, 'Final', 3, 5, 'Final.'),
        (30, 11, 'Semifinal', 1, 5, 'Ronda generada para cuadro completo.'),
        (31, 11, 'Final', 2, 5, 'Final clasificatoria.'),
        (32, 13, 'Semifinal', 1, 3, 'Ronda generada para cuadro completo.'),
        (33, 13, 'Final', 2, 3, 'Final femenina demo.');

    INSERT INTO "Match" (id, round_id, scheduled_datetime, court_id, status, winning_team_id, notes)
    VALUES
        (100, 20, today - 18 + TIME '10:00', 3, 'Completed', 19, 'Quarterfinal completa.'),
        (101, 20, today - 18 + TIME '12:00', 3, 'Completed', 22, 'Quarterfinal completa.'),
        (102, 20, today - 18 + TIME '14:00', 3, 'Completed', 23, 'Quarterfinal completa.'),
        (103, 20, today - 18 + TIME '16:00', 3, 'Completed', 2, 'Quarterfinal completa.'),
        (104, 21, today - 15 + TIME '11:00', 3, 'Completed', 19, 'Semifinal completa.'),
        (105, 21, today - 15 + TIME '15:00', 3, 'Completed', 23, 'Semifinal completa.'),
        (106, 22, today - 12 + TIME '14:00', 3, 'InProgress', 19, 'Final completa.');

    INSERT INTO "MatchParticipant" (match_id, team_id, side, sets_won, games_won, points_won, is_winner)
    VALUES
        (100, 19, 'A', 3, 18, 96, true), (100, 20, 'B', 1, 12, 77, false),
        (101, 21, 'A', 2, 15, 83, false), (101, 22, 'B', 3, 17, 91, true),
        (102, 23, 'A', 3, 18, 98, true), (102, 24, 'B', 0, 9, 61, false),
        (103, 1, 'A', 1, 13, 72, false), (103, 2, 'B', 3, 17, 94, true),
        (104, 19, 'A', 3, 18, 102, true), (104, 22, 'B', 2, 16, 95, false),
        (105, 23, 'A', 3, 18, 99, true), (105, 2, 'B', 1, 13, 76, false),
        (106, 19, 'A', 3, 19, 108, true), (106, 23, 'B', 2, 16, 101, false);

    INSERT INTO "MatchSet" (match_id, set_number, team_a_games, team_b_games, tie_break_a, tie_break_b, winner_team_id)
    VALUES
        (106, 1, 6, 4, NULL, NULL, 19),
        (106, 2, 4, 6, NULL, NULL, 23),
        (106, 3, 7, 6, 7, 4, 19),
        (106, 4, 5, 7, NULL, NULL, 23),
        (106, 5, 6, 3, NULL, NULL, 19);

    UPDATE "Match"
    SET status = 'Completed'
    WHERE id = 106;

    INSERT INTO "InjuryType" (id, name, description)
    VALUES
        (1, 'Ankle Sprain', 'Esguince de tobillo.'),
        (2, 'Shoulder Strain', 'Molestia de hombro.');

    INSERT INTO "ViolationType" (id, code, name, category, default_sanction_type, description)
    VALUES
        (1, 'TIME-001', 'Time Violation', 'Behaviour', 'Warning', 'Exceso de tiempo entre puntos.'),
        (2, 'CONDUCT-001', 'Unsportsmanlike Conduct', 'Behaviour', 'Point Penalty', 'Conducta antideportiva.');

    PERFORM setval(pg_get_serial_sequence('"Tournament"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Tournament"), true);
    PERFORM setval(pg_get_serial_sequence('"Court"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Court"), true);
    PERFORM setval(pg_get_serial_sequence('"Category"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Category"), true);
    PERFORM setval(pg_get_serial_sequence('"SubCategory"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "SubCategory"), true);
    PERFORM setval(pg_get_serial_sequence('"Round"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Round"), true);
    PERFORM setval(pg_get_serial_sequence('"Team"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Team"), true);
    PERFORM setval(pg_get_serial_sequence('"Entry"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Entry"), true);
    PERFORM setval(pg_get_serial_sequence('"Match"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Match"), true);
    PERFORM setval(pg_get_serial_sequence('"MatchSet"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "MatchSet"), true);
    PERFORM setval(pg_get_serial_sequence('"InjuryType"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "InjuryType"), true);
    PERFORM setval(pg_get_serial_sequence('"ViolationType"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "ViolationType"), true);
END;
$procedure$
```

#### sp_seed_grand_slam_demo_data
```sql
CREATE OR REPLACE PROCEDURE public.sp_seed_grand_slam_demo_data()
 LANGUAGE plpgsql
AS $procedure$
DECLARE
    today date := CURRENT_DATE;
BEGIN
    TRUNCATE
        "AuditLog",
        "SessionMatch",
        "MatchPlayerStat",
        "MatchTeamStat",
        "MatchPoint",
        "MatchGame",
        "MatchSet",
        "MatchOfficial",
        "MatchSchedule",
        "MatchRescheduleLog",
        "MatchParticipant",
        "SanctionAppeal",
        "Sanction",
        "MedicalReport",
        "PlayerInjury",
        "Injury",
        "InjuryType",
        "PlayerRanking",
        "PlayerCoach",
        "Coach",
        "PrizeRule",
        "RankingPointsRule",
        "Standing",
        "Session",
        "Match",
        "Entry",
        "Round",
        "SubCategory",
        "Category",
        "Court",
        "Event",
        "Tournament",
        "TeamMember",
        "Team",
        "Official",
        "ViolationType",
        "Player"
    RESTART IDENTITY CASCADE;

    INSERT INTO "Tournament" (id, name, year, start_date, end_date, location, surface, description)
    VALUES
        (1, 'Australian Open', 2026, DATE '2026-01-12', DATE '2026-01-25', 'Melbourne Park, Melbourne, Australia', 'Hard', 'Primer Grand Slam de la temporada.'),
        (2, 'Roland-Garros', 2026, DATE '2026-05-24', DATE '2026-06-07', 'Stade Roland-Garros, Paris, France', 'Clay', 'Grand Slam sobre arcilla.'),
        (3, 'The Championships, Wimbledon', 2026, DATE '2026-06-29', DATE '2026-07-12', 'All England Club, London, United Kingdom', 'Grass', 'Grand Slam sobre cesped.'),
        (4, 'US Open', 2026, DATE '2026-08-24', DATE '2026-09-13', 'USTA Billie Jean King National Tennis Center, New York, USA', 'Hard', 'Grand Slam de cierre de temporada.'),
        (5, 'Torneo Prueba Incompleto - Operacion Hoy', EXTRACT(YEAR FROM today)::integer, today - 1, today + 7, 'Centro de Pruebas Victory, Medellin, COL', 'Hard', 'Torneo de prueba con partidos programados para hoy.'),
        (6, 'Torneo Incompleto Validacion - Match Lab', EXTRACT(YEAR FROM today)::integer, today, today + 5, 'Cancha Laboratorio Victory, Medellin, COL', 'Clay', 'Torneo incompleto para validar trazabilidad y desarrollo de partido.');

    INSERT INTO "Court" (id, tournament_id, name, capacity, surface, indoor, location)
    VALUES
        (1, 1, 'Rod Laver Arena', 14820, 'Hard', false, 'Melbourne Park'),
        (2, 2, 'Court Philippe-Chatrier', 15000, 'Clay', false, 'Paris'),
        (3, 3, 'Centre Court', 14979, 'Grass', false, 'London'),
        (4, 4, 'Arthur Ashe Stadium', 23771, 'Hard', false, 'New York'),
        (5, 5, 'Cancha Central Prueba', 5000, 'Hard', false, 'Medellin'),
        (6, 5, 'Cancha 2 Prueba', 1500, 'Hard', false, 'Medellin'),
        (7, 6, 'Cancha Laboratorio 1', 800, 'Clay', false, 'Medellin');

    INSERT INTO "Player" (id, document_type, issuer_country, first_name, last_name, gender, birth_date, country_code, height_cm, weight_kg, hand, turned_pro_year, biography)
    VALUES
        ('P-SRB-001', 'Passport', 'SRB', 'Novak', 'Djokovic', 'M', DATE '1987-05-22', 'SRB', 188, 77, 'R', 2003, 'Campeon multiple de Grand Slam.'),
        ('P-ESP-002', 'Passport', 'ESP', 'Carlos', 'Alcaraz', 'M', DATE '2003-05-05', 'ESP', 183, 74, 'R', 2018, 'Jugador espanol de elite.'),
        ('P-ITA-003', 'Passport', 'ITA', 'Jannik', 'Sinner', 'M', DATE '2001-08-16', 'ITA', 191, 76, 'R', 2018, 'Jugador italiano de alto rendimiento.'),
        ('P-RUS-004', 'Passport', 'RUS', 'Daniil', 'Medvedev', 'M', DATE '1996-02-11', 'RUS', 198, 83, 'R', 2014, 'Especialista en canchas duras.'),
        ('P-POL-005', 'Passport', 'POL', 'Iga', 'Swiatek', 'F', DATE '2001-05-31', 'POL', 176, 65, 'R', 2016, 'Campeona de Grand Slam.'),
        ('P-BLR-006', 'Passport', 'BLR', 'Aryna', 'Sabalenka', 'F', DATE '1998-05-05', 'BLR', 182, 80, 'R', 2015, 'Potencia ofensiva del circuito.'),
        ('P-USA-007', 'Passport', 'USA', 'Coco', 'Gauff', 'F', DATE '2004-03-13', 'USA', 175, 59, 'R', 2018, 'Campeona estadounidense.'),
        ('P-KAZ-008', 'Passport', 'KAZ', 'Elena', 'Rybakina', 'F', DATE '1999-06-17', 'KAZ', 184, 72, 'R', 2016, 'Campeona sobre cesped.'),
        ('P-COL-009', 'CC', 'COL', 'Juan', 'Ortiz', 'M', DATE '1999-04-12', 'COL', 181, 73, 'R', 2019, 'Jugador invitado para pruebas operativas.'),
        ('P-COL-010', 'CC', 'COL', 'Diego', 'Castillo', 'M', DATE '1998-09-20', 'COL', 185, 78, 'R', 2018, 'Jugador invitado para pruebas operativas.'),
        ('P-COL-011', 'CC', 'COL', 'Hugo', 'Moreau', 'M', DATE '2000-01-08', 'COL', 179, 70, 'L', 2020, 'Jugador invitado para pruebas operativas.'),
        ('P-COL-012', 'CC', 'COL', 'Noah', 'Brown', 'M', DATE '2001-11-03', 'COL', 188, 82, 'R', 2021, 'Jugador invitado para pruebas operativas.');

    INSERT INTO "Team" (id, name, notes)
    VALUES
        (1, 'Djokovic', 'Singles'),
        (2, 'Alcaraz', 'Singles'),
        (3, 'Sinner', 'Singles'),
        (4, 'Medvedev', 'Singles'),
        (5, 'Swiatek', 'Singles'),
        (6, 'Sabalenka', 'Singles'),
        (7, 'Gauff', 'Singles'),
        (8, 'Rybakina', 'Singles'),
        (9, 'Juan Ortiz', 'Singles prueba'),
        (10, 'Diego Castillo', 'Singles prueba'),
        (11, 'Hugo Moreau', 'Singles prueba'),
        (12, 'Noah Brown', 'Singles prueba');

    INSERT INTO "TeamMember" (team_id, player_id, role, start_date)
    VALUES
        (1, 'P-SRB-001', 'Player', DATE '2026-01-01'),
        (2, 'P-ESP-002', 'Player', DATE '2026-01-01'),
        (3, 'P-ITA-003', 'Player', DATE '2026-01-01'),
        (4, 'P-RUS-004', 'Player', DATE '2026-01-01'),
        (5, 'P-POL-005', 'Player', DATE '2026-01-01'),
        (6, 'P-BLR-006', 'Player', DATE '2026-01-01'),
        (7, 'P-USA-007', 'Player', DATE '2026-01-01'),
        (8, 'P-KAZ-008', 'Player', DATE '2026-01-01'),
        (9, 'P-COL-009', 'Player', today - 1),
        (10, 'P-COL-010', 'Player', today - 1),
        (11, 'P-COL-011', 'Player', today),
        (12, 'P-COL-012', 'Player', today);

    INSERT INTO "Category" (id, tournament_id, name, gender, mode, description)
    VALUES
        (1, 1, 'Men Singles', 'M', 'Singles', 'Cuadro masculino individual.'),
        (2, 1, 'Women Singles', 'F', 'Singles', 'Cuadro femenino individual.'),
        (3, 2, 'Men Singles', 'M', 'Singles', 'Cuadro masculino individual.'),
        (4, 2, 'Women Singles', 'F', 'Singles', 'Cuadro femenino individual.'),
        (5, 3, 'Men Singles', 'M', 'Singles', 'Cuadro masculino individual.'),
        (6, 4, 'Men Singles', 'M', 'Singles', 'Cuadro masculino individual.'),
        (7, 5, 'Men Singles', 'M', 'Singles', 'Categoria principal de prueba.'),
        (8, 6, 'Men Singles', 'M', 'Singles', 'Categoria incompleta para validacion.');

    INSERT INTO "SubCategory" (id, category_id, name, draw_size, description)
    VALUES
        (1, 1, 'Main Draw Men', 128, 'Cuadro principal masculino Australian Open.'),
        (2, 2, 'Main Draw Women', 128, 'Cuadro principal femenino Australian Open.'),
        (3, 3, 'Main Draw Men', 128, 'Cuadro principal masculino Roland-Garros.'),
        (4, 4, 'Main Draw Women', 128, 'Cuadro principal femenino Roland-Garros.'),
        (5, 5, 'Main Draw Men', 128, 'Cuadro principal masculino Wimbledon.'),
        (6, 6, 'Main Draw Men', 128, 'Cuadro principal masculino US Open.'),
        (7, 7, 'Main Draw Test', 16, 'Cuadro de prueba para partidos del dia.'),
        (8, 8, 'Qualification Test', 8, 'Cuadro incompleto para validar flujos.');

    INSERT INTO "Round" (id, subcategory_id, round_name, round_number, best_of_sets, description)
    VALUES
        (1, 1, 'Round 1', 1, 5, 'Primera ronda.'),
        (2, 3, 'Round 1', 1, 5, 'Primera ronda.'),
        (3, 5, 'Round 1', 1, 5, 'Primera ronda.'),
        (4, 6, 'Round 1', 1, 5, 'Primera ronda.'),
        (5, 7, 'Round 1', 1, 3, 'Primera ronda del torneo de prueba.'),
        (6, 7, 'Quarterfinal', 2, 3, 'Cuartos de final del torneo de prueba.'),
        (7, 8, 'Round 1', 1, 3, 'Primera ronda incompleta.'),
        (8, 8, 'Final', 2, 3, 'Final incompleta de validacion.');

    INSERT INTO "Entry" (id, subcategory_id, team_id, seed, ranking_at_entry, qualifying_method)
    VALUES
        (1, 1, 1, 1, 1, 'Direct'),
        (2, 1, 2, 2, 2, 'Direct'),
        (3, 3, 3, 1, 1, 'Direct'),
        (4, 3, 4, 2, 4, 'Direct'),
        (5, 4, 5, 1, 1, 'Direct'),
        (6, 4, 6, 2, 2, 'Direct'),
        (7, 7, 9, 1, 12, 'Wildcard'),
        (8, 7, 10, 2, 18, 'Wildcard'),
        (9, 7, 11, 3, 24, 'Qualifier'),
        (10, 7, 12, 4, 27, 'Qualifier'),
        (11, 8, 9, 1, 12, 'Wildcard'),
        (12, 8, 10, 2, 18, 'Qualifier');

    INSERT INTO "Match" (id, round_id, scheduled_datetime, court_id, status, winning_team_id, notes)
    VALUES
        (1, 5, today + TIME '10:00', 5, 'Scheduled', NULL, 'Partido de prueba disponible para iniciar hoy.'),
        (2, 5, today + TIME '12:00', 6, 'Scheduled', NULL, 'Segundo partido de prueba disponible para iniciar hoy.'),
        (3, 6, today + TIME '15:00', 5, 'InProgress', NULL, 'Partido ya iniciado para validar marcador en vivo.'),
        (4, 7, today + TIME '16:30', 7, 'Scheduled', NULL, 'Partido incompleto de validacion para hoy.'),
        (5, 2, DATE '2026-05-25' + TIME '11:00', 2, 'Scheduled', NULL, 'Partido de Roland-Garros programado.'),
        (6, 3, DATE '2026-06-29' + TIME '13:00', 3, 'Scheduled', NULL, 'Partido de Wimbledon programado.');

    INSERT INTO "MatchParticipant" (match_id, team_id, side, sets_won, games_won, points_won, is_winner)
    VALUES
        (1, 9, 'A', 0, 0, 0, false),
        (1, 10, 'B', 0, 0, 0, false),
        (2, 11, 'A', 0, 0, 0, false),
        (2, 12, 'B', 0, 0, 0, false),
        (3, 9, 'A', 1, 6, 0, false),
        (3, 11, 'B', 0, 4, 0, false),
        (4, 9, 'A', 0, 0, 0, false),
        (4, 10, 'B', 0, 0, 0, false),
        (5, 3, 'A', 0, 0, 0, false),
        (5, 4, 'B', 0, 0, 0, false),
        (6, 1, 'A', 0, 0, 0, false),
        (6, 2, 'B', 0, 0, 0, false);

    INSERT INTO "MatchSet" (id, match_id, set_number, team_a_games, team_b_games, tie_break_a, tie_break_b, winner_team_id)
    VALUES
        (1, 3, 1, 6, 4, NULL, NULL, 9);

    INSERT INTO "Session" (id, tournament_id, name, start_datetime, end_datetime, status, notes)
    VALUES
        (1, 5, 'Jornada de prueba - manana', today + TIME '09:00', today + TIME '13:30', 'scheduled', 'Bloque para validar inicio de partidos.'),
        (2, 5, 'Jornada de prueba - tarde', today + TIME '14:00', today + TIME '18:00', 'scheduled', 'Bloque para validar partido en progreso.'),
        (3, 6, 'Jornada incompleta', today + TIME '16:00', today + TIME '19:00', 'scheduled', 'Bloque de validacion incompleto.');

    INSERT INTO "SessionMatch" (session_id, match_id, order_in_session)
    VALUES
        (1, 1, 1),
        (1, 2, 2),
        (2, 3, 1),
        (3, 4, 1);

    INSERT INTO "Official" (id, first_name, last_name, nationality, official_type, certification_level, license_number, is_active)
    VALUES
        (1, 'Carlos', 'Bernal', 'COL', 'Chair Umpire', 'Gold Badge', 'OFF-COL-001', true),
        (2, 'Laura', 'Mendez', 'COL', 'Referee', 'Silver Badge', 'OFF-COL-002', true),
        (3, 'Emma', 'Wilson', 'GBR', 'Line Umpire', 'International', 'OFF-GBR-003', true);

    INSERT INTO "MatchOfficial" (match_id, official_id, role, assigned_by_user_id, assigned_at)
    VALUES
        (1, 1, 'Chair Umpire', 2, now()),
        (2, 3, 'Line Umpire', 2, now()),
        (3, 1, 'Chair Umpire', 2, now()),
        (4, 2, 'Referee', 2, now());

    INSERT INTO "InjuryType" (id, name, description)
    VALUES
        (1, 'Ankle Sprain', 'Esguince de tobillo.'),
        (2, 'Back Pain', 'Dolor lumbar.'),
        (3, 'Shoulder Strain', 'Molestia en hombro.');

    INSERT INTO "Injury" (id, injury_type_id, injury_date, recovery_date, description, active)
    VALUES
        (1, 1, today - 2, NULL, 'Molestia reportada durante calentamiento.', true),
        (2, 2, today - 10, today - 1, 'Dolor lumbar recuperado.', false);

    INSERT INTO "PlayerInjury" (player_id, injury_id, assigned_at)
    VALUES
        ('P-COL-010', 1, today - 2),
        ('P-ESP-002', 2, today - 10);

    INSERT INTO "ViolationType" (id, code, name, category, default_sanction_type, description)
    VALUES
        (1, 'TIME-001', 'Time Violation', 'Behaviour', 'Warning', 'Exceso de tiempo entre puntos.'),
        (2, 'CONDUCT-001', 'Unsportsmanlike Conduct', 'Behaviour', 'Point Penalty', 'Conducta antideportiva.'),
        (3, 'COACH-001', 'Illegal Coaching', 'Coaching', 'Warning', 'Instrucciones no permitidas durante el partido.');

    INSERT INTO "Sanction" (id, tournament_id, match_id, violation_type_id, player_id, team_id, official_id, issued_by_user_id, sanction_type, penalty_points, penalty_games, fine_amount, currency, is_active, issued_at, notes)
    VALUES
        (1, 5, 3, 1, 'P-COL-011', NULL, NULL, 2, 'Warning', 0, 0, 0, 'USD', true, now(), 'Advertencia de tiempo durante prueba.'),
        (2, 5, 3, 2, NULL, 9, NULL, 2, 'Point Penalty', 1, 0, 0, 'USD', true, now(), 'Penalizacion de punto para validar disciplina.');

    INSERT INTO "PlayerRanking" (id, player_id, ranking_date, rank_value, ranking_points)
    VALUES
        (1, 'P-SRB-001', today, 3, 6800),
        (2, 'P-ESP-002', today, 2, 8600),
        (3, 'P-ITA-003', today, 1, 9400),
        (4, 'P-POL-005', today, 1, 9200),
        (5, 'P-COL-009', today, 12, 1200),
        (6, 'P-COL-010', today, 18, 900);

    PERFORM setval(pg_get_serial_sequence('"Tournament"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Tournament"), true);
    PERFORM setval(pg_get_serial_sequence('"Court"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Court"), true);
    PERFORM setval(pg_get_serial_sequence('"Category"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Category"), true);
    PERFORM setval(pg_get_serial_sequence('"SubCategory"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "SubCategory"), true);
    PERFORM setval(pg_get_serial_sequence('"Round"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Round"), true);
    PERFORM setval(pg_get_serial_sequence('"Team"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Team"), true);
    PERFORM setval(pg_get_serial_sequence('"Entry"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Entry"), true);
    PERFORM setval(pg_get_serial_sequence('"Match"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Match"), true);
    PERFORM setval(pg_get_serial_sequence('"MatchSet"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "MatchSet"), true);
    PERFORM setval(pg_get_serial_sequence('"Session"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Session"), true);
    PERFORM setval(pg_get_serial_sequence('"Official"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Official"), true);
    PERFORM setval(pg_get_serial_sequence('"InjuryType"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "InjuryType"), true);
    PERFORM setval(pg_get_serial_sequence('"Injury"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Injury"), true);
    PERFORM setval(pg_get_serial_sequence('"ViolationType"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "ViolationType"), true);
    PERFORM setval(pg_get_serial_sequence('"Sanction"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Sanction"), true);
    PERFORM setval(pg_get_serial_sequence('"PlayerRanking"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "PlayerRanking"), true);
END;
$procedure$
```

### Otros

#### sp_create_event
```sql
CREATE OR REPLACE PROCEDURE public.sp_create_event(IN p_tournament_id integer, IN p_subcategory_id integer, IN p_event_type character varying, IN p_event_datetime timestamp without time zone, IN p_location character varying, IN p_description text)
 LANGUAGE plpgsql
AS $procedure$
BEGIN
    INSERT INTO "Event" (
        "tournament_id", "subcategory_id", "event_type", "event_datetime", "location", "description"
    )
    VALUES (
        p_tournament_id, p_subcategory_id, p_event_type, p_event_datetime, p_location, p_description
    );
END;
$procedure$
```

## Funciones

### Seguridad y usuarios

#### sp_authenticate_user_json
```sql
CREATE OR REPLACE FUNCTION public.sp_authenticate_user_json(p_email text)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    user_id_col text;
    email_col text;
    password_col text;
    full_name_col text;
    active_col text;
    role_id_col text;
    role_name_col text;
    ur_user_col text;
    ur_role_col text;
    select_sql text;
    join_sql text := '';
    result jsonb;
BEGIN
    user_id_col := public.fn_read_first_column('UserAccount', ARRAY['user_id', 'id']);
    email_col := public.fn_read_first_column('UserAccount', ARRAY['email', 'user_email']);
    password_col := public.fn_read_first_column('UserAccount', ARRAY['password_hash', 'password']);
    full_name_col := public.fn_read_first_column('UserAccount', ARRAY['full_name', 'name', 'username']);
    active_col := public.fn_read_first_column('UserAccount', ARRAY['is_active', 'active', 'status']);
    role_id_col := public.fn_read_first_column('Role', ARRAY['role_id', 'id']);
    role_name_col := public.fn_read_first_column('Role', ARRAY['role_name', 'name']);
    ur_user_col := public.fn_read_first_column('UserRole', ARRAY['user_id', 'account_id']);
    ur_role_col := public.fn_read_first_column('UserRole', ARRAY['role_id']);

    IF user_id_col IS NULL OR email_col IS NULL OR password_col IS NULL THEN
        RETURN NULL;
    END IF;

    select_sql := format(
        'SELECT ua.%1$I AS user_id, ua.%2$I AS email, ua.%3$I AS password_hash, %4$s AS full_name, %5$s AS is_active, %6$s AS role_name FROM %7$I ua',
        user_id_col,
        email_col,
        password_col,
        CASE WHEN full_name_col IS NOT NULL THEN format('ua.%I', full_name_col) ELSE 'NULL' END,
        CASE WHEN active_col IS NOT NULL THEN format('ua.%I', active_col) ELSE 'TRUE' END,
        CASE WHEN role_name_col IS NOT NULL AND role_id_col IS NOT NULL AND ur_user_col IS NOT NULL AND ur_role_col IS NOT NULL THEN format('r.%I', role_name_col) ELSE 'NULL' END,
        'UserAccount'
    );

    IF role_name_col IS NOT NULL AND role_id_col IS NOT NULL AND ur_user_col IS NOT NULL AND ur_role_col IS NOT NULL THEN
        join_sql := format(
            ' LEFT JOIN %I ur ON ur.%I = ua.%I LEFT JOIN %I r ON r.%I = ur.%I',
            'UserRole',
            ur_user_col,
            user_id_col,
            'Role',
            role_id_col,
            ur_role_col
        );
    END IF;

    EXECUTE 'SELECT to_jsonb(auth_row) FROM ('
        || select_sql
        || join_sql
        || format(' WHERE lower(cast(ua.%I AS text)) = lower($1) LIMIT 1', email_col)
        || ') auth_row'
    INTO result
    USING p_email;
    RETURN result;
END;
$function$
```

#### trg_normalize_user_account
```sql
CREATE OR REPLACE FUNCTION public.trg_normalize_user_account()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.email := lower(btrim(NEW.email));
    RETURN NEW;
END;
$function$
```

### Torneos y estructura competitiva

#### fn_tournament_entries_complete
```sql
CREATE OR REPLACE FUNCTION public.fn_tournament_entries_complete(p_tournament_id integer)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
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
$function$
```

#### sp_categories_by_tournament_json
```sql
CREATE OR REPLACE FUNCTION public.sp_categories_by_tournament_json(p_tournament_id integer, p_limit integer DEFAULT 300)
 RETURNS SETOF jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    safe_limit integer := LEAST(GREATEST(COALESCE(p_limit, 300), 1), 1000);
BEGIN
    IF p_tournament_id IS NULL THEN
        RETURN QUERY SELECT * FROM public.sp_categories_overview_json(safe_limit);
        RETURN;
    END IF;

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
            WHERE c.tournament_id = $1
            ORDER BY c.name, c.id
            LIMIT %3$s
        ) row_data',
        'Category',
        'Tournament',
        safe_limit
    )
    USING p_tournament_id;
END;
$function$
```

#### sp_entry_options_by_round_json
```sql
CREATE OR REPLACE FUNCTION public.sp_entry_options_by_round_json(p_round_id integer)
 RETURNS SETOF jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
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
$function$
```

#### sp_rounds_by_tournament_json
```sql
CREATE OR REPLACE FUNCTION public.sp_rounds_by_tournament_json(p_tournament_id integer, p_limit integer DEFAULT 300)
 RETURNS SETOF jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    safe_limit integer := LEAST(GREATEST(COALESCE(p_limit, 300), 1), 1000);
BEGIN
    IF p_tournament_id IS NULL THEN
        RETURN QUERY SELECT * FROM public.sp_rounds_overview_json(safe_limit);
        RETURN;
    END IF;

    RETURN QUERY EXECUTE format(
        'SELECT to_jsonb(row_data)
        FROM (
            SELECT
                r.id,
                r.round_name,
                r.round_number,
                r.best_of_sets,
                r.subcategory_id,
                COALESCE(sc.name, ''-'') AS cuadro,
                COALESCE(c.name, ''-'') AS categoria,
                c.id AS category_id,
                COALESCE(t.name, ''-'') AS torneo,
                r.description
            FROM %1$I r
            LEFT JOIN %2$I sc ON sc.id = r.subcategory_id
            LEFT JOIN %3$I c ON c.id = sc.category_id
            LEFT JOIN %4$I t ON t.id = c.tournament_id
            WHERE c.tournament_id = $1
            ORDER BY c.id, sc.id, r.round_number, r.id
            LIMIT %5$s
        ) row_data',
        'Round',
        'SubCategory',
        'Category',
        'Tournament',
        safe_limit
    )
    USING p_tournament_id;
END;
$function$
```

#### sp_rounds_overview_json
```sql
CREATE OR REPLACE FUNCTION public.sp_rounds_overview_json(p_limit integer DEFAULT 300)
 RETURNS SETOF jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    safe_limit integer := LEAST(GREATEST(COALESCE(p_limit, 300), 1), 1000);
BEGIN
    IF NOT public.fn_crud_table_exists('Round') THEN
        RETURN;
    END IF;

    RETURN QUERY EXECUTE format(
        'SELECT to_jsonb(row_data)
        FROM (
            SELECT
                r.id,
                r.round_name,
                r.round_number,
                r.best_of_sets,
                r.subcategory_id,
                COALESCE(sc.name, ''-'') AS cuadro,
                COALESCE(c.name, ''-'') AS categoria,
                c.id AS category_id,
                COALESCE(t.name, ''-'') AS torneo,
                r.description
            FROM %1$I r
            LEFT JOIN %2$I sc ON sc.id = r.subcategory_id
            LEFT JOIN %3$I c ON c.id = sc.category_id
            LEFT JOIN %4$I t ON t.id = c.tournament_id
            ORDER BY t.name NULLS LAST, c.id, sc.id, r.round_number, r.id
            LIMIT %5$s
        ) row_data',
        'Round',
        'SubCategory',
        'Category',
        'Tournament',
        safe_limit
    );
END;
$function$
```

#### sp_subcategories_by_tournament_json
```sql
CREATE OR REPLACE FUNCTION public.sp_subcategories_by_tournament_json(p_tournament_id integer, p_limit integer DEFAULT 300)
 RETURNS SETOF jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    safe_limit integer := LEAST(GREATEST(COALESCE(p_limit, 300), 1), 1000);
BEGIN
    IF p_tournament_id IS NULL THEN
        RETURN QUERY SELECT * FROM public.sp_subcategories_overview_json(safe_limit);
        RETURN;
    END IF;

    RETURN QUERY EXECUTE format(
        'SELECT to_jsonb(row_data)
        FROM (
            SELECT
                sc.id,
                sc.name,
                sc.category_id,
                COALESCE(c.name, ''-'') AS categoria,
                COALESCE(t.name, ''-'') AS torneo,
                sc.draw_size,
                sc.description
            FROM %1$I sc
            LEFT JOIN %2$I c ON c.id = sc.category_id
            LEFT JOIN %3$I t ON t.id = c.tournament_id
            WHERE c.tournament_id = $1
            ORDER BY c.id, sc.name, sc.id
            LIMIT %4$s
        ) row_data',
        'SubCategory',
        'Category',
        'Tournament',
        safe_limit
    )
    USING p_tournament_id;
END;
$function$
```

#### sp_tournament_bracket_json
```sql
CREATE OR REPLACE FUNCTION public.sp_tournament_bracket_json(p_tournament_id integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
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
$function$
```

#### trg_sync_tournament_status_from_match
```sql
CREATE OR REPLACE FUNCTION public.trg_sync_tournament_status_from_match()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
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
$function$
```

#### trg_validate_category
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_category()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF NEW.gender NOT IN ('M', 'F') THEN
        RAISE EXCEPTION 'invalid_category_gender';
    END IF;
    IF NEW.mode NOT IN ('Singles', 'Doubles') THEN
        RAISE EXCEPTION 'invalid_category_mode';
    END IF;
    RETURN NEW;
END;
$function$
```

#### trg_validate_round
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_round()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF NEW.round_number IS NULL OR NEW.round_number < 1 THEN
        RAISE EXCEPTION 'invalid_round_number';
    END IF;
    IF NEW.best_of_sets NOT IN (1, 3, 5) THEN
        RAISE EXCEPTION 'invalid_best_of_sets';
    END IF;
    RETURN NEW;
END;
$function$
```

#### trg_validate_subcategory
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_subcategory()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF NEW.draw_size IS NULL OR NEW.draw_size NOT IN (2, 4, 8, 16, 32, 64, 128) THEN
        RAISE EXCEPTION 'invalid_grand_slam_draw_size';
    END IF;
    RETURN NEW;
END;
$function$
```

#### trg_validate_tournament_dates
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_tournament_dates()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
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
$function$
```

### Canchas y programacion

#### sp_list_courts_json
```sql
CREATE OR REPLACE FUNCTION public.sp_list_courts_json()
 RETURNS SETOF jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    court_tournament_col text;
    court_surface_col text;
    tournament_id_col text;
    tournament_surface_col text;
BEGIN
    court_tournament_col := public.fn_read_first_column('Court', ARRAY['tournament_id']);
    court_surface_col := public.fn_read_first_column('Court', ARRAY['surface']);
    tournament_id_col := public.fn_read_first_column('Tournament', ARRAY['id', 'tournament_id']);
    tournament_surface_col := public.fn_read_first_column('Tournament', ARRAY['surface']);

    IF court_tournament_col IS NOT NULL
       AND court_surface_col IS NOT NULL
       AND tournament_id_col IS NOT NULL
       AND tournament_surface_col IS NOT NULL THEN
        RETURN QUERY EXECUTE format(
            'SELECT to_jsonb(row_data) FROM (
                SELECT c.*, t.%1$I AS tournament_surface,
                       (lower(cast(c.%2$I AS text)) = lower(cast(t.%1$I AS text))) AS surface_matches
                FROM %3$I c
                LEFT JOIN %4$I t ON t.%5$I = c.%6$I
                ORDER BY c.%6$I
                LIMIT 200
            ) row_data',
            tournament_surface_col,
            court_surface_col,
            'Court',
            'Tournament',
            tournament_id_col,
            court_tournament_col
        );
        RETURN;
    END IF;

    RETURN QUERY SELECT * FROM public.sp_select_table_json('Court', '{}'::jsonb, NULL, ARRAY['tournament_id', 'name', 'id'], 200);
END;
$function$
```

#### trg_validate_court
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_court()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    tournament_surface text;
BEGIN
    IF NEW.capacity IS NOT NULL AND NEW.capacity < 0 THEN
        RAISE EXCEPTION 'invalid_court_capacity';
    END IF;

    SELECT "surface"::text INTO tournament_surface
    FROM "Tournament"
    WHERE "id" = NEW.tournament_id;

    IF tournament_surface IS NOT NULL
       AND NEW.surface IS NOT NULL
       AND tournament_surface <> NEW.surface::text THEN
        RAISE EXCEPTION 'court_surface_must_match_tournament';
    END IF;

    RETURN NEW;
END;
$function$
```

#### trg_validate_session
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_session()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF NEW.start_datetime IS NOT NULL AND NEW.end_datetime IS NOT NULL AND NEW.start_datetime > NEW.end_datetime THEN
        RAISE EXCEPTION 'invalid_session_dates';
    END IF;
    RETURN NEW;
END;
$function$
```

### Jugadores, equipos e inscripciones

#### sp_available_entry_teams_json
```sql
CREATE OR REPLACE FUNCTION public.sp_available_entry_teams_json(p_subcategory_id integer)
 RETURNS TABLE(row_data jsonb)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_mode text;
    v_required_members integer;
BEGIN
    SELECT c.mode::text
    INTO v_mode
    FROM "SubCategory" sc
    JOIN "Category" c ON c.id = sc.category_id
    WHERE sc.id = p_subcategory_id;

    v_required_members := CASE WHEN v_mode = 'Doubles' THEN 2 ELSE 1 END;

    RETURN QUERY
    SELECT to_jsonb(q)
    FROM (
        SELECT
            t.id AS team_id,
            t.name AS equipo,
            COUNT(tm.player_id) AS jugadores,
            v_required_members AS jugadores_requeridos
        FROM "Team" t
        JOIN "TeamMember" tm ON tm.team_id = t.id
        WHERE (
            p_subcategory_id IS NULL
            OR NOT EXISTS (
                SELECT 1
                FROM "Entry" e
                WHERE e.subcategory_id = p_subcategory_id
                  AND e.team_id = t.id
            )
        )
        GROUP BY t.id, t.name
        HAVING p_subcategory_id IS NULL OR COUNT(tm.player_id) = v_required_members
        ORDER BY t.name
    ) q;
END;
$function$
```

#### sp_available_team_member_players_json
```sql
CREATE OR REPLACE FUNCTION public.sp_available_team_member_players_json(p_team_id integer)
 RETURNS TABLE(row_data jsonb)
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    RETURN QUERY
    SELECT to_jsonb(q)
    FROM (
        SELECT
            p.id AS player_id,
            TRIM(CONCAT(p.first_name, ' ', p.last_name)) AS jugador,
            p.country_code AS pais
        FROM "Player" p
        WHERE p_team_id IS NULL
           OR NOT EXISTS (
                SELECT 1
                FROM "TeamMember" tm
                WHERE tm.team_id = p_team_id
                  AND tm.player_id = p.id
           )
        ORDER BY p.last_name, p.first_name, p.id
    ) q;
END;
$function$
```

#### sp_team_member_count
```sql
CREATE OR REPLACE FUNCTION public.sp_team_member_count(p_team_id integer)
 RETURNS integer
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    target_table text;
    team_col text;
    total integer;
BEGIN
    target_table := public.fn_crud_first_table(ARRAY['TeamMember', 'TeamPlayer', 'PlayerTeam']);
    IF target_table IS NULL THEN
        RETURN 0;
    END IF;
    team_col := public.fn_read_first_column(target_table, ARRAY['team_id']);
    IF team_col IS NULL THEN
        RETURN 0;
    END IF;

    EXECUTE format('SELECT COUNT(*) FROM %I WHERE %I::text = $1', target_table, team_col)
    INTO total
    USING p_team_id::text;
    RETURN COALESCE(total, 0);
END;
$function$
```

#### trg_validate_entry
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_entry()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_draw_size integer;
    v_used_slots integer;
BEGIN
    SELECT sc."draw_size" INTO v_draw_size
    FROM "SubCategory" sc
    WHERE sc."id" = NEW.subcategory_id;

    SELECT COUNT(*) INTO v_used_slots
    FROM "Entry" e
    WHERE e."subcategory_id" = NEW.subcategory_id
      AND e."id" <> COALESCE(NEW.id, -1);

    IF v_draw_size IS NOT NULL AND v_used_slots >= v_draw_size THEN
        RAISE EXCEPTION 'draw_capacity_exceeded';
    END IF;
    IF NEW.seed IS NOT NULL AND NEW.seed < 1 THEN
        RAISE EXCEPTION 'invalid_seed';
    END IF;
    RETURN NEW;
END;
$function$
```

#### trg_validate_team_member
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_team_member()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    members_count integer;
BEGIN
    IF NEW.player_id IS NULL OR NEW.team_id IS NULL THEN
        RAISE EXCEPTION 'invalid_team_member';
    END IF;

    EXECUTE format('SELECT COUNT(*) FROM %I WHERE team_id = $1 AND player_id <> $2', TG_TABLE_NAME)
    INTO members_count
    USING NEW.team_id, NEW.player_id;

    IF members_count >= 2 THEN
        RAISE EXCEPTION 'team_member_limit_exceeded';
    END IF;

    RETURN NEW;
END;
$function$
```

### Partidos y marcador

#### fn_tennis_point_label
```sql
CREATE OR REPLACE FUNCTION public.fn_tennis_point_label(p_points_for bigint, p_points_against bigint)
 RETURNS text
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
BEGIN
    RETURN public.fn_tennis_point_label(p_points_for::integer, p_points_against::integer);
END;
$function$
```

#### fn_tennis_point_label
```sql
CREATE OR REPLACE FUNCTION public.fn_tennis_point_label(p_points_for integer, p_points_against integer)
 RETURNS text
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
BEGIN
    IF p_points_for IS NULL THEN
        p_points_for := 0;
    END IF;
    IF p_points_against IS NULL THEN
        p_points_against := 0;
    END IF;

    IF p_points_for >= 3 AND p_points_against >= 3 THEN
        IF p_points_for = p_points_against THEN
            RETURN '40';
        ELSIF p_points_for = p_points_against + 1 THEN
            RETURN 'AD';
        END IF;
        RETURN '40';
    END IF;

    RETURN CASE p_points_for
        WHEN 0 THEN '0'
        WHEN 1 THEN '15'
        WHEN 2 THEN '30'
        ELSE '40'
    END;
END;
$function$
```

#### sp_dashboard_upcoming_matches_json
```sql
CREATE OR REPLACE FUNCTION public.sp_dashboard_upcoming_matches_json(p_limit integer DEFAULT 8)
 RETURNS SETOF jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
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
$function$
```

#### sp_match_development_detail_json
```sql
CREATE OR REPLACE FUNCTION public.sp_match_development_detail_json(p_match_id integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
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
        participants AS (
            SELECT
                MAX(mp.team_id) FILTER (WHERE upper(mp.side) = ''A'') AS team_a,
                MAX(mp.team_id) FILTER (WHERE upper(mp.side) = ''B'') AS team_b,
                jsonb_object_agg(upper(mp.side), mp.team_id) AS teams
            FROM %2$I mp
            WHERE mp.match_id = $1
        ),
        sets AS (
            SELECT
                COALESCE(jsonb_agg(to_jsonb(ms) ORDER BY ms.set_number), ''[]''::jsonb) AS rows,
                COALESCE(jsonb_agg(to_jsonb(ms) ORDER BY ms.set_number) FILTER (WHERE ms.winner_team_id IS NOT NULL), ''[]''::jsonb) AS completed_rows,
                COUNT(*) FILTER (WHERE ms.winner_team_id = (SELECT team_a FROM participants)) AS sets_a,
                COUNT(*) FILTER (WHERE ms.winner_team_id = (SELECT team_b FROM participants)) AS sets_b,
                COALESCE(MAX(ms.set_number), 0) + 1 AS next_set
            FROM %1$I ms
            WHERE ms.match_id = $1
        ),
        current_set AS (
            SELECT ms.*
            FROM %1$I ms
            WHERE ms.match_id = $1
              AND ms.winner_team_id IS NULL
            ORDER BY ms.set_number DESC, ms.id DESC
            LIMIT 1
        ),
        last_set AS (
            SELECT ms.*
            FROM %1$I ms
            WHERE ms.match_id = $1
            ORDER BY ms.set_number DESC, ms.id DESC
            LIMIT 1
        ),
        current_game AS (
            SELECT mg.*
            FROM %3$I mg
            JOIN current_set cs ON cs.id = mg.match_set_id
            WHERE mg.winner_team_id IS NULL
            ORDER BY mg.game_number DESC, mg.id DESC
            LIMIT 1
        ),
        next_game AS (
            SELECT COALESCE(MAX(mg.game_number), 0) + 1 AS game_number
            FROM %3$I mg
            JOIN current_set cs ON cs.id = mg.match_set_id
        ),
        current_points AS (
            SELECT
                COUNT(*) FILTER (WHERE tm.team_id = (SELECT team_a FROM participants)) AS points_a,
                COUNT(*) FILTER (WHERE tm.team_id = (SELECT team_b FROM participants)) AS points_b
            FROM %4$I p
            JOIN "TeamMember" tm ON tm.player_id = p.winner_player_id
            WHERE p.game_id = (SELECT id FROM current_game)
        )
        SELECT jsonb_build_object(
            ''match'', (SELECT item FROM match_base),
            ''sets'', COALESCE((SELECT rows FROM sets), ''[]''::jsonb),
            ''completed_sets'', COALESCE((SELECT completed_rows FROM sets), ''[]''::jsonb),
            ''sets_a'', COALESCE((SELECT sets_a FROM sets), 0),
            ''sets_b'', COALESCE((SELECT sets_b FROM sets), 0),
            ''next_set'', COALESCE((SELECT next_set FROM sets), 1),
            ''teams'', COALESCE((SELECT teams FROM participants), ''{}''::jsonb),
            ''score'', jsonb_build_object(
                ''current_set_id'', (SELECT id FROM current_set),
                ''current_game_id'', (SELECT id FROM current_game),
                ''set_number'', CASE
                    WHEN (SELECT item ->> ''estado'' FROM match_base) = ''Completed'' THEN COALESCE((SELECT set_number FROM last_set), 1)
                    ELSE COALESCE((SELECT set_number FROM current_set), (SELECT next_set FROM sets), 1)
                END,
                ''game_number'', CASE
                    WHEN (SELECT item ->> ''estado'' FROM match_base) = ''Completed'' THEN NULL
                    ELSE COALESCE((SELECT game_number FROM current_game), (SELECT game_number FROM next_game), 1)
                END,
                ''games_a'', CASE
                    WHEN (SELECT item ->> ''estado'' FROM match_base) = ''Completed'' THEN COALESCE((SELECT team_a_games FROM last_set), 0)
                    ELSE COALESCE((SELECT team_a_games FROM current_set), 0)
                END,
                ''games_b'', CASE
                    WHEN (SELECT item ->> ''estado'' FROM match_base) = ''Completed'' THEN COALESCE((SELECT team_b_games FROM last_set), 0)
                    ELSE COALESCE((SELECT team_b_games FROM current_set), 0)
                END,
                ''points_a'', COALESCE((SELECT points_a FROM current_points), 0),
                ''points_b'', COALESCE((SELECT points_b FROM current_points), 0),
                ''point_label_a'', public.fn_tennis_point_label(COALESCE((SELECT points_a FROM current_points), 0), COALESCE((SELECT points_b FROM current_points), 0)),
                ''point_label_b'', public.fn_tennis_point_label(COALESCE((SELECT points_b FROM current_points), 0), COALESCE((SELECT points_a FROM current_points), 0))
            )
        )',
        'MatchSet',
        'MatchParticipant',
        'MatchGame',
        'MatchPoint'
    )
    INTO result
    USING p_match_id;

    RETURN result;
END;
$function$
```

#### sp_matches_by_structure_json
```sql
CREATE OR REPLACE FUNCTION public.sp_matches_by_structure_json(p_tournament_id integer DEFAULT NULL::integer, p_category_id integer DEFAULT NULL::integer, p_round_id integer DEFAULT NULL::integer, p_limit integer DEFAULT 300)
 RETURNS SETOF jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
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
$function$
```

#### trg_match_set_requires_in_progress
```sql
CREATE OR REPLACE FUNCTION public.trg_match_set_requires_in_progress()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
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
$function$
```

#### trg_validate_match
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_match()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    conflict_count integer;
BEGIN
    IF NEW.scheduled_datetime IS NOT NULL AND NEW.court_id IS NOT NULL THEN
        SELECT COUNT(*) INTO conflict_count
        FROM "Match"
        WHERE "court_id" = NEW.court_id
          AND "scheduled_datetime" = NEW.scheduled_datetime
          AND "id" <> COALESCE(NEW.id, -1)
          AND COALESCE("status"::text, '') NOT IN ('Cancelled');

        IF conflict_count > 0 THEN
            RAISE EXCEPTION 'court_schedule_conflict';
        END IF;
    END IF;
    RETURN NEW;
END;
$function$
```

#### trg_validate_match_participant
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_match_participant()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    side_count integer;
BEGIN
    IF NEW.side IS NULL OR upper(NEW.side) NOT IN ('A', 'B') THEN
        RAISE EXCEPTION 'invalid_match_side';
    END IF;

    SELECT COUNT(*) INTO side_count
    FROM "MatchParticipant" mp
    WHERE mp."match_id" = NEW.match_id
      AND upper(mp."side") = upper(NEW.side)
      AND mp."team_id" <> NEW.team_id;

    IF side_count > 0 THEN
        RAISE EXCEPTION 'match_side_already_assigned';
    END IF;

    RETURN NEW;
END;
$function$
```

#### trg_validate_match_point_score
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_match_point_score()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    match_status text;
    point_match_id integer;
    game_winner integer;
    winner_team integer;
    participant_count integer;
BEGIN
    IF NEW.game_id IS NULL OR NEW.match_set_id IS NULL OR NEW.winner_player_id IS NULL THEN
        RAISE EXCEPTION 'invalid_point_payload';
    END IF;

    SELECT ms.match_id, mg.winner_team_id
    INTO point_match_id, game_winner
    FROM "MatchGame" mg
    JOIN "MatchSet" ms ON ms.id = mg.match_set_id
    WHERE mg.id = NEW.game_id
      AND ms.id = NEW.match_set_id;

    IF point_match_id IS NULL THEN
        RAISE EXCEPTION 'point_game_not_found';
    END IF;

    SELECT status::text
    INTO match_status
    FROM "Match"
    WHERE id = point_match_id;

    IF match_status <> 'InProgress' THEN
        RAISE EXCEPTION 'points_require_in_progress_match';
    END IF;
    IF game_winner IS NOT NULL THEN
        RAISE EXCEPTION 'game_already_closed';
    END IF;

    SELECT mp.team_id
    INTO winner_team
    FROM "MatchParticipant" mp
    JOIN "TeamMember" tm ON tm.team_id = mp.team_id
    WHERE mp.match_id = point_match_id
      AND tm.player_id = NEW.winner_player_id
    LIMIT 1;

    IF winner_team IS NULL THEN
        RAISE EXCEPTION 'point_winner_not_in_match';
    END IF;

    SELECT COUNT(*)
    INTO participant_count
    FROM "MatchParticipant" mp
    WHERE mp.match_id = point_match_id
      AND mp.team_id = winner_team;

    IF participant_count <> 1 THEN
        RAISE EXCEPTION 'point_winner_not_in_match';
    END IF;

    IF NEW.point_number IS NULL OR NEW.point_number < 1 THEN
        SELECT COALESCE(MAX(point_number), 0) + 1
        INTO NEW.point_number
        FROM "MatchPoint"
        WHERE match_set_id = NEW.match_set_id;
    END IF;

    RETURN NEW;
END;
$function$
```

#### trg_validate_match_set
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_match_set()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF NEW.set_number IS NULL OR NEW.set_number < 1 THEN
        RAISE EXCEPTION 'invalid_set_number';
    END IF;

    IF NEW.team_a_games IS NOT NULL AND NEW.team_a_games < 0 THEN
        RAISE EXCEPTION 'invalid_team_a_games';
    END IF;
    IF NEW.team_b_games IS NOT NULL AND NEW.team_b_games < 0 THEN
        RAISE EXCEPTION 'invalid_team_b_games';
    END IF;

    IF NEW.winner_team_id IS NOT NULL
       AND NEW.team_a_games IS NOT NULL
       AND NEW.team_b_games IS NOT NULL
       AND NEW.team_a_games = NEW.team_b_games THEN
        RAISE EXCEPTION 'set_must_have_winner';
    END IF;

    RETURN NEW;
END;
$function$
```

### Oficiales, sanciones y lesiones

#### fn_injury_recovery_handler
```sql
CREATE OR REPLACE FUNCTION public.fn_injury_recovery_handler()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Si se modifica recovery_date en la inserción/actualización
  IF NEW.recovery_date IS NOT NULL THEN
    -- Si antes no había fecha de recuperación, marcar inactivo
    NEW.active := FALSE;
  END IF;
  -- No permitir que se modifique recovery_date en una lesión ya
  -- recuperada (protección contra reactivaciones).
  IF TG_OP = 'UPDATE' AND OLD.recovery_date IS NOT NULL THEN
    RAISE EXCEPTION 'No se puede modificar una lesión ya recuperada.';
  END IF;
  RETURN NEW;
END;
$function$
```

#### sp_sanctions_overview_json
```sql
CREATE OR REPLACE FUNCTION public.sp_sanctions_overview_json(p_limit integer DEFAULT 300)
 RETURNS SETOF jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
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
$function$
```

#### trg_validate_injury
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_injury()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF NEW.recovery_date IS NOT NULL AND NEW.injury_date IS NOT NULL AND NEW.recovery_date < NEW.injury_date THEN
        RAISE EXCEPTION 'invalid_recovery_date';
    END IF;
    IF NEW.recovery_date IS NOT NULL THEN
        NEW.active := FALSE;
    END IF;
    RETURN NEW;
END;
$function$
```

#### trg_validate_sanction_target
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_sanction_target()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    payload jsonb := to_jsonb(NEW);
    target_count integer := 0;
BEGIN
    IF payload ? 'player_id' AND payload ->> 'player_id' IS NOT NULL AND payload ->> 'player_id' <> '' THEN
        target_count := target_count + 1;
    END IF;
    IF payload ? 'team_id' AND payload ->> 'team_id' IS NOT NULL AND payload ->> 'team_id' <> '' THEN
        target_count := target_count + 1;
    END IF;
    IF payload ? 'official_id' AND payload ->> 'official_id' IS NOT NULL AND payload ->> 'official_id' <> '' THEN
        target_count := target_count + 1;
    END IF;

    IF target_count <> 1 THEN
        RAISE EXCEPTION 'sanction_requires_one_target';
    END IF;
    RETURN NEW;
END;
$function$
```

### Lectura, dashboard y reportes

#### sp_categories_overview_json
```sql
CREATE OR REPLACE FUNCTION public.sp_categories_overview_json(p_limit integer DEFAULT 300)
 RETURNS SETOF jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
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
$function$
```

#### sp_injuries_overview_json
```sql
CREATE OR REPLACE FUNCTION public.sp_injuries_overview_json(p_limit integer DEFAULT 300)
 RETURNS SETOF jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
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
$function$
```

#### sp_list_entries_with_slots_json
```sql
CREATE OR REPLACE FUNCTION public.sp_list_entries_with_slots_json()
 RETURNS SETOF jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    entry_sub_col text;
    sub_id_col text;
    draw_size_col text;
BEGIN
    IF NOT public.fn_crud_table_exists('Entry') THEN
        RETURN;
    END IF;

    entry_sub_col := public.fn_read_first_column('Entry', ARRAY['subcategory_id']);
    sub_id_col := public.fn_read_first_column('SubCategory', ARRAY['id', 'subcategory_id']);
    draw_size_col := public.fn_read_first_column('SubCategory', ARRAY['draw_size']);

    IF entry_sub_col IS NOT NULL AND sub_id_col IS NOT NULL AND draw_size_col IS NOT NULL THEN
        RETURN QUERY EXECUTE format(
            'SELECT to_jsonb(row_data) FROM (
                SELECT e.*, sc.%1$I AS draw_size,
                       (sc.%1$I - counts.used_slots) AS available_slots
                FROM %2$I e
                JOIN %3$I sc ON sc.%4$I = e.%5$I
                JOIN (
                    SELECT %5$I AS sid, COUNT(*) AS used_slots
                    FROM %2$I
                    GROUP BY %5$I
                ) counts ON counts.sid = e.%5$I
                LIMIT 200
            ) row_data',
            draw_size_col,
            'Entry',
            'SubCategory',
            sub_id_col,
            entry_sub_col
        );
        RETURN;
    END IF;

    RETURN QUERY SELECT * FROM public.sp_select_table_json('Entry', '{}'::jsonb, NULL, ARRAY['subcategory_id', 'id'], 200);
END;
$function$
```

#### sp_safe_count
```sql
CREATE OR REPLACE FUNCTION public.sp_safe_count(p_table text, p_filters jsonb DEFAULT '{}'::jsonb)
 RETURNS integer
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    where_clause text;
    total integer;
BEGIN
    IF NOT public.fn_crud_table_exists(p_table) THEN
        RETURN 0;
    END IF;

    where_clause := public.fn_read_where_clause(p_table, p_filters);
    EXECUTE format('SELECT COUNT(*) FROM %I%s', p_table, where_clause) INTO total;
    RETURN COALESCE(total, 0);
END;
$function$
```

#### sp_select_by_id_json
```sql
CREATE OR REPLACE FUNCTION public.sp_select_by_id_json(p_table text, p_object_id text, p_id_candidates text[] DEFAULT ARRAY[]::text[])
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    id_column text;
    result jsonb;
    candidates text[];
BEGIN
    IF NOT public.fn_crud_table_exists(p_table) OR p_object_id IS NULL THEN
        RETURN NULL;
    END IF;

    candidates := COALESCE(NULLIF(p_id_candidates, ARRAY[]::text[]), ARRAY[lower(p_table) || '_id', 'id', 'pk']);
    id_column := public.fn_read_first_column(p_table, candidates);
    IF id_column IS NULL THEN
        RETURN NULL;
    END IF;

    EXECUTE format('SELECT to_jsonb(row_data) FROM (SELECT * FROM %I WHERE %I::text = $1 LIMIT 1) row_data', p_table, id_column)
    INTO result
    USING p_object_id;
    RETURN result;
END;
$function$
```

#### sp_select_table_json
```sql
CREATE OR REPLACE FUNCTION public.sp_select_table_json(p_table text, p_filters jsonb DEFAULT '{}'::jsonb, p_search text DEFAULT NULL::text, p_order_candidates text[] DEFAULT ARRAY[]::text[], p_limit integer DEFAULT 200)
 RETURNS SETOF jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    where_clause text := '';
    search_clause text := '';
    order_clause text := '';
    safe_limit integer := LEAST(GREATEST(COALESCE(p_limit, 200), 1), 1000);
    order_column text;
    search_parts text;
BEGIN
    IF NOT public.fn_crud_table_exists(p_table) THEN
        RETURN;
    END IF;

    where_clause := public.fn_read_where_clause(p_table, p_filters);

    IF p_search IS NOT NULL AND btrim(p_search) <> '' THEN
        SELECT string_agg(format('CAST(%I AS text) ILIKE %L', column_name, '%' || p_search || '%'), ' OR ')
        INTO search_parts
        FROM (
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = p_table
            ORDER BY ordinal_position
            LIMIT 8
        ) limited_columns;

        IF search_parts IS NOT NULL THEN
            search_clause := CASE WHEN where_clause = '' THEN ' WHERE ' ELSE ' AND ' END || '(' || search_parts || ')';
        END IF;
    END IF;

    order_column := public.fn_read_first_column(p_table, COALESCE(p_order_candidates, ARRAY[]::text[]));
    IF order_column IS NOT NULL THEN
        order_clause := format(' ORDER BY %I', order_column);
    END IF;

    RETURN QUERY EXECUTE format(
        'SELECT to_jsonb(row_data) FROM (SELECT * FROM %I%s%s%s LIMIT %s) row_data',
        p_table,
        where_clause,
        search_clause,
        order_clause,
        safe_limit
    );
END;
$function$
```

#### sp_subcategories_overview_json
```sql
CREATE OR REPLACE FUNCTION public.sp_subcategories_overview_json(p_limit integer DEFAULT 300)
 RETURNS SETOF jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    safe_limit integer := LEAST(GREATEST(COALESCE(p_limit, 300), 1), 1000);
BEGIN
    IF NOT public.fn_crud_table_exists('SubCategory') THEN
        RETURN;
    END IF;

    RETURN QUERY EXECUTE format(
        'SELECT to_jsonb(row_data)
        FROM (
            SELECT
                sc.id,
                sc.name,
                sc.category_id,
                COALESCE(c.name, ''-'') AS categoria,
                COALESCE(t.name, ''-'') AS torneo,
                sc.draw_size,
                sc.description
            FROM %1$I sc
            LEFT JOIN %2$I c ON c.id = sc.category_id
            LEFT JOIN %3$I t ON t.id = c.tournament_id
            ORDER BY t.name NULLS LAST, c.id, sc.name, sc.id
            LIMIT %4$s
        ) row_data',
        'SubCategory',
        'Category',
        'Tournament',
        safe_limit
    );
END;
$function$
```

### Utilidades internas

#### fn_crud_column_exists
```sql
CREATE OR REPLACE FUNCTION public.fn_crud_column_exists(p_table text, p_column text)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = p_table
          AND column_name = p_column
    );
$function$
```

#### fn_crud_first_table
```sql
CREATE OR REPLACE FUNCTION public.fn_crud_first_table(p_tables text[])
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    table_name text;
BEGIN
    FOREACH table_name IN ARRAY p_tables
    LOOP
        IF public.fn_crud_table_exists(table_name) THEN
            RETURN table_name;
        END IF;
    END LOOP;
    RETURN NULL;
END;
$function$
```

#### fn_crud_insert_json
```sql
CREATE OR REPLACE FUNCTION public.fn_crud_insert_json(p_table text, p_payload jsonb, p_return_col text DEFAULT 'id'::text)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
DECLARE
    clean_payload jsonb := jsonb_strip_nulls(COALESCE(p_payload, '{}'::jsonb));
    column_sql text;
    value_sql text;
    result text;
BEGIN
    SELECT
        string_agg(format('%I', a.attname), ', ' ORDER BY a.attnum),
        string_agg(format('($1 ->> %L)::%s', a.attname, format_type(a.atttypid, a.atttypmod)), ', ' ORDER BY a.attnum)
    INTO column_sql, value_sql
    FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = current_schema()
      AND c.relname = p_table
      AND a.attnum > 0
      AND NOT a.attisdropped
      AND a.attname IN (SELECT jsonb_object_keys(clean_payload));

    IF column_sql IS NULL THEN
        RAISE EXCEPTION 'No insertable columns found for %.', p_table;
    END IF;

    IF p_return_col IS NOT NULL AND public.fn_crud_column_exists(p_table, p_return_col) THEN
        EXECUTE format(
            'INSERT INTO %I (%s) VALUES (%s) RETURNING %I::text',
            p_table,
            column_sql,
            value_sql,
            p_return_col
        )
        INTO result
        USING clean_payload;
        RETURN result;
    END IF;

    EXECUTE format('INSERT INTO %I (%s) VALUES (%s)', p_table, column_sql, value_sql)
    USING clean_payload;
    RETURN NULL;
END;
$function$
```

#### fn_crud_table_exists
```sql
CREATE OR REPLACE FUNCTION public.fn_crud_table_exists(p_table text)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    SELECT to_regclass(format('%I', p_table)) IS NOT NULL;
$function$
```

#### fn_crud_update_json
```sql
CREATE OR REPLACE FUNCTION public.fn_crud_update_json(p_table text, p_id_col text, p_id text, p_payload jsonb)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    payload jsonb := COALESCE(p_payload, '{}'::jsonb);
    set_sql text;
BEGIN
    SELECT string_agg(
        format('%I = ($1 ->> %L)::%s', a.attname, a.attname, format_type(a.atttypid, a.atttypmod)),
        ', ' ORDER BY a.attnum
    )
    INTO set_sql
    FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = current_schema()
      AND c.relname = p_table
      AND a.attnum > 0
      AND NOT a.attisdropped
      AND a.attname <> p_id_col
      AND a.attname IN (SELECT jsonb_object_keys(payload));

    IF set_sql IS NULL THEN
        RETURN;
    END IF;

    EXECUTE format('UPDATE %I SET %s WHERE %I::text = $2', p_table, set_sql, p_id_col)
    USING payload, p_id;
END;
$function$
```

#### fn_read_first_column
```sql
CREATE OR REPLACE FUNCTION public.fn_read_first_column(p_table text, p_candidates text[])
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    candidate text;
    found text;
BEGIN
    FOREACH candidate IN ARRAY COALESCE(p_candidates, ARRAY[]::text[])
    LOOP
        SELECT column_name INTO found
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = p_table
          AND lower(column_name) = lower(candidate)
        LIMIT 1;

        IF found IS NOT NULL THEN
            RETURN found;
        END IF;
    END LOOP;
    RETURN NULL;
END;
$function$
```

#### fn_read_where_clause
```sql
CREATE OR REPLACE FUNCTION public.fn_read_where_clause(p_table text, p_filters jsonb)
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    item record;
    column_name text;
    parts text[] := ARRAY[]::text[];
BEGIN
    FOR item IN SELECT key, value FROM jsonb_each_text(COALESCE(p_filters, '{}'::jsonb))
    LOOP
        IF item.value IS NULL OR item.value = '' THEN
            CONTINUE;
        END IF;

        column_name := public.fn_read_first_column(p_table, ARRAY[item.key]);
        IF column_name IS NOT NULL THEN
            parts := array_append(parts, format('%I::text = %L', column_name, item.value));
        END IF;
    END LOOP;

    IF array_length(parts, 1) IS NULL THEN
        RETURN '';
    END IF;
    RETURN ' WHERE ' || array_to_string(parts, ' AND ');
END;
$function$
```

### Otros

#### sp_entries_by_structure_json
```sql
CREATE OR REPLACE FUNCTION public.sp_entries_by_structure_json(p_tournament_id integer DEFAULT NULL::integer, p_category_id integer DEFAULT NULL::integer, p_subcategory_id integer DEFAULT NULL::integer, p_limit integer DEFAULT 300)
 RETURNS SETOF jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
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
$function$
```
