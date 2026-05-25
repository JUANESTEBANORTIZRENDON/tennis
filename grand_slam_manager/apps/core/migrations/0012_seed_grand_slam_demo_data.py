"""Resetea datos de prueba deportivos y carga una semilla Grand Slam coherente."""

from django.db import migrations


SQL = r"""
CREATE OR REPLACE FUNCTION public.trg_validate_entry()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_draw_size integer;
    v_used_slots integer;
BEGIN
    SELECT sc."draw_size" INTO v_draw_size
    FROM "SubCategory" sc
    WHERE sc."id" = NEW.subcategory_id;

    SELECT COUNT(*) INTO v_used_slots
    FROM "Entry" e
    WHERE e."subcategory_id" = NEW.subcategory_id
      AND e."id" <> COALESCE(NEW.id, -1);

    IF v_draw_size IS NOT NULL AND v_used_slots >= v_draw_size THEN
        RAISE EXCEPTION 'draw_capacity_exceeded';
    END IF;
    IF NEW.seed IS NOT NULL AND NEW.seed < 1 THEN
        RAISE EXCEPTION 'invalid_seed';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_validate_match_participant()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    side_count integer;
BEGIN
    IF NEW.side IS NULL OR upper(NEW.side) NOT IN ('A', 'B') THEN
        RAISE EXCEPTION 'invalid_match_side';
    END IF;

    SELECT COUNT(*) INTO side_count
    FROM "MatchParticipant" mp
    WHERE mp."match_id" = NEW.match_id
      AND upper(mp."side") = upper(NEW.side)
      AND mp."team_id" <> NEW.team_id;

    IF side_count > 0 THEN
        RAISE EXCEPTION 'match_side_already_assigned';
    END IF;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE PROCEDURE public.sp_seed_grand_slam_demo_data()
LANGUAGE plpgsql
AS $$
DECLARE
    today date := CURRENT_DATE;
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

    INSERT INTO "Tournament" (id, name, year, start_date, end_date, location, surface, description)
    VALUES
        (1, 'Australian Open', 2026, DATE '2026-01-12', DATE '2026-01-25', 'Melbourne Park, Melbourne, Australia', 'Hard', 'Primer Grand Slam de la temporada.'),
        (2, 'Roland-Garros', 2026, DATE '2026-05-24', DATE '2026-06-07', 'Stade Roland-Garros, Paris, France', 'Clay', 'Grand Slam sobre arcilla.'),
        (3, 'The Championships, Wimbledon', 2026, DATE '2026-06-29', DATE '2026-07-12', 'All England Club, London, United Kingdom', 'Grass', 'Grand Slam sobre cesped.'),
        (4, 'US Open', 2026, DATE '2026-08-24', DATE '2026-09-13', 'USTA Billie Jean King National Tennis Center, New York, USA', 'Hard', 'Grand Slam de cierre de temporada.'),
        (5, 'Torneo Prueba Incompleto - Operacion Hoy', EXTRACT(YEAR FROM today)::integer, today - 1, today + 7, 'Centro de Pruebas Victory, Medellin, COL', 'Hard', 'Torneo de prueba con partidos programados para hoy.'),
        (6, 'Torneo Incompleto Validacion - Match Lab', EXTRACT(YEAR FROM today)::integer, today, today + 5, 'Cancha Laboratorio Victory, Medellin, COL', 'Clay', 'Torneo incompleto para validar trazabilidad y desarrollo de partido.');

    INSERT INTO "Court" (id, tournament_id, name, capacity, surface, indoor, location)
    VALUES
        (1, 1, 'Rod Laver Arena', 14820, 'Hard', false, 'Melbourne Park'),
        (2, 2, 'Court Philippe-Chatrier', 15000, 'Clay', false, 'Paris'),
        (3, 3, 'Centre Court', 14979, 'Grass', false, 'London'),
        (4, 4, 'Arthur Ashe Stadium', 23771, 'Hard', false, 'New York'),
        (5, 5, 'Cancha Central Prueba', 5000, 'Hard', false, 'Medellin'),
        (6, 5, 'Cancha 2 Prueba', 1500, 'Hard', false, 'Medellin'),
        (7, 6, 'Cancha Laboratorio 1', 800, 'Clay', false, 'Medellin');

    INSERT INTO "Player" (id, document_type, issuer_country, first_name, last_name, gender, birth_date, country_code, height_cm, weight_kg, hand, turned_pro_year, biography)
    VALUES
        ('P-SRB-001', 'Passport', 'SRB', 'Novak', 'Djokovic', 'M', DATE '1987-05-22', 'SRB', 188, 77, 'R', 2003, 'Campeon multiple de Grand Slam.'),
        ('P-ESP-002', 'Passport', 'ESP', 'Carlos', 'Alcaraz', 'M', DATE '2003-05-05', 'ESP', 183, 74, 'R', 2018, 'Jugador espanol de elite.'),
        ('P-ITA-003', 'Passport', 'ITA', 'Jannik', 'Sinner', 'M', DATE '2001-08-16', 'ITA', 191, 76, 'R', 2018, 'Jugador italiano de alto rendimiento.'),
        ('P-RUS-004', 'Passport', 'RUS', 'Daniil', 'Medvedev', 'M', DATE '1996-02-11', 'RUS', 198, 83, 'R', 2014, 'Especialista en canchas duras.'),
        ('P-POL-005', 'Passport', 'POL', 'Iga', 'Swiatek', 'F', DATE '2001-05-31', 'POL', 176, 65, 'R', 2016, 'Campeona de Grand Slam.'),
        ('P-BLR-006', 'Passport', 'BLR', 'Aryna', 'Sabalenka', 'F', DATE '1998-05-05', 'BLR', 182, 80, 'R', 2015, 'Potencia ofensiva del circuito.'),
        ('P-USA-007', 'Passport', 'USA', 'Coco', 'Gauff', 'F', DATE '2004-03-13', 'USA', 175, 59, 'R', 2018, 'Campeona estadounidense.'),
        ('P-KAZ-008', 'Passport', 'KAZ', 'Elena', 'Rybakina', 'F', DATE '1999-06-17', 'KAZ', 184, 72, 'R', 2016, 'Campeona sobre cesped.'),
        ('P-COL-009', 'CC', 'COL', 'Juan', 'Ortiz', 'M', DATE '1999-04-12', 'COL', 181, 73, 'R', 2019, 'Jugador invitado para pruebas operativas.'),
        ('P-COL-010', 'CC', 'COL', 'Diego', 'Castillo', 'M', DATE '1998-09-20', 'COL', 185, 78, 'R', 2018, 'Jugador invitado para pruebas operativas.'),
        ('P-COL-011', 'CC', 'COL', 'Hugo', 'Moreau', 'M', DATE '2000-01-08', 'COL', 179, 70, 'L', 2020, 'Jugador invitado para pruebas operativas.'),
        ('P-COL-012', 'CC', 'COL', 'Noah', 'Brown', 'M', DATE '2001-11-03', 'COL', 188, 82, 'R', 2021, 'Jugador invitado para pruebas operativas.');

    INSERT INTO "Team" (id, name, notes)
    VALUES
        (1, 'Djokovic', 'Singles'),
        (2, 'Alcaraz', 'Singles'),
        (3, 'Sinner', 'Singles'),
        (4, 'Medvedev', 'Singles'),
        (5, 'Swiatek', 'Singles'),
        (6, 'Sabalenka', 'Singles'),
        (7, 'Gauff', 'Singles'),
        (8, 'Rybakina', 'Singles'),
        (9, 'Juan Ortiz', 'Singles prueba'),
        (10, 'Diego Castillo', 'Singles prueba'),
        (11, 'Hugo Moreau', 'Singles prueba'),
        (12, 'Noah Brown', 'Singles prueba');

    INSERT INTO "TeamMember" (team_id, player_id, role, start_date)
    VALUES
        (1, 'P-SRB-001', 'Player', DATE '2026-01-01'),
        (2, 'P-ESP-002', 'Player', DATE '2026-01-01'),
        (3, 'P-ITA-003', 'Player', DATE '2026-01-01'),
        (4, 'P-RUS-004', 'Player', DATE '2026-01-01'),
        (5, 'P-POL-005', 'Player', DATE '2026-01-01'),
        (6, 'P-BLR-006', 'Player', DATE '2026-01-01'),
        (7, 'P-USA-007', 'Player', DATE '2026-01-01'),
        (8, 'P-KAZ-008', 'Player', DATE '2026-01-01'),
        (9, 'P-COL-009', 'Player', today - 1),
        (10, 'P-COL-010', 'Player', today - 1),
        (11, 'P-COL-011', 'Player', today),
        (12, 'P-COL-012', 'Player', today);

    INSERT INTO "Category" (id, tournament_id, name, gender, mode, description)
    VALUES
        (1, 1, 'Men Singles', 'M', 'Singles', 'Cuadro masculino individual.'),
        (2, 1, 'Women Singles', 'F', 'Singles', 'Cuadro femenino individual.'),
        (3, 2, 'Men Singles', 'M', 'Singles', 'Cuadro masculino individual.'),
        (4, 2, 'Women Singles', 'F', 'Singles', 'Cuadro femenino individual.'),
        (5, 3, 'Men Singles', 'M', 'Singles', 'Cuadro masculino individual.'),
        (6, 4, 'Men Singles', 'M', 'Singles', 'Cuadro masculino individual.'),
        (7, 5, 'Men Singles', 'M', 'Singles', 'Categoria principal de prueba.'),
        (8, 6, 'Men Singles', 'M', 'Singles', 'Categoria incompleta para validacion.');

    INSERT INTO "SubCategory" (id, category_id, name, draw_size, description)
    VALUES
        (1, 1, 'Main Draw Men', 128, 'Cuadro principal masculino Australian Open.'),
        (2, 2, 'Main Draw Women', 128, 'Cuadro principal femenino Australian Open.'),
        (3, 3, 'Main Draw Men', 128, 'Cuadro principal masculino Roland-Garros.'),
        (4, 4, 'Main Draw Women', 128, 'Cuadro principal femenino Roland-Garros.'),
        (5, 5, 'Main Draw Men', 128, 'Cuadro principal masculino Wimbledon.'),
        (6, 6, 'Main Draw Men', 128, 'Cuadro principal masculino US Open.'),
        (7, 7, 'Main Draw Test', 16, 'Cuadro de prueba para partidos del dia.'),
        (8, 8, 'Qualification Test', 8, 'Cuadro incompleto para validar flujos.');

    INSERT INTO "Round" (id, subcategory_id, round_name, round_number, best_of_sets, description)
    VALUES
        (1, 1, 'Round 1', 1, 5, 'Primera ronda.'),
        (2, 3, 'Round 1', 1, 5, 'Primera ronda.'),
        (3, 5, 'Round 1', 1, 5, 'Primera ronda.'),
        (4, 6, 'Round 1', 1, 5, 'Primera ronda.'),
        (5, 7, 'Round 1', 1, 3, 'Primera ronda del torneo de prueba.'),
        (6, 7, 'Quarterfinal', 2, 3, 'Cuartos de final del torneo de prueba.'),
        (7, 8, 'Round 1', 1, 3, 'Primera ronda incompleta.'),
        (8, 8, 'Final', 2, 3, 'Final incompleta de validacion.');

    INSERT INTO "Entry" (id, subcategory_id, team_id, seed, ranking_at_entry, qualifying_method)
    VALUES
        (1, 1, 1, 1, 1, 'Direct'),
        (2, 1, 2, 2, 2, 'Direct'),
        (3, 3, 3, 1, 1, 'Direct'),
        (4, 3, 4, 2, 4, 'Direct'),
        (5, 4, 5, 1, 1, 'Direct'),
        (6, 4, 6, 2, 2, 'Direct'),
        (7, 7, 9, 1, 12, 'Wildcard'),
        (8, 7, 10, 2, 18, 'Wildcard'),
        (9, 7, 11, 3, 24, 'Qualifier'),
        (10, 7, 12, 4, 27, 'Qualifier'),
        (11, 8, 9, 1, 12, 'Wildcard'),
        (12, 8, 10, 2, 18, 'Qualifier');

    INSERT INTO "Match" (id, round_id, scheduled_datetime, court_id, status, winning_team_id, notes)
    VALUES
        (1, 5, today + TIME '10:00', 5, 'Scheduled', NULL, 'Partido de prueba disponible para iniciar hoy.'),
        (2, 5, today + TIME '12:00', 6, 'Scheduled', NULL, 'Segundo partido de prueba disponible para iniciar hoy.'),
        (3, 6, today + TIME '15:00', 5, 'InProgress', NULL, 'Partido ya iniciado para validar marcador en vivo.'),
        (4, 7, today + TIME '16:30', 7, 'Scheduled', NULL, 'Partido incompleto de validacion para hoy.'),
        (5, 2, DATE '2026-05-25' + TIME '11:00', 2, 'Scheduled', NULL, 'Partido de Roland-Garros programado.'),
        (6, 3, DATE '2026-06-29' + TIME '13:00', 3, 'Scheduled', NULL, 'Partido de Wimbledon programado.');

    INSERT INTO "MatchParticipant" (match_id, team_id, side, sets_won, games_won, points_won, is_winner)
    VALUES
        (1, 9, 'A', 0, 0, 0, false),
        (1, 10, 'B', 0, 0, 0, false),
        (2, 11, 'A', 0, 0, 0, false),
        (2, 12, 'B', 0, 0, 0, false),
        (3, 9, 'A', 1, 6, 0, false),
        (3, 11, 'B', 0, 4, 0, false),
        (4, 9, 'A', 0, 0, 0, false),
        (4, 10, 'B', 0, 0, 0, false),
        (5, 3, 'A', 0, 0, 0, false),
        (5, 4, 'B', 0, 0, 0, false),
        (6, 1, 'A', 0, 0, 0, false),
        (6, 2, 'B', 0, 0, 0, false);

    INSERT INTO "MatchSet" (id, match_id, set_number, team_a_games, team_b_games, tie_break_a, tie_break_b, winner_team_id)
    VALUES
        (1, 3, 1, 6, 4, NULL, NULL, 9);

    INSERT INTO "Session" (id, tournament_id, name, start_datetime, end_datetime, status, notes)
    VALUES
        (1, 5, 'Jornada de prueba - manana', today + TIME '09:00', today + TIME '13:30', 'scheduled', 'Bloque para validar inicio de partidos.'),
        (2, 5, 'Jornada de prueba - tarde', today + TIME '14:00', today + TIME '18:00', 'scheduled', 'Bloque para validar partido en progreso.'),
        (3, 6, 'Jornada incompleta', today + TIME '16:00', today + TIME '19:00', 'scheduled', 'Bloque de validacion incompleto.');

    INSERT INTO "SessionMatch" (session_id, match_id, order_in_session)
    VALUES
        (1, 1, 1),
        (1, 2, 2),
        (2, 3, 1),
        (3, 4, 1);

    INSERT INTO "Official" (id, first_name, last_name, nationality, official_type, certification_level, license_number, is_active)
    VALUES
        (1, 'Carlos', 'Bernal', 'COL', 'Chair Umpire', 'Gold Badge', 'OFF-COL-001', true),
        (2, 'Laura', 'Mendez', 'COL', 'Referee', 'Silver Badge', 'OFF-COL-002', true),
        (3, 'Emma', 'Wilson', 'GBR', 'Line Umpire', 'International', 'OFF-GBR-003', true);

    INSERT INTO "MatchOfficial" (match_id, official_id, role, assigned_by_user_id, assigned_at)
    VALUES
        (1, 1, 'Chair Umpire', 2, now()),
        (2, 3, 'Line Umpire', 2, now()),
        (3, 1, 'Chair Umpire', 2, now()),
        (4, 2, 'Referee', 2, now());

    INSERT INTO "InjuryType" (id, name, description)
    VALUES
        (1, 'Ankle Sprain', 'Esguince de tobillo.'),
        (2, 'Back Pain', 'Dolor lumbar.'),
        (3, 'Shoulder Strain', 'Molestia en hombro.');

    INSERT INTO "Injury" (id, injury_type_id, injury_date, recovery_date, description, active)
    VALUES
        (1, 1, today - 2, NULL, 'Molestia reportada durante calentamiento.', true),
        (2, 2, today - 10, today - 1, 'Dolor lumbar recuperado.', false);

    INSERT INTO "PlayerInjury" (player_id, injury_id, assigned_at)
    VALUES
        ('P-COL-010', 1, today - 2),
        ('P-ESP-002', 2, today - 10);

    INSERT INTO "ViolationType" (id, code, name, category, default_sanction_type, description)
    VALUES
        (1, 'TIME-001', 'Time Violation', 'Behaviour', 'Warning', 'Exceso de tiempo entre puntos.'),
        (2, 'CONDUCT-001', 'Unsportsmanlike Conduct', 'Behaviour', 'Point Penalty', 'Conducta antideportiva.'),
        (3, 'COACH-001', 'Illegal Coaching', 'Coaching', 'Warning', 'Instrucciones no permitidas durante el partido.');

    INSERT INTO "Sanction" (id, tournament_id, match_id, violation_type_id, player_id, team_id, official_id, issued_by_user_id, sanction_type, penalty_points, penalty_games, fine_amount, currency, is_active, issued_at, notes)
    VALUES
        (1, 5, 3, 1, 'P-COL-011', NULL, NULL, 2, 'Warning', 0, 0, 0, 'USD', true, now(), 'Advertencia de tiempo durante prueba.'),
        (2, 5, 3, 2, NULL, 9, NULL, 2, 'Point Penalty', 1, 0, 0, 'USD', true, now(), 'Penalizacion de punto para validar disciplina.');

    INSERT INTO "PlayerRanking" (id, player_id, ranking_date, rank_value, ranking_points)
    VALUES
        (1, 'P-SRB-001', today, 3, 6800),
        (2, 'P-ESP-002', today, 2, 8600),
        (3, 'P-ITA-003', today, 1, 9400),
        (4, 'P-POL-005', today, 1, 9200),
        (5, 'P-COL-009', today, 12, 1200),
        (6, 'P-COL-010', today, 18, 900);

    PERFORM setval(pg_get_serial_sequence('"Tournament"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Tournament"), true);
    PERFORM setval(pg_get_serial_sequence('"Court"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Court"), true);
    PERFORM setval(pg_get_serial_sequence('"Category"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Category"), true);
    PERFORM setval(pg_get_serial_sequence('"SubCategory"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "SubCategory"), true);
    PERFORM setval(pg_get_serial_sequence('"Round"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Round"), true);
    PERFORM setval(pg_get_serial_sequence('"Team"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Team"), true);
    PERFORM setval(pg_get_serial_sequence('"Entry"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Entry"), true);
    PERFORM setval(pg_get_serial_sequence('"Match"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Match"), true);
    PERFORM setval(pg_get_serial_sequence('"MatchSet"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "MatchSet"), true);
    PERFORM setval(pg_get_serial_sequence('"Session"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Session"), true);
    PERFORM setval(pg_get_serial_sequence('"Official"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Official"), true);
    PERFORM setval(pg_get_serial_sequence('"InjuryType"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "InjuryType"), true);
    PERFORM setval(pg_get_serial_sequence('"Injury"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Injury"), true);
    PERFORM setval(pg_get_serial_sequence('"ViolationType"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "ViolationType"), true);
    PERFORM setval(pg_get_serial_sequence('"Sanction"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "Sanction"), true);
    PERFORM setval(pg_get_serial_sequence('"PlayerRanking"', 'id'), (SELECT COALESCE(MAX(id), 1) FROM "PlayerRanking"), true);
END;
$$;

CALL public.sp_seed_grand_slam_demo_data();
"""


REVERSE_SQL = "DROP PROCEDURE IF EXISTS public.sp_seed_grand_slam_demo_data();"


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0011_match_operations"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
