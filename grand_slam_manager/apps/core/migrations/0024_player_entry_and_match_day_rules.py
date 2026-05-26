"""Refuerza disponibilidad de jugadores por torneo y dia de partido."""

from django.db import migrations


SQL = r"""
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
            FROM "TeamMember" tm_same
            WHERE tm_same.team_id = p_team_id
              AND tm_same.player_id = p.id
              AND tm_same.end_date IS NULL
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
    IN p_start_date date
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
    VALUES (p_team_id, p_player_id, 'Player', COALESCE(p_start_date, CURRENT_DATE));
END;
$$;

CREATE OR REPLACE FUNCTION public.fn_match_has_player_day_conflict(
    p_match_id integer,
    p_team_id integer,
    p_scheduled_datetime timestamp without time zone
)
RETURNS boolean
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    IF p_match_id IS NULL OR p_team_id IS NULL OR p_scheduled_datetime IS NULL THEN
        RETURN FALSE;
    END IF;

    RETURN EXISTS (
        SELECT 1
        FROM "TeamMember" new_tm
        JOIN "TeamMember" other_tm ON other_tm.player_id = new_tm.player_id
        JOIN "MatchParticipant" other_mp ON other_mp.team_id = other_tm.team_id
        JOIN "Match" other_m ON other_m.id = other_mp.match_id
        WHERE new_tm.team_id = p_team_id
          AND new_tm.end_date IS NULL
          AND other_tm.end_date IS NULL
          AND other_m.id <> p_match_id
          AND other_m.scheduled_datetime IS NOT NULL
          AND other_m.scheduled_datetime::date = p_scheduled_datetime::date
          AND COALESCE(other_m.status::text, '') NOT IN ('Cancelled')
    );
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_validate_match_participant_player_day()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_scheduled_datetime timestamp without time zone;
BEGIN
    SELECT scheduled_datetime
    INTO v_scheduled_datetime
    FROM "Match"
    WHERE id = NEW.match_id;

    IF public.fn_match_has_player_day_conflict(NEW.match_id, NEW.team_id, v_scheduled_datetime) THEN
        RAISE EXCEPTION 'player_match_day_conflict';
    END IF;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_validate_match_schedule_player_day()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    participant record;
BEGIN
    IF NEW.scheduled_datetime IS NULL THEN
        RETURN NEW;
    END IF;

    FOR participant IN
        SELECT team_id
        FROM "MatchParticipant"
        WHERE match_id = NEW.id
    LOOP
        IF public.fn_match_has_player_day_conflict(NEW.id, participant.team_id, NEW.scheduled_datetime) THEN
            RAISE EXCEPTION 'player_match_day_conflict';
        END IF;
    END LOOP;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS biu_match_participant_player_day ON "MatchParticipant";
CREATE TRIGGER biu_match_participant_player_day
BEFORE INSERT OR UPDATE ON "MatchParticipant"
FOR EACH ROW EXECUTE FUNCTION public.trg_validate_match_participant_player_day();

DROP TRIGGER IF EXISTS biu_match_schedule_player_day ON "Match";
CREATE TRIGGER biu_match_schedule_player_day
BEFORE INSERT OR UPDATE OF scheduled_datetime ON "Match"
FOR EACH ROW EXECUTE FUNCTION public.trg_validate_match_schedule_player_day();
"""


REVERSE_SQL = r"""
DROP TRIGGER IF EXISTS biu_match_schedule_player_day ON "Match";
DROP TRIGGER IF EXISTS biu_match_participant_player_day ON "MatchParticipant";
DROP FUNCTION IF EXISTS public.trg_validate_match_schedule_player_day();
DROP FUNCTION IF EXISTS public.trg_validate_match_participant_player_day();
DROP FUNCTION IF EXISTS public.fn_match_has_player_day_conflict(integer, integer, timestamp without time zone);
DROP PROCEDURE IF EXISTS public.sp_add_entry_team_player(integer, integer, character varying, date);
DROP FUNCTION IF EXISTS public.sp_available_entry_players_json(integer, integer, integer);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0023_entry_player_registration"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
