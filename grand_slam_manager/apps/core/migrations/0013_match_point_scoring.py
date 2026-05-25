from django.db import migrations


SQL = r"""
CREATE OR REPLACE FUNCTION public.trg_validate_match_set()
RETURNS trigger
LANGUAGE plpgsql
AS $$
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
$$;

CREATE OR REPLACE FUNCTION public.trg_validate_match_point_score()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    match_status text;
    point_match_id integer;
    game_winner integer;
    winner_team integer;
    participant_count integer;
BEGIN
    IF NEW.game_id IS NULL OR NEW.winner_player_id IS NULL THEN
        RAISE EXCEPTION 'invalid_point_payload';
    END IF;

    SELECT ms.match_id, mg.winner_team_id
    INTO point_match_id, game_winner
    FROM "MatchGame" mg
    JOIN "MatchSet" ms ON ms.id = mg.match_set_id
    WHERE mg.id = NEW.game_id;

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

    SELECT tm.team_id
    INTO winner_team
    FROM "TeamMember" tm
    WHERE tm.player_id = NEW.winner_player_id
    LIMIT 1;

    IF winner_team IS NULL THEN
        RAISE EXCEPTION 'point_winner_not_in_team';
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
        WHERE game_id = NEW.game_id;
    END IF;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.fn_tennis_point_label(p_points_for integer, p_points_against integer)
RETURNS text
LANGUAGE plpgsql
IMMUTABLE
AS $$
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
$$;

CREATE OR REPLACE FUNCTION public.fn_tennis_point_label(p_points_for bigint, p_points_against bigint)
RETURNS text
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    RETURN public.fn_tennis_point_label(p_points_for::integer, p_points_against::integer);
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_register_match_point(
    IN p_match_id integer,
    IN p_side text
)
LANGUAGE plpgsql
AS $$
DECLARE
    normalized_side text := upper(btrim(COALESCE(p_side, '')));
    match_status text;
    best_of_sets integer := 3;
    sets_to_win integer := 2;
    team_a integer;
    team_b integer;
    winner_team integer;
    loser_team integer;
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
    loser_team := CASE WHEN normalized_side = 'A' THEN team_b ELSE team_a END;

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
            SET sets_won = CASE WHEN team_id = team_a THEN sets_a WHEN team_id = team_b THEN sets_b ELSE sets_won END,
                games_won = CASE WHEN team_id = team_a THEN games_a WHEN team_id = team_b THEN games_b ELSE games_won END,
                points_won = CASE WHEN team_id = team_a THEN points_a WHEN team_id = team_b THEN points_b ELSE points_won END
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
$$;

CREATE OR REPLACE FUNCTION public.sp_match_development_detail_json(p_match_id integer)
RETURNS jsonb
LANGUAGE plpgsql
STABLE
AS $$
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
                ''set_number'', COALESCE((SELECT set_number FROM current_set), (SELECT next_set FROM sets), 1),
                ''game_number'', COALESCE((SELECT game_number FROM current_game), (SELECT game_number FROM next_game), 1),
                ''games_a'', COALESCE((SELECT team_a_games FROM current_set), 0),
                ''games_b'', COALESCE((SELECT team_b_games FROM current_set), 0),
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
$$;

DO $$
BEGIN
    IF public.fn_crud_table_exists('MatchSet')
       AND public.fn_crud_column_exists('MatchSet', 'team_a_games')
       AND public.fn_crud_column_exists('MatchSet', 'team_b_games') THEN
        DROP TRIGGER IF EXISTS biu_match_set_integrity ON "MatchSet";
        CREATE TRIGGER biu_match_set_integrity
        BEFORE INSERT OR UPDATE ON "MatchSet"
        FOR EACH ROW EXECUTE FUNCTION public.trg_validate_match_set();
    END IF;

    IF public.fn_crud_table_exists('MatchPoint') THEN
        DROP TRIGGER IF EXISTS bi_match_point_score_integrity ON "MatchPoint";
        CREATE TRIGGER bi_match_point_score_integrity
        BEFORE INSERT ON "MatchPoint"
        FOR EACH ROW EXECUTE FUNCTION public.trg_validate_match_point_score();
    END IF;
END;
$$;
"""


REVERSE_SQL = r"""
DO $$
BEGIN
    IF public.fn_crud_table_exists('MatchPoint') THEN
        DROP TRIGGER IF EXISTS bi_match_point_score_integrity ON "MatchPoint";
    END IF;
END;
$$;

DROP PROCEDURE IF EXISTS public.sp_register_match_point(integer, text);
DROP FUNCTION IF EXISTS public.trg_validate_match_point_score();
DROP FUNCTION IF EXISTS public.fn_tennis_point_label(bigint, bigint);
DROP FUNCTION IF EXISTS public.fn_tennis_point_label(integer, integer);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0012_seed_grand_slam_demo_data"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
