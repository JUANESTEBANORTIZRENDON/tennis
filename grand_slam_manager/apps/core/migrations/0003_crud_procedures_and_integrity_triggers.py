"""Versiona procedimientos de escritura y reglas de integridad operativa."""

from django.db import migrations


SQL = r"""
DO $$
DECLARE
    procedure_name text;
    procedure_signature text;
BEGIN
    FOREACH procedure_name IN ARRAY ARRAY[
        'sp_create_tournament',
        'sp_update_tournament',
        'sp_create_court',
        'sp_create_category',
        'sp_create_subcategory',
        'sp_create_round',
        'sp_create_player',
        'sp_create_injury',
        'sp_assign_injury_to_player',
        'sp_close_injury',
        'sp_create_team',
        'sp_add_team_member',
        'sp_create_entry',
        'sp_create_match',
        'sp_add_match_participant',
        'sp_register_match_set',
        'sp_finish_match',
        'sp_schedule_match',
        'sp_reschedule_match',
        'sp_create_session',
        'sp_add_match_to_session',
        'sp_create_official',
        'sp_assign_official_to_match',
        'sp_create_sanction',
        'sp_create_sanction_appeal',
        'sp_create_audit_log',
        'sp_create_user_account'
    ]
    LOOP
        FOR procedure_signature IN
            SELECT p.oid::regprocedure::text
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = current_schema()
              AND p.prokind = 'p'
              AND p.proname = procedure_name
        LOOP
            EXECUTE format('DROP PROCEDURE IF EXISTS %s', procedure_signature);
        END LOOP;
    END LOOP;
END $$;

CREATE OR REPLACE FUNCTION public.fn_crud_table_exists(p_table text)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT to_regclass(format('%I', p_table)) IS NOT NULL;
$$;

CREATE OR REPLACE FUNCTION public.fn_crud_column_exists(p_table text, p_column text)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = p_table
          AND column_name = p_column
    );
$$;

CREATE OR REPLACE FUNCTION public.fn_crud_first_table(p_tables text[])
RETURNS text
LANGUAGE plpgsql
STABLE
AS $$
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
$$;

CREATE OR REPLACE FUNCTION public.fn_crud_insert_json(
    p_table text,
    p_payload jsonb,
    p_return_col text DEFAULT 'id'
)
RETURNS text
LANGUAGE plpgsql
AS $$
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
$$;

CREATE OR REPLACE FUNCTION public.fn_crud_update_json(
    p_table text,
    p_id_col text,
    p_id text,
    p_payload jsonb
)
RETURNS void
LANGUAGE plpgsql
AS $$
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
$$;

CREATE OR REPLACE PROCEDURE public.sp_create_tournament(
    IN p_name character varying,
    IN p_year integer,
    IN p_start date,
    IN p_end date,
    IN p_location text,
    IN p_surface surface_type,
    IN p_description text
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM public.fn_crud_insert_json('Tournament', jsonb_build_object(
        'name', p_name,
        'year', p_year,
        'start_date', p_start,
        'end_date', p_end,
        'location', p_location,
        'surface', p_surface,
        'description', p_description
    ));
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_update_tournament(
    IN p_id integer,
    IN p_name character varying,
    IN p_year integer,
    IN p_start date,
    IN p_end date,
    IN p_location text,
    IN p_surface surface_type,
    IN p_description text
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM public.fn_crud_update_json('Tournament', 'id', p_id::text, jsonb_build_object(
        'name', p_name,
        'year', p_year,
        'start_date', p_start,
        'end_date', p_end,
        'location', p_location,
        'surface', p_surface,
        'description', p_description,
        'updated_at', CURRENT_TIMESTAMP
    ));
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_create_court(
    IN p_tournament_id integer,
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
        'tournament_id', p_tournament_id,
        'name', p_name,
        'capacity', p_capacity,
        'surface', p_surface,
        'indoor', p_indoor,
        'location', p_location
    ));
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_create_category(
    IN p_tournament_id integer,
    IN p_name character varying,
    IN p_gender character varying,
    IN p_mode character varying,
    IN p_description text
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM public.fn_crud_insert_json('Category', jsonb_build_object(
        'tournament_id', p_tournament_id,
        'name', p_name,
        'gender', p_gender,
        'mode', p_mode,
        'description', p_description
    ));
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_create_subcategory(
    IN p_category_id integer,
    IN p_name character varying,
    IN p_draw_size integer,
    IN p_description text
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM public.fn_crud_insert_json('SubCategory', jsonb_build_object(
        'category_id', p_category_id,
        'name', p_name,
        'draw_size', p_draw_size,
        'description', p_description
    ));
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_create_round(
    IN p_round_name character varying,
    IN p_subcategory_id integer,
    IN p_round_number integer,
    IN p_best_of_sets integer,
    IN p_description text
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM public.fn_crud_insert_json('Round', jsonb_build_object(
        'round_name', p_round_name,
        'subcategory_id', p_subcategory_id,
        'round_number', p_round_number,
        'best_of_sets', p_best_of_sets,
        'description', p_description
    ));
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_create_player(
    IN p_id character varying,
    IN p_doc_type character varying,
    IN p_issuer_country character varying,
    IN p_first_name character varying,
    IN p_last_name character varying,
    IN p_gender character varying,
    IN p_birth_date date,
    IN p_country_code character varying,
    IN p_height_cm integer,
    IN p_weight_kg integer,
    IN p_hand character varying,
    IN p_turned_pro_year integer,
    IN p_bio text
)
LANGUAGE plpgsql
AS $$
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
$$;

CREATE OR REPLACE PROCEDURE public.sp_create_injury(
    IN p_injury_type_id integer,
    IN p_injury_date date,
    IN p_description text
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM public.fn_crud_insert_json('Injury', jsonb_build_object(
        'injury_type_id', p_injury_type_id,
        'injury_date', p_injury_date,
        'description', p_description,
        'active', TRUE
    ));
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_assign_injury_to_player(
    IN p_player_id character varying,
    IN p_injury_id integer
)
LANGUAGE plpgsql
AS $$
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
$$;

CREATE OR REPLACE PROCEDURE public.sp_close_injury(
    IN p_injury_id integer,
    IN p_recovery_date date
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM public.fn_crud_update_json('Injury', 'id', p_injury_id::text, jsonb_build_object(
        'recovery_date', p_recovery_date,
        'active', FALSE
    ));
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_create_team(
    IN p_name character varying,
    IN p_notes text
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM public.fn_crud_insert_json('Team', jsonb_build_object(
        'name', p_name,
        'notes', p_notes
    ));
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_add_team_member(
    IN p_team_id integer,
    IN p_player_id character varying,
    IN p_role character varying,
    IN p_start_date date
)
LANGUAGE plpgsql
AS $$
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
$$;

CREATE OR REPLACE PROCEDURE public.sp_create_entry(
    IN p_subcategory_id integer,
    IN p_team_id integer,
    IN p_seed integer,
    IN p_ranking_at_entry integer,
    IN p_qualifying_method character varying
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM public.fn_crud_insert_json('Entry', jsonb_build_object(
        'subcategory_id', p_subcategory_id,
        'team_id', p_team_id,
        'seed', p_seed,
        'ranking_at_entry', p_ranking_at_entry,
        'qualifying_method', p_qualifying_method
    ));
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_create_match(
    IN p_round_id integer,
    IN p_scheduled_datetime timestamp with time zone,
    IN p_court_id integer,
    IN p_status character varying
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM public.fn_crud_insert_json('Match', jsonb_build_object(
        'round_id', p_round_id,
        'scheduled_datetime', p_scheduled_datetime,
        'court_id', p_court_id,
        'status', p_status
    ));
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_add_match_participant(
    IN p_match_id integer,
    IN p_team_id integer,
    IN p_side character varying
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM public.fn_crud_insert_json('MatchParticipant', jsonb_build_object(
        'match_id', p_match_id,
        'team_id', p_team_id,
        'side', p_side
    ));
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_register_match_set(
    IN p_match_id integer,
    IN p_set_number integer,
    IN p_team_a_games integer,
    IN p_team_b_games integer,
    IN p_tie_break_a integer,
    IN p_tie_break_b integer,
    IN p_winner_team_id integer
)
LANGUAGE plpgsql
AS $$
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
$$;

CREATE OR REPLACE PROCEDURE public.sp_finish_match(
    IN p_match_id integer,
    IN p_winning_team_id integer
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM public.fn_crud_update_json('Match', 'id', p_match_id::text, jsonb_build_object(
        'status', 'Completed',
        'winning_team_id', p_winning_team_id,
        'winner_team_id', p_winning_team_id,
        'finished_at', CURRENT_TIMESTAMP
    ));
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_schedule_match(
    IN p_match_id integer,
    IN p_round_id integer,
    IN p_scheduled_datetime timestamp with time zone,
    IN p_court_id integer,
    IN p_created_by integer
)
LANGUAGE plpgsql
AS $$
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
$$;

CREATE OR REPLACE PROCEDURE public.sp_reschedule_match(
    IN p_match_id integer,
    IN p_user_id integer,
    IN p_new_datetime timestamp with time zone,
    IN p_new_court_id integer,
    IN p_reason text
)
LANGUAGE plpgsql
AS $$
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
$$;

CREATE OR REPLACE PROCEDURE public.sp_create_session(
    IN p_tournament_id integer,
    IN p_name character varying,
    IN p_start_datetime timestamp with time zone,
    IN p_end_datetime timestamp with time zone,
    IN p_status character varying,
    IN p_notes text
)
LANGUAGE plpgsql
AS $$
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
$$;

CREATE OR REPLACE PROCEDURE public.sp_add_match_to_session(
    IN p_session_id integer,
    IN p_match_id integer,
    IN p_order_in_session integer
)
LANGUAGE plpgsql
AS $$
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
$$;

CREATE OR REPLACE PROCEDURE public.sp_create_official(
    IN p_first_name character varying,
    IN p_last_name character varying,
    IN p_nationality character varying,
    IN p_official_type character varying,
    IN p_certification_level character varying,
    IN p_license_number character varying
)
LANGUAGE plpgsql
AS $$
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
$$;

CREATE OR REPLACE PROCEDURE public.sp_assign_official_to_match(
    IN p_match_id integer,
    IN p_official_id integer,
    IN p_role character varying,
    IN p_assigned_by_user_id integer
)
LANGUAGE plpgsql
AS $$
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
$$;

CREATE OR REPLACE PROCEDURE public.sp_create_sanction(
    IN p_tournament_id integer,
    IN p_match_id integer,
    IN p_violation_type_id integer,
    IN p_team_id integer,
    IN p_player_id character varying,
    IN p_official_id integer,
    IN p_sanction_type character varying,
    IN p_penalty_points integer,
    IN p_penalty_games integer,
    IN p_fine_amount numeric,
    IN p_currency character varying,
    IN p_notes text,
    IN p_created_by integer
)
LANGUAGE plpgsql
AS $$
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
$$;

CREATE OR REPLACE PROCEDURE public.sp_create_sanction_appeal(
    IN p_sanction_id integer,
    IN p_filed_by_player_id character varying,
    IN p_status character varying,
    IN p_notes text,
    IN p_created_by integer
)
LANGUAGE plpgsql
AS $$
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
$$;

CREATE OR REPLACE PROCEDURE public.sp_create_audit_log(
    IN p_user_id integer,
    IN p_tournament_id integer,
    IN p_action character varying,
    IN p_entity_table character varying,
    IN p_entity_id integer,
    IN p_entity_pk character varying,
    IN p_details jsonb,
    IN p_ip_address character varying
)
LANGUAGE plpgsql
AS $$
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
$$;

CREATE OR REPLACE PROCEDURE public.sp_create_user_account(
    IN p_email character varying,
    IN p_full_name character varying,
    IN p_phone character varying,
    IN p_password_hash character varying,
    IN p_role_id integer,
    IN p_is_active boolean
)
LANGUAGE plpgsql
AS $$
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
$$;
"""


TRIGGER_SQL = r"""
CREATE OR REPLACE FUNCTION public.trg_validate_tournament_dates()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.start_date IS NOT NULL AND NEW.end_date IS NOT NULL AND NEW.start_date > NEW.end_date THEN
        RAISE EXCEPTION 'invalid_tournament_dates';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_validate_court()
RETURNS trigger
LANGUAGE plpgsql
AS $$
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
$$;

CREATE OR REPLACE FUNCTION public.trg_validate_category()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.gender NOT IN ('M', 'F') THEN
        RAISE EXCEPTION 'invalid_category_gender';
    END IF;
    IF NEW.mode NOT IN ('Singles', 'Doubles') THEN
        RAISE EXCEPTION 'invalid_category_mode';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_validate_subcategory()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.draw_size IS NULL OR NEW.draw_size < 2 THEN
        RAISE EXCEPTION 'invalid_draw_size';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_validate_round()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.round_number IS NULL OR NEW.round_number < 1 THEN
        RAISE EXCEPTION 'invalid_round_number';
    END IF;
    IF NEW.best_of_sets NOT IN (1, 3, 5) THEN
        RAISE EXCEPTION 'invalid_best_of_sets';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_validate_injury()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.recovery_date IS NOT NULL AND NEW.injury_date IS NOT NULL AND NEW.recovery_date < NEW.injury_date THEN
        RAISE EXCEPTION 'invalid_recovery_date';
    END IF;
    IF NEW.recovery_date IS NOT NULL THEN
        NEW.active := FALSE;
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_validate_team_member()
RETURNS trigger
LANGUAGE plpgsql
AS $$
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
$$;

CREATE OR REPLACE FUNCTION public.trg_validate_entry()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    draw_size integer;
    used_slots integer;
BEGIN
    SELECT "draw_size" INTO draw_size FROM "SubCategory" WHERE "id" = NEW.subcategory_id;
    SELECT COUNT(*) INTO used_slots FROM "Entry" WHERE "subcategory_id" = NEW.subcategory_id AND "id" <> COALESCE(NEW.id, -1);

    IF draw_size IS NOT NULL AND used_slots >= draw_size THEN
        RAISE EXCEPTION 'draw_capacity_exceeded';
    END IF;
    IF NEW.seed IS NOT NULL AND NEW.seed < 1 THEN
        RAISE EXCEPTION 'invalid_seed';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_validate_match()
RETURNS trigger
LANGUAGE plpgsql
AS $$
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
$$;

CREATE OR REPLACE FUNCTION public.trg_validate_match_participant()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    participant_count integer;
BEGIN
    IF NEW.side NOT IN ('A', 'B') THEN
        RAISE EXCEPTION 'invalid_match_side';
    END IF;

    SELECT COUNT(*) INTO participant_count
    FROM "MatchParticipant"
    WHERE "match_id" = NEW.match_id
      AND "id" <> COALESCE(NEW.id, -1);

    IF participant_count >= 2 THEN
        RAISE EXCEPTION 'match_participant_limit_exceeded';
    END IF;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_validate_match_set()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.set_number IS NULL OR NEW.set_number < 1 THEN
        RAISE EXCEPTION 'invalid_set_number';
    END IF;
    IF NEW.team_a_games IS NOT NULL
       AND NEW.team_b_games IS NOT NULL
       AND NEW.team_a_games = NEW.team_b_games THEN
        RAISE EXCEPTION 'set_must_have_winner';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_validate_session()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.start_datetime IS NOT NULL AND NEW.end_datetime IS NOT NULL AND NEW.start_datetime > NEW.end_datetime THEN
        RAISE EXCEPTION 'invalid_session_dates';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_validate_sanction_target()
RETURNS trigger
LANGUAGE plpgsql
AS $$
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
$$;

CREATE OR REPLACE FUNCTION public.trg_normalize_user_account()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.email := lower(btrim(NEW.email));
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

    IF public.fn_crud_table_exists('Court') THEN
        DROP TRIGGER IF EXISTS biu_court_integrity ON "Court";
        CREATE TRIGGER biu_court_integrity
        BEFORE INSERT OR UPDATE ON "Court"
        FOR EACH ROW EXECUTE FUNCTION public.trg_validate_court();
    END IF;

    IF public.fn_crud_table_exists('Category') THEN
        DROP TRIGGER IF EXISTS biu_category_integrity ON "Category";
        CREATE TRIGGER biu_category_integrity
        BEFORE INSERT OR UPDATE ON "Category"
        FOR EACH ROW EXECUTE FUNCTION public.trg_validate_category();
    END IF;

    IF public.fn_crud_table_exists('SubCategory') THEN
        DROP TRIGGER IF EXISTS biu_subcategory_integrity ON "SubCategory";
        CREATE TRIGGER biu_subcategory_integrity
        BEFORE INSERT OR UPDATE ON "SubCategory"
        FOR EACH ROW EXECUTE FUNCTION public.trg_validate_subcategory();
    END IF;

    IF public.fn_crud_table_exists('Round') THEN
        DROP TRIGGER IF EXISTS biu_round_integrity ON "Round";
        CREATE TRIGGER biu_round_integrity
        BEFORE INSERT OR UPDATE ON "Round"
        FOR EACH ROW EXECUTE FUNCTION public.trg_validate_round();
    END IF;

    IF public.fn_crud_table_exists('Injury') THEN
        DROP TRIGGER IF EXISTS biu_injury_integrity ON "Injury";
        CREATE TRIGGER biu_injury_integrity
        BEFORE INSERT OR UPDATE ON "Injury"
        FOR EACH ROW EXECUTE FUNCTION public.trg_validate_injury();
    END IF;

    IF public.fn_crud_table_exists('TeamMember') THEN
        DROP TRIGGER IF EXISTS biu_team_member_integrity ON "TeamMember";
        CREATE TRIGGER biu_team_member_integrity
        BEFORE INSERT OR UPDATE ON "TeamMember"
        FOR EACH ROW EXECUTE FUNCTION public.trg_validate_team_member();
    END IF;

    IF public.fn_crud_table_exists('Entry') THEN
        DROP TRIGGER IF EXISTS biu_entry_integrity ON "Entry";
        CREATE TRIGGER biu_entry_integrity
        BEFORE INSERT OR UPDATE ON "Entry"
        FOR EACH ROW EXECUTE FUNCTION public.trg_validate_entry();
    END IF;

    IF public.fn_crud_table_exists('Match') THEN
        DROP TRIGGER IF EXISTS biu_match_schedule_integrity ON "Match";
        CREATE TRIGGER biu_match_schedule_integrity
        BEFORE INSERT OR UPDATE ON "Match"
        FOR EACH ROW EXECUTE FUNCTION public.trg_validate_match();
    END IF;

    IF public.fn_crud_table_exists('MatchParticipant') THEN
        DROP TRIGGER IF EXISTS biu_match_participant_integrity ON "MatchParticipant";
        CREATE TRIGGER biu_match_participant_integrity
        BEFORE INSERT OR UPDATE ON "MatchParticipant"
        FOR EACH ROW EXECUTE FUNCTION public.trg_validate_match_participant();
    END IF;

    IF public.fn_crud_table_exists('MatchSet')
       AND public.fn_crud_column_exists('MatchSet', 'team_a_games')
       AND public.fn_crud_column_exists('MatchSet', 'team_b_games') THEN
        DROP TRIGGER IF EXISTS biu_match_set_integrity ON "MatchSet";
        CREATE TRIGGER biu_match_set_integrity
        BEFORE INSERT OR UPDATE ON "MatchSet"
        FOR EACH ROW EXECUTE FUNCTION public.trg_validate_match_set();
    END IF;

    IF public.fn_crud_table_exists('Session') THEN
        DROP TRIGGER IF EXISTS biu_session_integrity ON "Session";
        CREATE TRIGGER biu_session_integrity
        BEFORE INSERT OR UPDATE ON "Session"
        FOR EACH ROW EXECUTE FUNCTION public.trg_validate_session();
    END IF;

    IF public.fn_crud_table_exists('Sanction') THEN
        DROP TRIGGER IF EXISTS biu_sanction_target_integrity ON "Sanction";
        CREATE TRIGGER biu_sanction_target_integrity
        BEFORE INSERT OR UPDATE ON "Sanction"
        FOR EACH ROW EXECUTE FUNCTION public.trg_validate_sanction_target();
    END IF;

    IF public.fn_crud_table_exists('UserAccount') AND public.fn_crud_column_exists('UserAccount', 'email') THEN
        DROP TRIGGER IF EXISTS biu_user_account_normalize ON "UserAccount";
        CREATE TRIGGER biu_user_account_normalize
        BEFORE INSERT OR UPDATE ON "UserAccount"
        FOR EACH ROW EXECUTE FUNCTION public.trg_normalize_user_account();
    END IF;
END $$;
"""


REVERSE_SQL = r"""
DO $$
DECLARE
    drop_stmt text;
BEGIN
    FOR drop_stmt IN
        SELECT format('DROP TRIGGER IF EXISTS %I ON %I', trigger_name, event_object_table)
        FROM information_schema.triggers
        WHERE trigger_schema = current_schema()
          AND trigger_name IN (
              'biu_tournament_dates',
              'biu_court_integrity',
              'biu_category_integrity',
              'biu_subcategory_integrity',
              'biu_round_integrity',
              'biu_injury_integrity',
              'biu_team_member_integrity',
              'biu_entry_integrity',
              'biu_match_schedule_integrity',
              'biu_match_participant_integrity',
              'biu_match_set_integrity',
              'biu_session_integrity',
              'biu_sanction_target_integrity',
              'biu_user_account_normalize'
          )
    LOOP
        EXECUTE drop_stmt;
    END LOOP;
END $$;

DROP FUNCTION IF EXISTS public.trg_validate_tournament_dates();
DROP FUNCTION IF EXISTS public.trg_validate_court();
DROP FUNCTION IF EXISTS public.trg_validate_category();
DROP FUNCTION IF EXISTS public.trg_validate_subcategory();
DROP FUNCTION IF EXISTS public.trg_validate_round();
DROP FUNCTION IF EXISTS public.trg_validate_injury();
DROP FUNCTION IF EXISTS public.trg_validate_team_member();
DROP FUNCTION IF EXISTS public.trg_validate_entry();
DROP FUNCTION IF EXISTS public.trg_validate_match();
DROP FUNCTION IF EXISTS public.trg_validate_match_participant();
DROP FUNCTION IF EXISTS public.trg_validate_match_set();
DROP FUNCTION IF EXISTS public.trg_validate_session();
DROP FUNCTION IF EXISTS public.trg_validate_sanction_target();
DROP FUNCTION IF EXISTS public.trg_normalize_user_account();

DO $$
DECLARE
    procedure_name text;
    procedure_signature text;
BEGIN
    FOREACH procedure_name IN ARRAY ARRAY[
        'sp_create_tournament',
        'sp_update_tournament',
        'sp_create_court',
        'sp_create_category',
        'sp_create_subcategory',
        'sp_create_round',
        'sp_create_player',
        'sp_create_injury',
        'sp_assign_injury_to_player',
        'sp_close_injury',
        'sp_create_team',
        'sp_add_team_member',
        'sp_create_entry',
        'sp_create_match',
        'sp_add_match_participant',
        'sp_register_match_set',
        'sp_finish_match',
        'sp_schedule_match',
        'sp_reschedule_match',
        'sp_create_session',
        'sp_add_match_to_session',
        'sp_create_official',
        'sp_assign_official_to_match',
        'sp_create_sanction',
        'sp_create_sanction_appeal',
        'sp_create_audit_log',
        'sp_create_user_account'
    ]
    LOOP
        FOR procedure_signature IN
            SELECT p.oid::regprocedure::text
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = current_schema()
              AND p.prokind = 'p'
              AND p.proname = procedure_name
        LOOP
            EXECUTE format('DROP PROCEDURE IF EXISTS %s', procedure_signature);
        END LOOP;
    END LOOP;
END $$;

DROP FUNCTION IF EXISTS public.fn_crud_insert_json(text, jsonb, text);
DROP FUNCTION IF EXISTS public.fn_crud_update_json(text, text, text, jsonb);
DROP FUNCTION IF EXISTS public.fn_crud_first_table(text[]);
DROP FUNCTION IF EXISTS public.fn_crud_column_exists(text, text);
DROP FUNCTION IF EXISTS public.fn_crud_table_exists(text);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_location_fields_as_text"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL + TRIGGER_SQL, reverse_sql=REVERSE_SQL),
    ]
