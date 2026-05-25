from django.db import migrations


SQL = r"""
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
$$;
"""


REVERSE_SQL = migrations.RunSQL.noop


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0016_match_detail_next_game"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
