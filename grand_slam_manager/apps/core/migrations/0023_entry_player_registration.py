"""Agrega flujo de jugadores sobre equipos ya inscritos."""

from django.db import migrations


SQL = r"""
CREATE OR REPLACE FUNCTION public.sp_entered_teams_by_structure_json(
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
    SELECT to_jsonb(row_data)
    FROM (
        SELECT
            e.id AS entry_id,
            trn.id AS tournament_id,
            trn.name AS torneo,
            c.id AS category_id,
            c.name AS categoria,
            sc.id AS subcategory_id,
            sc.name AS cuadro,
            e.team_id,
            COALESCE(t.name, 'Equipo ' || e.team_id::text) AS equipo,
            COUNT(tm.player_id) AS total_jugadores,
            COALESCE(
                STRING_AGG(TRIM(CONCAT(p.first_name, ' ', p.last_name)), ', ' ORDER BY p.last_name, p.first_name),
                'Sin jugadores'
            ) AS jugadores
        FROM "Entry" e
        JOIN "SubCategory" sc ON sc.id = e.subcategory_id
        JOIN "Category" c ON c.id = sc.category_id
        JOIN "Tournament" trn ON trn.id = c.tournament_id
        JOIN "Team" t ON t.id = e.team_id
        LEFT JOIN "TeamMember" tm ON tm.team_id = t.id
        LEFT JOIN "Player" p ON p.id = tm.player_id
        WHERE (p_tournament_id IS NULL OR trn.id = p_tournament_id)
          AND (p_category_id IS NULL OR c.id = p_category_id)
          AND (p_subcategory_id IS NULL OR sc.id = p_subcategory_id)
        GROUP BY e.id, trn.id, trn.name, c.id, c.name, sc.id, sc.name, e.team_id, t.name
        ORDER BY trn.name, c.name, sc.name, t.name, e.id
        LIMIT safe_limit
    ) row_data;
END;
$$;

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
          AND p.proname = 'sp_add_entry_team_player'
    LOOP
        EXECUTE format('DROP PROCEDURE IF EXISTS %s', procedure_signature);
    END LOOP;
END
$drop$;

CREATE OR REPLACE PROCEDURE public.sp_add_entry_team_player(
    IN p_subcategory_id integer,
    IN p_team_id integer,
    IN p_player_id character varying,
    IN p_role character varying,
    IN p_start_date date
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_subcategory_id IS NULL OR p_team_id IS NULL OR p_player_id IS NULL THEN
        RAISE EXCEPTION 'invalid_entry_player_payload';
    END IF;

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

    INSERT INTO "TeamMember" (team_id, player_id, role, start_date)
    VALUES (p_team_id, p_player_id, COALESCE(NULLIF(p_role, ''), 'Player'), COALESCE(p_start_date, CURRENT_DATE));
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_seed_entry_registration_test_data()
LANGUAGE plpgsql
AS $$
DECLARE
    today date := CURRENT_DATE;
    i integer;
    pid text;
    tid integer;
    first_names text[] := ARRAY['Laura','Paula','Elena','Diana','Carlos','Ivan'];
    last_names text[] := ARRAY['Prueba','Reserva','Dobles','Alterna','Suplente','Nuevo'];
    genders text[] := ARRAY['F','F','F','F','M','M'];
BEGIN
    FOR i IN 1..array_length(first_names, 1) LOOP
        pid := 'P-TEST-ENTRY-' || lpad(i::text, 3, '0');

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
            DATE '2000-01-01' + (i * 120),
            'COL',
            170 + i,
            60 + i,
            'R'::hand_type,
            2020 + (i % 4),
            'Jugador de prueba para validar inscripciones por equipo.'
        )
        ON CONFLICT (id) DO NOTHING;

        INSERT INTO "Team" (name, notes)
        SELECT 'Equipo prueba inscripcion ' || i::text, 'Equipo disponible para pruebas de inscripcion.'
        WHERE NOT EXISTS (
            SELECT 1 FROM "Team" WHERE name = 'Equipo prueba inscripcion ' || i::text
        )
        RETURNING id INTO tid;

        IF tid IS NULL THEN
            SELECT id INTO tid FROM "Team" WHERE name = 'Equipo prueba inscripcion ' || i::text LIMIT 1;
        END IF;

        INSERT INTO "TeamMember" (team_id, player_id, role, start_date)
        SELECT tid, pid, 'Player', today
        WHERE NOT EXISTS (
            SELECT 1 FROM "TeamMember"
            WHERE team_id = tid
              AND player_id = pid
        );
    END LOOP;
END;
$$;

CALL public.sp_seed_entry_registration_test_data();
"""


REVERSE_SQL = r"""
DROP PROCEDURE IF EXISTS public.sp_seed_entry_registration_test_data();
DROP PROCEDURE IF EXISTS public.sp_add_entry_team_player(integer, integer, character varying, character varying, date);
DROP FUNCTION IF EXISTS public.sp_entered_teams_by_structure_json(integer, integer, integer, integer);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0022_coach_user_team_rules"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
