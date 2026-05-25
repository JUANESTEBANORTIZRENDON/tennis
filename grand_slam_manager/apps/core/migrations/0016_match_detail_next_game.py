from django.db import migrations


SQL = r"""
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
"""


REVERSE_SQL = migrations.RunSQL.noop


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0015_match_point_open_set_zero_zero"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
