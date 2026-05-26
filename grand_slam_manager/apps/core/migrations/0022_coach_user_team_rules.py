"""Vincula entrenadores con usuarios/equipos y refuerza sus asignaciones."""

from django.db import migrations


SQL = r"""
ALTER TABLE "Coach" ADD COLUMN IF NOT EXISTS "user_id" integer;
ALTER TABLE "Coach" ADD COLUMN IF NOT EXISTS "team_id" integer;

DO $$
BEGIN
    IF public.fn_crud_table_exists('Role') THEN
        INSERT INTO "Role" ("name", "description")
        SELECT 'Coach', 'Entrenador de equipo'
        WHERE NOT EXISTS (
            SELECT 1 FROM "Role" WHERE lower("name") IN ('coach', 'entrenador')
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_coach_user'
    ) THEN
        ALTER TABLE "Coach"
        ADD CONSTRAINT "fk_coach_user"
        FOREIGN KEY ("user_id") REFERENCES "UserAccount"("id")
        ON DELETE SET NULL NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_coach_team'
    ) THEN
        ALTER TABLE "Coach"
        ADD CONSTRAINT "fk_coach_team"
        FOREIGN KEY ("team_id") REFERENCES "Team"("id")
        ON DELETE RESTRICT NOT VALID;
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_coach_user_not_null
ON "Coach" ("user_id")
WHERE "user_id" IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_coach_team
ON "Coach" ("team_id");

CREATE OR REPLACE FUNCTION public.trg_validate_coach_team()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.team_id IS NULL THEN
        RAISE EXCEPTION 'coach_team_required';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_validate_player_coach_team()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_team_id integer;
BEGIN
    SELECT c.team_id
    INTO v_team_id
    FROM "Coach" c
    WHERE c.id = NEW.coach_id;

    IF v_team_id IS NULL THEN
        RAISE EXCEPTION 'coach_team_required';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM "TeamMember" tm
        WHERE tm.team_id = v_team_id
          AND tm.player_id = NEW.player_id
    ) THEN
        RAISE EXCEPTION 'coach_player_team_mismatch';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS biu_coach_team_integrity ON "Coach";
CREATE TRIGGER biu_coach_team_integrity
BEFORE INSERT OR UPDATE ON "Coach"
FOR EACH ROW EXECUTE FUNCTION public.trg_validate_coach_team();

DROP TRIGGER IF EXISTS biu_player_coach_team_integrity ON "PlayerCoach";
CREATE TRIGGER biu_player_coach_team_integrity
BEFORE INSERT OR UPDATE ON "PlayerCoach"
FOR EACH ROW EXECUTE FUNCTION public.trg_validate_player_coach_team();

DO $drop$
DECLARE
    procedure_name text;
    procedure_signature text;
BEGIN
    FOREACH procedure_name IN ARRAY ARRAY['sp_create_coach', 'sp_assign_coach_to_player']
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

CREATE OR REPLACE PROCEDURE public.sp_create_coach(
    IN p_user_id integer,
    IN p_team_id integer,
    IN p_first_name character varying,
    IN p_last_name character varying,
    IN p_nationality character varying,
    IN p_birth_date date,
    IN p_license_number character varying
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM public.fn_crud_insert_json('Coach', jsonb_build_object(
        'user_id', p_user_id,
        'team_id', p_team_id,
        'first_name', p_first_name,
        'last_name', p_last_name,
        'nationality', p_nationality,
        'birth_date', p_birth_date,
        'license_number', NULLIF(p_license_number, '')
    ));
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_assign_coach_to_player(
    IN p_coach_id integer,
    IN p_player_id character varying,
    IN p_start_date date
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM public.fn_crud_insert_json('PlayerCoach', jsonb_build_object(
        'coach_id', p_coach_id,
        'player_id', p_player_id,
        'start_date', p_start_date
    ), NULL);
END;
$$;

CREATE OR REPLACE FUNCTION public.sp_coaches_overview_json(p_limit integer DEFAULT 300)
RETURNS SETOF jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    safe_limit integer := LEAST(GREATEST(COALESCE(p_limit, 300), 1), 1000);
BEGIN
    IF NOT public.fn_crud_table_exists('Coach') THEN
        RETURN;
    END IF;

    RETURN QUERY
    SELECT to_jsonb(row_data)
    FROM (
        SELECT
            c.id AS coach_id,
            TRIM(CONCAT(c.first_name, ' ', c.last_name)) AS entrenador,
            c.user_id,
            COALESCE(NULLIF(TRIM(CONCAT(ua.full_name, ' ', ua.email)), ''), 'Sin usuario') AS usuario,
            COALESCE(r.name, 'Sin rol') AS rol_usuario,
            c.team_id,
            COALESCE(t.name, 'Sin equipo') AS equipo,
            COUNT(DISTINCT pc.player_id) AS jugadores_asignados,
            COALESCE(
                STRING_AGG(DISTINCT TRIM(CONCAT(p.first_name, ' ', p.last_name)), ', ' ORDER BY TRIM(CONCAT(p.first_name, ' ', p.last_name))),
                'Sin jugadores'
            ) AS jugadores,
            c.license_number,
            c.nationality
        FROM "Coach" c
        LEFT JOIN "UserAccount" ua ON ua.id = c.user_id
        LEFT JOIN "UserRole" ur ON ur.user_id = ua.id
        LEFT JOIN "Role" r ON r.id = ur.role_id
        LEFT JOIN "Team" t ON t.id = c.team_id
        LEFT JOIN "PlayerCoach" pc ON pc.coach_id = c.id AND pc.end_date IS NULL
        LEFT JOIN "Player" p ON p.id = pc.player_id
        GROUP BY c.id, c.first_name, c.last_name, c.user_id, ua.full_name, ua.email, r.name, c.team_id, t.name, c.license_number, c.nationality
        ORDER BY c.last_name, c.first_name, c.id
        LIMIT safe_limit
    ) row_data;
END;
$$;

CREATE OR REPLACE FUNCTION public.sp_available_coach_players_json(p_coach_id integer)
RETURNS SETOF jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_team_id integer;
BEGIN
    IF p_coach_id IS NULL THEN
        RETURN;
    END IF;

    SELECT team_id INTO v_team_id
    FROM "Coach"
    WHERE id = p_coach_id;

    IF v_team_id IS NULL THEN
        RETURN;
    END IF;

    RETURN QUERY
    SELECT to_jsonb(row_data)
    FROM (
        SELECT
            p.id AS player_id,
            TRIM(CONCAT(p.first_name, ' ', p.last_name)) AS jugador,
            t.name AS equipo,
            p.country_code AS pais
        FROM "TeamMember" tm
        JOIN "Player" p ON p.id = tm.player_id
        JOIN "Team" t ON t.id = tm.team_id
        WHERE tm.team_id = v_team_id
          AND NOT EXISTS (
              SELECT 1
              FROM "PlayerCoach" pc
              WHERE pc.coach_id = p_coach_id
                AND pc.player_id = p.id
                AND pc.end_date IS NULL
          )
        ORDER BY p.last_name, p.first_name, p.id
    ) row_data;
END;
$$;
"""


REVERSE_SQL = r"""
DROP FUNCTION IF EXISTS public.sp_available_coach_players_json(integer);
DROP FUNCTION IF EXISTS public.sp_coaches_overview_json(integer);

DROP PROCEDURE IF EXISTS public.sp_assign_coach_to_player(integer, character varying, date);
DROP PROCEDURE IF EXISTS public.sp_create_coach(integer, integer, character varying, character varying, character varying, date, character varying);

DROP TRIGGER IF EXISTS biu_player_coach_team_integrity ON "PlayerCoach";
DROP TRIGGER IF EXISTS biu_coach_team_integrity ON "Coach";
DROP FUNCTION IF EXISTS public.trg_validate_player_coach_team();
DROP FUNCTION IF EXISTS public.trg_validate_coach_team();

DROP INDEX IF EXISTS idx_coach_team;
DROP INDEX IF EXISTS uq_coach_user_not_null;

ALTER TABLE "Coach" DROP CONSTRAINT IF EXISTS "fk_coach_team";
ALTER TABLE "Coach" DROP CONSTRAINT IF EXISTS "fk_coach_user";
ALTER TABLE "Coach" DROP COLUMN IF EXISTS "team_id";
ALTER TABLE "Coach" DROP COLUMN IF EXISTS "user_id";
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0021_entry_option_filters_and_clean_demo_seed"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
