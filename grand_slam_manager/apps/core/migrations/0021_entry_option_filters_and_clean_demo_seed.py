from django.db import migrations


SQL = r"""
CREATE OR REPLACE FUNCTION public.sp_available_entry_teams_json(p_subcategory_id integer)
RETURNS TABLE(row_data jsonb)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_mode text;
    v_required_members integer;
BEGIN
    SELECT c.mode::text
    INTO v_mode
    FROM "SubCategory" sc
    JOIN "Category" c ON c.id = sc.category_id
    WHERE sc.id = p_subcategory_id;

    v_required_members := CASE WHEN v_mode = 'Doubles' THEN 2 ELSE 1 END;

    RETURN QUERY
    SELECT to_jsonb(q)
    FROM (
        SELECT
            t.id AS team_id,
            t.name AS equipo,
            COUNT(tm.player_id) AS jugadores,
            v_required_members AS jugadores_requeridos
        FROM "Team" t
        JOIN "TeamMember" tm ON tm.team_id = t.id
        WHERE (
            p_subcategory_id IS NULL
            OR NOT EXISTS (
                SELECT 1
                FROM "Entry" e
                WHERE e.subcategory_id = p_subcategory_id
                  AND e.team_id = t.id
            )
        )
        GROUP BY t.id, t.name
        HAVING p_subcategory_id IS NULL OR COUNT(tm.player_id) = v_required_members
        ORDER BY t.name
    ) q;
END;
$$;

CREATE OR REPLACE FUNCTION public.sp_available_team_member_players_json(p_team_id integer)
RETURNS TABLE(row_data jsonb)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT to_jsonb(q)
    FROM (
        SELECT
            p.id AS player_id,
            TRIM(CONCAT(p.first_name, ' ', p.last_name)) AS jugador,
            p.country_code AS pais
        FROM "Player" p
        WHERE p_team_id IS NULL
           OR NOT EXISTS (
                SELECT 1
                FROM "TeamMember" tm
                WHERE tm.team_id = p_team_id
                  AND tm.player_id = p.id
           )
        ORDER BY p.last_name, p.first_name, p.id
    ) q;
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_seed_competition_demo_only()
LANGUAGE plpgsql
AS $$
DECLARE
    today date := CURRENT_DATE;
    pid text;
    tid integer;
    i integer;
    first_names text[] := ARRAY[
        'Mateo','Lucas','Nicolas','Samuel','Tomas','Emiliano','Sebastian','Martin',
        'Valeria','Camila','Isabella','Luciana','Sofia','Mariana','Renata','Gabriela',
        'Adrian','Daniel','Felipe','Joaquin','Andres','Bruno','Cristian','David'
    ];
    last_names text[] := ARRAY[
        'Rivera','Morales','Cortes','Vargas','Herrera','Rojas','Navarro','Salazar',
        'Torres','Castro','Mendoza','Pineda','Mejia','Arias','Lopez','Ramirez',
        'Ortega','Vega','Molina','Suarez','Peña','Muñoz','Cárdenas','Niño'
    ];
    genders text[] := ARRAY[
        'M','M','M','M','M','M','M','M',
        'F','F','F','F','F','F','F','F',
        'M','M','M','M','M','M','M','M'
    ];
BEGIN
    TRUNCATE
        "AuditLog",
        "SessionMatch",
        "MatchPlayerStat",
        "MatchTeamStat",
        "MatchPoint",
        "MatchGame",
        "MatchSet",
        "MatchOfficial",
        "MatchSchedule",
        "MatchRescheduleLog",
        "MatchParticipant",
        "SanctionAppeal",
        "Sanction",
        "MedicalReport",
        "PlayerInjury",
        "Injury",
        "InjuryType",
        "PlayerRanking",
        "PlayerCoach",
        "Coach",
        "PrizeRule",
        "RankingPointsRule",
        "Standing",
        "Session",
        "Match",
        "Entry",
        "Round",
        "SubCategory",
        "Category",
        "Court",
        "Event",
        "Tournament",
        "TeamMember",
        "Team",
        "Official",
        "ViolationType",
        "Player"
    RESTART IDENTITY CASCADE;

    INSERT INTO "Tournament" (id, name, year, start_date, end_date, location, surface, description, status)
    VALUES
        (8, 'Grand Slam Demo Pendiente - Inscripciones', EXTRACT(YEAR FROM today)::integer, today + 10, today + 23, 'Victory Tennis Park, Medellín, COL', 'Hard', 'Torneo demo con cuadros completos e incompletos para probar inscripciones.', 'Pendiente por inscripciones'),
        (9, 'Victory Grand Slam Completo - Resultados', EXTRACT(YEAR FROM today)::integer, today - 20, today - 7, 'Victory Tennis Park, Medellín, COL', 'Clay', 'Torneo demo completo con resultados y bracket finalizado.', 'Finalizado');

    INSERT INTO "Court" (id, tournament_id, name, capacity, surface, indoor, location)
    VALUES
        (1, 8, 'Victory Central Court', 6500, 'Hard', false, 'Medellín'),
        (2, 8, 'Victory Court 2', 1800, 'Hard', false, 'Medellín'),
        (3, 9, 'Championship Court', 7200, 'Clay', false, 'Medellín');

    FOR i IN 1..array_length(first_names, 1) LOOP
        pid := 'P-DEMO-' || lpad(i::text, 3, '0');
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
            DATE '1996-01-01' + (i * 280),
            'COL',
            174 + (i % 18),
            66 + (i % 22),
            CASE WHEN i % 4 = 0 THEN 'L'::hand_type ELSE 'R'::hand_type END,
            2016 + (i % 7),
            'Jugador demo para pruebas de torneo.'
        );

        INSERT INTO "Team" (id, name, notes)
        VALUES (i, first_names[i] || ' ' || last_names[i], 'Equipo singles demo')
        RETURNING id INTO tid;

        INSERT INTO "TeamMember" (team_id, player_id, role, start_date)
        VALUES (tid, pid, 'Player', today - 30);
    END LOOP;

    INSERT INTO "Category" (id, tournament_id, name, gender, mode, description)
    VALUES
        (10, 8, 'Men Singles', 'M', 'Singles', 'Categoría masculina demo.'),
        (11, 8, 'Women Singles', 'F', 'Singles', 'Categoría femenina demo.'),
        (12, 9, 'Men Singles', 'M', 'Singles', 'Categoría masculina completa.');

    INSERT INTO "SubCategory" (id, category_id, name, draw_size, description)
    VALUES
        (10, 10, 'Main Draw Demo 8', 8, 'Cuadro principal incompleto: faltan dos equipos.'),
        (11, 10, 'Qualifying Demo 4', 4, 'Cuadro clasificatorio completo.'),
        (12, 11, 'Women Main Draw Demo 8', 8, 'Cuadro femenino incompleto: faltan tres equipos.'),
        (13, 11, 'Women Mini Draw 4', 4, 'Cuadro femenino completo.'),
        (20, 12, 'Championship Draw 8', 8, 'Cuadro completo con resultados.');

    INSERT INTO "Entry" (id, subcategory_id, team_id, seed, ranking_at_entry, qualifying_method)
    VALUES
        (1, 10, 1, 1, 11, 'Direct'),
        (2, 10, 2, 2, 14, 'Direct'),
        (3, 10, 3, 3, 18, 'Wildcard'),
        (4, 10, 4, 4, 22, 'Qualifier'),
        (5, 10, 5, 5, 31, 'Direct'),
        (6, 10, 6, 6, 39, 'Qualifier'),
        (7, 11, 7, 1, 48, 'Direct'),
        (8, 11, 8, 2, 52, 'Direct'),
        (9, 11, 17, 3, 67, 'Qualifier'),
        (10, 11, 18, 4, 72, 'Wildcard'),
        (11, 12, 9, 1, 9, 'Direct'),
        (12, 12, 10, 2, 15, 'Direct'),
        (13, 12, 11, 3, 20, 'Wildcard'),
        (14, 12, 12, 4, 26, 'Qualifier'),
        (15, 12, 13, 5, 33, 'Direct'),
        (16, 13, 14, 1, 41, 'Direct'),
        (17, 13, 15, 2, 45, 'Direct'),
        (18, 13, 16, 3, 58, 'Wildcard'),
        (19, 13, 9, 4, 62, 'Qualifier'),
        (20, 20, 19, 1, 4, 'Direct'),
        (21, 20, 20, 2, 8, 'Direct'),
        (22, 20, 21, 3, 12, 'Direct'),
        (23, 20, 22, 4, 16, 'Direct'),
        (24, 20, 23, 5, 21, 'Wildcard'),
        (25, 20, 24, 6, 25, 'Qualifier'),
        (26, 20, 1, 7, 30, 'Direct'),
        (27, 20, 2, 8, 36, 'Qualifier');

    INSERT INTO "Round" (id, subcategory_id, round_name, round_number, best_of_sets, description)
    VALUES
        (20, 20, 'Quarterfinal', 1, 5, 'Cuartos de final.'),
        (21, 20, 'Semifinal', 2, 5, 'Semifinal.'),
        (22, 20, 'Final', 3, 5, 'Final.'),
        (30, 11, 'Semifinal', 1, 5, 'Ronda generada para cuadro completo.'),
        (31, 11, 'Final', 2, 5, 'Final clasificatoria.'),
        (32, 13, 'Semifinal', 1, 3, 'Ronda generada para cuadro completo.'),
        (33, 13, 'Final', 2, 3, 'Final femenina demo.');

    INSERT INTO "Match" (id, round_id, scheduled_datetime, court_id, status, winning_team_id, notes)
    VALUES
        (100, 20, today - 18 + TIME '10:00', 3, 'Completed', 19, 'Quarterfinal completa.'),
        (101, 20, today - 18 + TIME '12:00', 3, 'Completed', 22, 'Quarterfinal completa.'),
        (102, 20, today - 18 + TIME '14:00', 3, 'Completed', 23, 'Quarterfinal completa.'),
        (103, 20, today - 18 + TIME '16:00', 3, 'Completed', 2, 'Quarterfinal completa.'),
        (104, 21, today - 15 + TIME '11:00', 3, 'Completed', 19, 'Semifinal completa.'),
        (105, 21, today - 15 + TIME '15:00', 3, 'Completed', 23, 'Semifinal completa.'),
        (106, 22, today - 12 + TIME '14:00', 3, 'InProgress', 19, 'Final completa.');

    INSERT INTO "MatchParticipant" (match_id, team_id, side, sets_won, games_won, points_won, is_winner)
    VALUES
        (100, 19, 'A', 3, 18, 96, true), (100, 20, 'B', 1, 12, 77, false),
        (101, 21, 'A', 2, 15, 83, false), (101, 22, 'B', 3, 17, 91, true),
        (102, 23, 'A', 3, 18, 98, true), (102, 24, 'B', 0, 9, 61, false),
        (103, 1, 'A', 1, 13, 72, false), (103, 2, 'B', 3, 17, 94, true),
        (104, 19, 'A', 3, 18, 102, true), (104, 22, 'B', 2, 16, 95, false),
        (105, 23, 'A', 3, 18, 99, true), (105, 2, 'B', 1, 13, 76, false),
        (106, 19, 'A', 3, 19, 108, true), (106, 23, 'B', 2, 16, 101, false);

    INSERT INTO "MatchSet" (match_id, set_number, team_a_games, team_b_games, tie_break_a, tie_break_b, winner_team_id)
    VALUES
        (106, 1, 6, 4, NULL, NULL, 19),
        (106, 2, 4, 6, NULL, NULL, 23),
        (106, 3, 7, 6, 7, 4, 19),
        (106, 4, 5, 7, NULL, NULL, 23),
        (106, 5, 6, 3, NULL, NULL, 19);

    UPDATE "Match"
    SET status = 'Completed'
    WHERE id = 106;

    INSERT INTO "InjuryType" (id, name, description)
    VALUES
        (1, 'Ankle Sprain', 'Esguince de tobillo.'),
        (2, 'Shoulder Strain', 'Molestia de hombro.');

    INSERT INTO "ViolationType" (id, code, name, category, default_sanction_type, description)
    VALUES
        (1, 'TIME-001', 'Time Violation', 'Behaviour', 'Warning', 'Exceso de tiempo entre puntos.'),
        (2, 'CONDUCT-001', 'Unsportsmanlike Conduct', 'Behaviour', 'Point Penalty', 'Conducta antideportiva.');

    PERFORM setval(pg_get_serial_sequence('"Tournament"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Tournament"), true);
    PERFORM setval(pg_get_serial_sequence('"Court"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Court"), true);
    PERFORM setval(pg_get_serial_sequence('"Category"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Category"), true);
    PERFORM setval(pg_get_serial_sequence('"SubCategory"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "SubCategory"), true);
    PERFORM setval(pg_get_serial_sequence('"Round"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Round"), true);
    PERFORM setval(pg_get_serial_sequence('"Team"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Team"), true);
    PERFORM setval(pg_get_serial_sequence('"Entry"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Entry"), true);
    PERFORM setval(pg_get_serial_sequence('"Match"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Match"), true);
    PERFORM setval(pg_get_serial_sequence('"MatchSet"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "MatchSet"), true);
    PERFORM setval(pg_get_serial_sequence('"InjuryType"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "InjuryType"), true);
    PERFORM setval(pg_get_serial_sequence('"ViolationType"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "ViolationType"), true);
END;
$$;

CALL public.sp_seed_competition_demo_only();
"""


REVERSE_SQL = "DROP PROCEDURE IF EXISTS public.sp_seed_competition_demo_only();"


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0020_seed_incomplete_bracket_demo"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
