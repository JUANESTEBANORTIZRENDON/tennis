"""Reglas de equipo unico, vista de inscripciones y CRUD administrativo."""

from django.db import migrations


SQL = r"""
CREATE OR REPLACE FUNCTION public.trg_validate_single_active_team_member()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.player_id IS NULL OR NEW.end_date IS NOT NULL THEN
        RETURN NEW;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM "TeamMember" tm
        WHERE tm.player_id = NEW.player_id
          AND tm.end_date IS NULL
          AND NOT (
              tm.team_id = NEW.team_id
              AND COALESCE(tm.start_date, DATE '1900-01-01') = COALESCE(NEW.start_date, DATE '1900-01-01')
          )
    ) THEN
        RAISE EXCEPTION 'player_already_has_active_team';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS biu_team_member_single_active_team ON "TeamMember";
CREATE TRIGGER biu_team_member_single_active_team
BEFORE INSERT OR UPDATE ON "TeamMember"
FOR EACH ROW EXECUTE FUNCTION public.trg_validate_single_active_team_member();

CREATE OR REPLACE PROCEDURE public.sp_add_team_member(
    IN p_team_id integer,
    IN p_player_id character varying,
    IN p_role character varying DEFAULT 'Player',
    IN p_start_date date DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_team_id IS NULL OR p_player_id IS NULL OR btrim(p_player_id) = '' THEN
        RAISE EXCEPTION 'invalid_team_member_payload';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM "TeamMember" tm
        WHERE tm.player_id = p_player_id
          AND tm.end_date IS NULL
    ) THEN
        RAISE EXCEPTION 'player_already_has_active_team';
    END IF;

    PERFORM public.fn_crud_insert_json('TeamMember', jsonb_build_object(
        'team_id', p_team_id,
        'player_id', p_player_id,
        'role', COALESCE(NULLIF(p_role, ''), 'Player'),
        'start_date', COALESCE(p_start_date, CURRENT_DATE)
    ));
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_add_entry_team_player(
    IN p_subcategory_id integer,
    IN p_team_id integer,
    IN p_player_id character varying
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_tournament_id integer;
BEGIN
    IF p_subcategory_id IS NULL OR p_team_id IS NULL OR p_player_id IS NULL OR btrim(p_player_id) = '' THEN
        RAISE EXCEPTION 'invalid_entry_player_payload';
    END IF;

    SELECT c.tournament_id
    INTO v_tournament_id
    FROM "SubCategory" sc
    JOIN "Category" c ON c.id = sc.category_id
    WHERE sc.id = p_subcategory_id;

    IF NOT EXISTS (
        SELECT 1
        FROM "Entry" e
        WHERE e.subcategory_id = p_subcategory_id
          AND e.team_id = p_team_id
    ) THEN
        RAISE EXCEPTION 'team_not_entered_in_subcategory';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM "TeamMember" tm
        WHERE tm.player_id = p_player_id
          AND tm.end_date IS NULL
    ) THEN
        RAISE EXCEPTION 'player_already_has_active_team';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM "TeamMember" tm
        JOIN "Entry" e ON e.team_id = tm.team_id
        JOIN "SubCategory" sc ON sc.id = e.subcategory_id
        JOIN "Category" c ON c.id = sc.category_id
        WHERE c.tournament_id = v_tournament_id
          AND tm.player_id = p_player_id
          AND tm.end_date IS NULL
    ) THEN
        RAISE EXCEPTION 'player_already_entered_in_tournament';
    END IF;

    PERFORM public.fn_crud_insert_json('TeamMember', jsonb_build_object(
        'team_id', p_team_id,
        'player_id', p_player_id,
        'role', 'Player',
        'start_date', CURRENT_DATE
    ));
END;
$$;

CREATE OR REPLACE FUNCTION public.sp_available_team_member_players_json(p_team_id integer)
RETURNS TABLE(row_data jsonb)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    IF p_team_id IS NULL THEN
        RETURN;
    END IF;

    RETURN QUERY
    SELECT to_jsonb(q)
    FROM (
        SELECT
            p.id AS player_id,
            TRIM(CONCAT(p.first_name, ' ', p.last_name)) AS jugador,
            p.country_code AS pais
        FROM "Player" p
        WHERE NOT EXISTS (
            SELECT 1
            FROM "TeamMember" tm
            WHERE tm.player_id = p.id
              AND tm.end_date IS NULL
        )
        ORDER BY p.last_name, p.first_name, p.id
        LIMIT 500
    ) q;
END;
$$;

CREATE OR REPLACE FUNCTION public.sp_available_entry_players_json(
    p_tournament_id integer DEFAULT NULL,
    p_team_id integer DEFAULT NULL,
    p_limit integer DEFAULT 300
)
RETURNS SETOF jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    safe_limit integer := LEAST(GREATEST(COALESCE(p_limit, 300), 1), 1000);
BEGIN
    IF p_team_id IS NULL THEN
        RETURN;
    END IF;

    RETURN QUERY
    SELECT to_jsonb(row_data)
    FROM (
        SELECT
            p.id AS player_id,
            TRIM(CONCAT(p.first_name, ' ', p.last_name)) AS jugador,
            p.country_code AS pais
        FROM "Player" p
        WHERE NOT EXISTS (
            SELECT 1
            FROM "TeamMember" tm_any
            WHERE tm_any.player_id = p.id
              AND tm_any.end_date IS NULL
        )
          AND (
              p_tournament_id IS NULL
              OR NOT EXISTS (
                  SELECT 1
                  FROM "TeamMember" tm
                  JOIN "Entry" e ON e.team_id = tm.team_id
                  JOIN "SubCategory" sc ON sc.id = e.subcategory_id
                  JOIN "Category" c ON c.id = sc.category_id
                  WHERE c.tournament_id = p_tournament_id
                    AND tm.player_id = p.id
                    AND tm.end_date IS NULL
              )
          )
        ORDER BY p.last_name, p.first_name, p.id
        LIMIT safe_limit
    ) row_data;
END;
$$;

CREATE OR REPLACE FUNCTION public.sp_team_members_json(
    p_team_id integer DEFAULT NULL,
    p_limit integer DEFAULT 300
)
RETURNS SETOF jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    safe_limit integer := LEAST(GREATEST(COALESCE(p_limit, 300), 1), 1000);
BEGIN
    IF p_team_id IS NULL THEN
        RETURN;
    END IF;

    RETURN QUERY
    SELECT to_jsonb(row_data)
    FROM (
        SELECT
            tm.team_id,
            t.name AS equipo,
            tm.player_id,
            TRIM(CONCAT(p.first_name, ' ', p.last_name)) AS jugador,
            p.country_code AS pais,
            tm.role,
            tm.start_date,
            tm.end_date
        FROM "TeamMember" tm
        JOIN "Team" t ON t.id = tm.team_id
        JOIN "Player" p ON p.id = tm.player_id
        WHERE tm.team_id = p_team_id
          AND tm.end_date IS NULL
        ORDER BY p.last_name, p.first_name, p.id
        LIMIT safe_limit
    ) row_data;
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

    RETURN QUERY
    WITH counts AS (
        SELECT subcategory_id, COUNT(*) AS used_slots
        FROM "Entry"
        GROUP BY subcategory_id
    ),
    team_players AS (
        SELECT
            tm.team_id,
            COUNT(tm.player_id) AS active_players,
            STRING_AGG(TRIM(CONCAT(p.first_name, ' ', p.last_name)), ', ' ORDER BY p.last_name, p.first_name) AS player_names
        FROM "TeamMember" tm
        JOIN "Player" p ON p.id = tm.player_id
        WHERE tm.end_date IS NULL
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
            COALESCE(t.name, 'Equipo ' || e.team_id::text) AS equipo,
            COALESCE(NULLIF(tp.player_names, ''), 'Sin jugadores') AS jugadores,
            COALESCE(tp.active_players, 0) AS jugadores_inscritos,
            e.seed,
            e.ranking_at_entry,
            e.qualifying_method,
            sc.draw_size,
            (sc.draw_size - COALESCE(counts.used_slots, 0)) AS available_slots
        FROM "Entry" e
        LEFT JOIN "SubCategory" sc ON sc.id = e.subcategory_id
        LEFT JOIN "Category" c ON c.id = sc.category_id
        LEFT JOIN "Tournament" trn ON trn.id = c.tournament_id
        LEFT JOIN "Team" t ON t.id = e.team_id
        LEFT JOIN team_players tp ON tp.team_id = e.team_id
        LEFT JOIN counts ON counts.subcategory_id = e.subcategory_id
        WHERE (p_tournament_id IS NULL OR trn.id = p_tournament_id)
          AND (p_category_id IS NULL OR c.id = p_category_id)
          AND (p_subcategory_id IS NULL OR sc.id = p_subcategory_id)
        ORDER BY trn.name NULLS LAST, c.name NULLS LAST, sc.name NULLS LAST, e.seed NULLS LAST, equipo
        LIMIT safe_limit
    ) row_data;
END;
$$;

CREATE OR REPLACE FUNCTION public.sp_admin_tables_json()
RETURNS SETOF jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    table_row record;
    total bigint;
BEGIN
    FOR table_row IN
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = current_schema()
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
    LOOP
        EXECUTE format('SELECT COUNT(*) FROM %I', table_row.table_name) INTO total;
        RETURN NEXT jsonb_build_object('table_name', table_row.table_name, 'rows', total);
    END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION public.sp_admin_table_columns_json(p_table text)
RETURNS SETOF jsonb
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    IF NOT public.fn_crud_table_exists(p_table) THEN
        RAISE EXCEPTION 'admin_table_not_found';
    END IF;

    RETURN QUERY
    SELECT to_jsonb(row_data)
    FROM (
        SELECT
            c.column_name,
            c.data_type,
            c.udt_name,
            c.is_nullable = 'YES' AS nullable,
            c.column_default,
            c.character_maximum_length,
            c.is_identity = 'YES' AS is_identity,
            EXISTS (
                SELECT 1
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON kcu.constraint_name = tc.constraint_name
                 AND kcu.table_schema = tc.table_schema
                 AND kcu.table_name = tc.table_name
                WHERE tc.table_schema = current_schema()
                  AND tc.table_name = p_table
                  AND tc.constraint_type = 'PRIMARY KEY'
                  AND kcu.column_name = c.column_name
            ) AS is_primary_key
        FROM information_schema.columns c
        WHERE c.table_schema = current_schema()
          AND c.table_name = p_table
        ORDER BY c.ordinal_position
    ) row_data;
END;
$$;

CREATE OR REPLACE FUNCTION public.sp_admin_table_rows_json(
    p_table text,
    p_search text DEFAULT NULL,
    p_limit integer DEFAULT 300
)
RETURNS SETOF jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    safe_limit integer := LEAST(GREATEST(COALESCE(p_limit, 300), 1), 1000);
    where_sql text := '';
    search_sql text;
BEGIN
    IF NOT public.fn_crud_table_exists(p_table) THEN
        RAISE EXCEPTION 'admin_table_not_found';
    END IF;

    IF p_search IS NOT NULL AND btrim(p_search) <> '' THEN
        SELECT string_agg(format('CAST(%I AS text) ILIKE $1', column_name), ' OR ')
        INTO search_sql
        FROM (
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = p_table
            ORDER BY ordinal_position
            LIMIT 12
        ) cols;
        IF search_sql IS NOT NULL THEN
            where_sql := ' WHERE ' || search_sql;
        END IF;
    END IF;

    IF where_sql = '' THEN
        RETURN QUERY EXECUTE format('SELECT to_jsonb(t) FROM (SELECT * FROM %I LIMIT %s) t', p_table, safe_limit);
    ELSE
        RETURN QUERY EXECUTE format('SELECT to_jsonb(t) FROM (SELECT * FROM %I%s LIMIT %s) t', p_table, where_sql, safe_limit)
        USING '%' || p_search || '%';
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION public.sp_admin_row_json(
    p_table text,
    p_pk_column text,
    p_pk_value text
)
RETURNS jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    result jsonb;
BEGIN
    IF NOT public.fn_crud_table_exists(p_table) OR NOT public.fn_crud_column_exists(p_table, p_pk_column) THEN
        RAISE EXCEPTION 'admin_table_not_found';
    END IF;

    EXECUTE format('SELECT to_jsonb(t) FROM (SELECT * FROM %I WHERE %I::text = $1 LIMIT 1) t', p_table, p_pk_column)
    INTO result
    USING p_pk_value;
    RETURN result;
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_admin_upsert_row(
    IN p_table text,
    IN p_pk_column text,
    IN p_pk_value text,
    IN p_payload jsonb
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT public.fn_crud_table_exists(p_table) OR NOT public.fn_crud_column_exists(p_table, p_pk_column) THEN
        RAISE EXCEPTION 'admin_table_not_found';
    END IF;

    IF COALESCE(NULLIF(p_pk_value, ''), '') = '' THEN
        PERFORM public.fn_crud_insert_json(p_table, COALESCE(p_payload, '{}'::jsonb), p_pk_column);
    ELSE
        PERFORM public.fn_crud_update_json(p_table, p_pk_column, p_pk_value, COALESCE(p_payload, '{}'::jsonb));
    END IF;
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_admin_delete_row(
    IN p_table text,
    IN p_pk_column text,
    IN p_pk_value text
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT public.fn_crud_table_exists(p_table) OR NOT public.fn_crud_column_exists(p_table, p_pk_column) THEN
        RAISE EXCEPTION 'admin_table_not_found';
    END IF;
    IF p_pk_value IS NULL OR btrim(p_pk_value) = '' THEN
        RAISE EXCEPTION 'admin_invalid_pk';
    END IF;

    EXECUTE format('DELETE FROM %I WHERE %I::text = $1', p_table, p_pk_column)
    USING p_pk_value;
END;
$$;
"""


REVERSE_SQL = r"""
DROP PROCEDURE IF EXISTS public.sp_admin_delete_row(text, text, text);
DROP PROCEDURE IF EXISTS public.sp_admin_upsert_row(text, text, text, jsonb);
DROP FUNCTION IF EXISTS public.sp_admin_row_json(text, text, text);
DROP FUNCTION IF EXISTS public.sp_admin_table_rows_json(text, text, integer);
DROP FUNCTION IF EXISTS public.sp_admin_table_columns_json(text);
DROP FUNCTION IF EXISTS public.sp_admin_tables_json();
DROP FUNCTION IF EXISTS public.sp_team_members_json(integer, integer);
DROP TRIGGER IF EXISTS biu_team_member_single_active_team ON "TeamMember";
DROP FUNCTION IF EXISTS public.trg_validate_single_active_team_member();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0029_global_courts_pairing_schedule_officials"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
