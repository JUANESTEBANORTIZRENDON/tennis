"""Automatiza siembra y fecha de jugadores inscritos."""

from django.db import migrations


SQL = r"""
DO $drop$
DECLARE
    procedure_name text;
    procedure_signature text;
BEGIN
    FOREACH procedure_name IN ARRAY ARRAY['sp_create_entry', 'sp_add_entry_team_player']
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
END
$drop$;

CREATE OR REPLACE PROCEDURE public.sp_create_entry(
    IN p_subcategory_id integer,
    IN p_team_id integer,
    IN p_qualifying_method character varying
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_seed integer;
BEGIN
    IF p_subcategory_id IS NULL OR p_team_id IS NULL THEN
        RAISE EXCEPTION 'invalid_entry_payload';
    END IF;

    SELECT COALESCE(MAX(seed), 0) + 1
    INTO v_seed
    FROM "Entry"
    WHERE subcategory_id = p_subcategory_id;

    PERFORM public.fn_crud_insert_json('Entry', jsonb_build_object(
        'subcategory_id', p_subcategory_id,
        'team_id', p_team_id,
        'seed', v_seed,
        'ranking_at_entry', NULL,
        'qualifying_method', COALESCE(NULLIF(p_qualifying_method, ''), 'Direct')
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
    IF p_subcategory_id IS NULL OR p_team_id IS NULL OR p_player_id IS NULL THEN
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
        WHERE tm.team_id = p_team_id
          AND tm.player_id = p_player_id
          AND tm.end_date IS NULL
    ) THEN
        RAISE EXCEPTION 'player_already_in_team';
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

    INSERT INTO "TeamMember" (team_id, player_id, role, start_date)
    VALUES (p_team_id, p_player_id, 'Player', CURRENT_DATE);
END;
$$;
"""


REVERSE_SQL = r"""
DROP PROCEDURE IF EXISTS public.sp_add_entry_team_player(integer, integer, character varying);
DROP PROCEDURE IF EXISTS public.sp_create_entry(integer, integer, character varying);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0024_player_entry_and_match_day_rules"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
