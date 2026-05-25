"""Agrega rutinas almacenadas para lecturas usadas por servicios."""

from django.db import migrations


SQL = r"""
CREATE OR REPLACE FUNCTION public.fn_read_first_column(p_table text, p_candidates text[])
RETURNS text
LANGUAGE plpgsql
STABLE
AS $$
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
$$;

CREATE OR REPLACE FUNCTION public.fn_read_where_clause(p_table text, p_filters jsonb)
RETURNS text
LANGUAGE plpgsql
STABLE
AS $$
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
$$;

CREATE OR REPLACE FUNCTION public.sp_select_table_json(
    p_table text,
    p_filters jsonb DEFAULT '{}'::jsonb,
    p_search text DEFAULT NULL,
    p_order_candidates text[] DEFAULT ARRAY[]::text[],
    p_limit integer DEFAULT 200
)
RETURNS SETOF jsonb
LANGUAGE plpgsql
STABLE
AS $$
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
$$;

CREATE OR REPLACE FUNCTION public.sp_select_by_id_json(
    p_table text,
    p_object_id text,
    p_id_candidates text[] DEFAULT ARRAY[]::text[]
)
RETURNS jsonb
LANGUAGE plpgsql
STABLE
AS $$
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
$$;

CREATE OR REPLACE FUNCTION public.sp_safe_count(
    p_table text,
    p_filters jsonb DEFAULT '{}'::jsonb
)
RETURNS integer
LANGUAGE plpgsql
STABLE
AS $$
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
$$;

CREATE OR REPLACE FUNCTION public.sp_authenticate_user_json(p_email text)
RETURNS jsonb
LANGUAGE plpgsql
STABLE
AS $$
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
$$;

CREATE OR REPLACE FUNCTION public.sp_list_courts_json()
RETURNS SETOF jsonb
LANGUAGE plpgsql
STABLE
AS $$
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
$$;

CREATE OR REPLACE FUNCTION public.sp_list_entries_with_slots_json()
RETURNS SETOF jsonb
LANGUAGE plpgsql
STABLE
AS $$
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
$$;

CREATE OR REPLACE FUNCTION public.sp_team_member_count(p_team_id integer)
RETURNS integer
LANGUAGE plpgsql
STABLE
AS $$
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
$$;
"""


REVERSE_SQL = r"""
DROP FUNCTION IF EXISTS public.sp_team_member_count(integer);
DROP FUNCTION IF EXISTS public.sp_list_entries_with_slots_json();
DROP FUNCTION IF EXISTS public.sp_list_courts_json();
DROP FUNCTION IF EXISTS public.sp_authenticate_user_json(text);
DROP FUNCTION IF EXISTS public.sp_safe_count(text, jsonb);
DROP FUNCTION IF EXISTS public.sp_select_by_id_json(text, text, text[]);
DROP FUNCTION IF EXISTS public.sp_select_table_json(text, jsonb, text, text[], integer);
DROP FUNCTION IF EXISTS public.fn_read_where_clause(text, jsonb);
DROP FUNCTION IF EXISTS public.fn_read_first_column(text, text[]);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_crud_procedures_and_integrity_triggers"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
