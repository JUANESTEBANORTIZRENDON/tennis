from django.db import migrations


SQL = r"""
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
$$;
"""


REVERSE_SQL = migrations.RunSQL.noop


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0014_match_point_label_bigint"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
