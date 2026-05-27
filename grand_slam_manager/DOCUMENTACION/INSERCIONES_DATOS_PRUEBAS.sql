-- ============================================================================
-- INSERCIONES DE DATOS DE PRUEBA - GRAND SLAM MANAGER
-- Generado: 2026-05-27
-- Base de datos: PostgreSQL (Neon)
-- Instrucciones: Copiar y pegar todo este contenido en pgAdmin
-- ============================================================================

-- Desactivar restricciones temporalmente si es necesario
-- SET session_replication_role = 'replica';

-- ============================================================================
-- 1. USUARIOS Y ROLES
-- ============================================================================

-- Insertar roles
INSERT INTO public."Role" (name, description) VALUES
('Administrator', 'Administrador del sistema con acceso total'),
('Tournament Director', 'Director del torneo con permisos de gestión'),
('Match Official', 'Árbitro con permisos para dirigir partidos'),
('Desk Official', 'Árbitro de escritorio'),
('Umpire', 'Árbitro de cancha'),
('User', 'Usuario estándar con permisos limitados')
ON CONFLICT DO NOTHING;

-- Insertar usuarios (contraseñas hasheadas con bcrypt)
INSERT INTO public."UserAccount" (email, password_hash, full_name, phone, is_active) VALUES
('admin@example.com', '$2b$12$8xR8P5q6.XoQ3p9L8mK7J.u5K9Z3x2Y1w0V7U6T5S4R3Q2P1O0N9M8L7', 'Admin User', '+1-555-0001', true),
('director@example.com', '$2b$12$9xR8P5q6.XoQ3p9L8mK7J.u5K9Z3x2Y1w0V7U6T5S4R3Q2P1O0N9M8L7', 'Director Tournament', '+1-555-0002', true),
('official1@example.com', '$2b$12$0xR8P5q6.XoQ3p9L8mK7J.u5K9Z3x2Y1w0V7U6T5S4R3Q2P1O0N9M8L7', 'John Martinez', '+1-555-0003', true),
('official2@example.com', '$2b$12$1xR8P5q6.XoQ3p9L8mK7J.u5K9Z3x2Y1w0V7U6T5S4R3Q2P1O0N9M8L7', 'Maria Gonzalez', '+1-555-0004', true)
ON CONFLICT DO NOTHING;

-- Asignar roles a usuarios
INSERT INTO public."UserRole" (user_id, role_id) VALUES
((SELECT id FROM public."UserAccount" WHERE email='admin@example.com'), (SELECT id FROM public."Role" WHERE name='Administrator')),
((SELECT id FROM public."UserAccount" WHERE email='director@example.com'), (SELECT id FROM public."Role" WHERE name='Tournament Director')),
((SELECT id FROM public."UserAccount" WHERE email='official1@example.com'), (SELECT id FROM public."Role" WHERE name='Match Official')),
((SELECT id FROM public."UserAccount" WHERE email='official2@example.com'), (SELECT id FROM public."Role" WHERE name='Umpire'))
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 2. PERMISOS
-- ============================================================================

INSERT INTO public."Permission" (code, description) VALUES
('view_tournament', 'Ver torneos'),
('edit_tournament', 'Editar torneos'),
('delete_tournament', 'Eliminar torneos'),
('view_player', 'Ver jugadores'),
('edit_player', 'Editar jugadores'),
('view_match', 'Ver partidos'),
('edit_match', 'Editar partidos'),
('manage_officials', 'Gestionar árbitros'),
('manage_sanctions', 'Gestionar sanciones'),
('view_audit', 'Ver registro de auditoría'),
('manage_users', 'Gestionar usuarios')
ON CONFLICT DO NOTHING;

-- Asignar permisos a roles
INSERT INTO public."RolePermission" (role_id, permission_id)
SELECT r.id, p.id FROM public."Role" r, public."Permission" p
WHERE r.name='Administrator'
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 3. TORNEOS
-- ============================================================================

INSERT INTO public."Tournament" (name, year, start_date, end_date, location, surface, description, status) VALUES
('Grand Slam Championship', 2026, '2026-06-01', '2026-06-30', 'New York, USA', 'Hard', 'Torneo principal de tenis', 'En progreso'),
('International Open', 2026, '2026-07-15', '2026-07-28', 'London, UK', 'Grass', 'Torneo abierto internacional', 'Pendiente por inscripciones'),
('Summer Series', 2026, '2026-08-01', '2026-08-14', 'Paris, France', 'Clay', 'Serie de verano', 'Pendiente por inscripciones')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 4. CATEGORÍAS Y SUBCATEGORÍAS
-- ============================================================================

-- Obtener ID del torneo principal para usar en las categorías
WITH tournament_main AS (
  SELECT id FROM public."Tournament" WHERE name='Grand Slam Championship'
)
INSERT INTO public."Category" (tournament_id, name, gender, mode, description) VALUES
((SELECT id FROM tournament_main), 'Men Single', 'M', 'Singles', 'Categoría de sencillos masculino'),
((SELECT id FROM tournament_main), 'Women Single', 'F', 'Singles', 'Categoría de sencillos femenino'),
((SELECT id FROM tournament_main), 'Men Double', 'M', 'Doubles', 'Categoría de dobles masculino'),
((SELECT id FROM tournament_main), 'Women Double', 'F', 'Doubles', 'Categoría de dobles femenino'),
((SELECT id FROM tournament_main), 'Mixed Double', 'M', 'Doubles', 'Categoría de dobles mixtos')
ON CONFLICT DO NOTHING;

-- Subcategorías
WITH category_main AS (
  SELECT id FROM public."Category" WHERE name='Men Single' LIMIT 1
)
INSERT INTO public."SubCategory" (category_id, name, draw_size, description) VALUES
((SELECT id FROM category_main), 'Round 1', 128, 'Primera ronda'),
((SELECT id FROM category_main), 'Round 2', 64, 'Segunda ronda'),
((SELECT id FROM category_main), 'Quarterfinals', 16, 'Cuartos de final'),
((SELECT id FROM category_main), 'Semifinals', 4, 'Semifinales'),
((SELECT id FROM category_main), 'Finals', 2, 'Final')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 5. JUGADORES
-- ============================================================================

INSERT INTO public."Player" (id, document_type, issuer_country, first_name, last_name, gender, birth_date, country_code, height_cm, weight_kg, hand, turned_pro_year) VALUES
('DJOK001', 'PASSPORT', 'SRB', 'Novak', 'Djokovic', 'M', '1987-05-22', 'SRB', 188, 80, 'R', 2003),
('MURR001', 'PASSPORT', 'GBR', 'Andy', 'Murray', 'M', '1987-05-15', 'GBR', 190, 84, 'R', 2005),
('FEDE001', 'PASSPORT', 'SUI', 'Roger', 'Federer', 'M', '1981-08-08', 'SUI', 185, 85, 'R', 1998),
('RAFA001', 'PASSPORT', 'ESP', 'Rafael', 'Nadal', 'M', '1986-06-03', 'ESP', 185, 85, 'L', 2001),
('SWIA001', 'PASSPORT', 'POL', 'Iga', 'Swiatek', 'F', '2004-05-31', 'POL', 172, 61, 'R', 2022),
('KREJ001', 'PASSPORT', 'CZE', 'Barbora', 'Krejcikova', 'F', '1995-12-18', 'CZE', 176, 66, 'R', 2014),
('GARB001', 'PASSPORT', 'USA', 'Sloane', 'Stephens', 'F', '1993-03-20', 'UZB', 183, 72, 'R', 2012),
('HALE001', 'PASSPORT', 'CAN', 'Eugenie', 'Bouchard', 'F', '1994-02-25', 'CAN', 183, 73, 'R', 2012)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 6. EQUIPOS Y MIEMBROS DE EQUIPO
-- ============================================================================

-- Equipos para singles (cada jugador es su propio equipo)
INSERT INTO public."Team" (name, notes) VALUES
('Djokovic Team', 'Equipo de Novak Djokovic'),
('Murray Team', 'Equipo de Andy Murray'),
('Federer Team', 'Equipo de Roger Federer'),
('Nadal Team', 'Equipo de Rafael Nadal'),
('Swiatek Team', 'Equipo de Iga Swiatek'),
('Krejcikova Team', 'Equipo de Barbora Krejcikova'),
('Stephens Team', 'Equipo de Sloane Stephens'),
('Bouchard Team', 'Equipo de Eugenie Bouchard')
ON CONFLICT DO NOTHING;

-- Miembros del equipo
INSERT INTO public."TeamMember" (team_id, player_id, role, start_date, end_date) VALUES
((SELECT id FROM public."Team" WHERE name='Djokovic Team'), 'DJOK001', 'Player', '2026-01-01', NULL),
((SELECT id FROM public."Team" WHERE name='Murray Team'), 'MURR001', 'Player', '2026-01-01', NULL),
((SELECT id FROM public."Team" WHERE name='Federer Team'), 'FEDE001', 'Player', '2026-01-01', NULL),
((SELECT id FROM public."Team" WHERE name='Nadal Team'), 'RAFA001', 'Player', '2026-01-01', NULL),
((SELECT id FROM public."Team" WHERE name='Swiatek Team'), 'SWIA001', 'Player', '2026-01-01', NULL),
((SELECT id FROM public."Team" WHERE name='Krejcikova Team'), 'KREJ001', 'Player', '2026-01-01', NULL),
((SELECT id FROM public."Team" WHERE name='Stephens Team'), 'GARB001', 'Player', '2026-01-01', NULL),
((SELECT id FROM public."Team" WHERE name='Bouchard Team'), 'HALE001', 'Player', '2026-01-01', NULL)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 7. ENTRENADORES
-- ============================================================================

INSERT INTO public."Coach" (first_name, last_name, nationality, birth_date, license_number) VALUES
('Marian', 'Vajda', 'SVK', '1968-02-17', 'COA001'),
('Ivan', 'Lendl', 'USA', '1960-03-28', 'COA002'),
('Severin', 'Luthi', 'SUI', '1969-10-04', 'COA003'),
('Carlos', 'Martinez', 'ESP', '1970-06-15', 'COA004'),
('Iga', 'Coach', 'POL', '1980-05-20', 'COA005'),
('Darina', 'Sabatova', 'CZE', '1985-08-10', 'COA006')
ON CONFLICT DO NOTHING;

-- Asignar entrenadores a jugadores
INSERT INTO public."PlayerCoach" (player_id, coach_id, start_date, end_date) VALUES
('DJOK001', (SELECT id FROM public."Coach" WHERE license_number='COA001'), '2020-01-01', NULL),
('MURR001', (SELECT id FROM public."Coach" WHERE license_number='COA002'), '2019-01-01', NULL),
('FEDE001', (SELECT id FROM public."Coach" WHERE license_number='COA003'), '2021-01-01', NULL),
('RAFA001', (SELECT id FROM public."Coach" WHERE license_number='COA004'), '2018-01-01', NULL),
('SWIA001', (SELECT id FROM public."Coach" WHERE license_number='COA005'), '2022-01-01', NULL),
('KREJ001', (SELECT id FROM public."Coach" WHERE license_number='COA006'), '2023-01-01', NULL)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 8. RANKING DE JUGADORES
-- ============================================================================

INSERT INTO public."PlayerRanking" (player_id, ranking_date, rank_value, ranking_points) VALUES
('DJOK001', '2026-05-27', 1, 10850),
('RAFA001', '2026-05-27', 2, 9850),
('FEDE001', '2026-05-27', 3, 8750),
('MURR001', '2026-05-27', 4, 7650),
('SWIA001', '2026-05-27', 1, 9200),
('KREJ001', '2026-05-27', 2, 8100),
('GARB001', '2026-05-27', 3, 7000),
('HALE001', '2026-05-27', 4, 5900)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 9. ÁRBITROS
-- ============================================================================

INSERT INTO public."Official" (first_name, last_name, nationality, official_type, certification_level, license_number, is_active) VALUES
('John', 'Smith', 'USA', 'Chair Umpire', 'Professional', 'OFF001', true),
('Maria', 'Garcia', 'ESP', 'Line Umpire', 'Professional', 'OFF002', true),
('Pierre', 'Dubois', 'FRA', 'Chair Umpire', 'Professional', 'OFF003', true),
('Anna', 'Mueller', 'GER', 'Net Umpire', 'Professional', 'OFF004', true),
('Elena', 'Rossi', 'ITA', 'Line Umpire', 'Professional', 'OFF005', true),
('David', 'Chen', 'CHN', 'Chair Umpire', 'International', 'OFF006', true)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 10. CANCHAS
-- ============================================================================

WITH tournament_main AS (
  SELECT id FROM public."Tournament" WHERE name='Grand Slam Championship'
)
INSERT INTO public."Court" (tournament_id, name, capacity, surface, indoor, location) VALUES
((SELECT id FROM tournament_main), 'Court 1 - Main', 8000, 'Hard', false, 'Stadium Area'),
((SELECT id FROM tournament_main), 'Court 2 - Second', 5000, 'Hard', false, 'Stadium Area'),
((SELECT id FROM tournament_main), 'Court 3 - Show', 3000, 'Hard', true, 'Indoor Hall'),
((SELECT id FROM tournament_main), 'Court 4 - Practice', 500, 'Hard', false, 'Practice Area'),
((SELECT id FROM tournament_main), 'Court 5 - Training', 300, 'Hard', false, 'Practice Area'),
((SELECT id FROM tournament_main), 'Court 6 - Auxiliary', 1500, 'Hard', false, 'Side Area')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 11. RONDAS
-- ============================================================================

WITH subcategory_main AS (
  SELECT id FROM public."SubCategory" 
  WHERE name='Round 1' AND category_id=(SELECT id FROM public."Category" WHERE name='Men Single' LIMIT 1)
)
INSERT INTO public."Round" (subcategory_id, round_name, round_number, best_of_sets, description) VALUES
((SELECT id FROM subcategory_main), 'First Round', 1, 3, 'Primera ronda del torneo')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 12. ENTRADAS (Entries)
-- ============================================================================

WITH subcategory_main AS (
  SELECT id FROM public."SubCategory" 
  WHERE name='Round 1' AND category_id=(SELECT id FROM public."Category" WHERE name='Men Single' LIMIT 1)
)
INSERT INTO public."Entry" (subcategory_id, team_id, seed, ranking_at_entry, qualifying_method) VALUES
((SELECT id FROM subcategory_main), (SELECT id FROM public."Team" WHERE name='Djokovic Team'), 1, 1, 'Direct'),
((SELECT id FROM subcategory_main), (SELECT id FROM public."Team" WHERE name='Murray Team'), 2, 4, 'Direct'),
((SELECT id FROM subcategory_main), (SELECT id FROM public."Team" WHERE name='Federer Team'), 3, 3, 'Direct'),
((SELECT id FROM subcategory_main), (SELECT id FROM public."Team" WHERE name='Nadal Team'), 4, 2, 'Direct')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 13. TIPOS DE LESIONES
-- ============================================================================

INSERT INTO public."InjuryType" (name, description) VALUES
('Muscle Strain', 'Desgarro muscular'),
('Ankle Sprain', 'Esguince de tobillo'),
('Knee Injury', 'Lesión de rodilla'),
('Shoulder Pain', 'Dolor de hombro'),
('Back Pain', 'Dolor de espalda'),
('Elbow Injury', 'Lesión de codo'),
('Wrist Injury', 'Lesión de muñeca'),
('Heat Exhaustion', 'Agotamiento por calor')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 14. LESIONES
-- ============================================================================

INSERT INTO public."Injury" (injury_type_id, injury_date, recovery_date, description, active) VALUES
((SELECT id FROM public."InjuryType" WHERE name='Muscle Strain'), '2026-05-15', '2026-05-22', 'Desgarro en cuádriceps', false),
((SELECT id FROM public."InjuryType" WHERE name='Ankle Sprain'), '2026-05-20', NULL, 'Esguince leve de tobillo', true),
((SELECT id FROM public."InjuryType" WHERE name='Shoulder Pain'), '2026-05-25', NULL, 'Dolor de hombro derecho', true)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 15. TIPOS DE VIOLACIONES
-- ============================================================================

INSERT INTO public."ViolationType" (code, name, category, default_sanction_type, description) VALUES
('ABU01', 'Verbal Abuse', 'Conduct', 'Code Violation Point', 'Abuso verbal hacia árbitro u oponente'),
('ABU02', 'Physical Abuse', 'Conduct', 'Code Violation Game', 'Agresión física'),
('ABU03', 'Ball Abuse', 'Equipment', 'Code Violation Point', 'Abuso de la pelota'),
('ABU04', 'Racket Abuse', 'Equipment', 'Code Violation Game', 'Abuso de la raqueta'),
('TIM01', 'Code Violation - Time', 'Timing', 'Code Violation Point', 'Exceso de tiempo'),
('UNS01', 'Unsportsmanlike Conduct', 'Conduct', 'Code Violation Point', 'Conducta antideportiva'),
('DOP01', 'Doping Violation', 'Health', 'Disqualification', 'Violación de antidoping')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 16. PARTIDOS (Matches)
-- ============================================================================

WITH round_main AS (
  SELECT id FROM public."Round" 
  WHERE round_number=1 AND subcategory_id=(
    SELECT id FROM public."SubCategory" 
    WHERE name='Round 1' AND category_id=(SELECT id FROM public."Category" WHERE name='Men Single' LIMIT 1)
  )
),
court_main AS (
  SELECT id FROM public."Court" WHERE name='Court 1 - Main' LIMIT 1
)
INSERT INTO public."Match" (round_id, scheduled_datetime, court_id, status, winning_team_id, notes) VALUES
((SELECT id FROM round_main), '2026-06-05 10:00:00', (SELECT id FROM court_main), 'Scheduled', NULL, 'Match 1 - First Round'),
((SELECT id FROM round_main), '2026-06-05 14:00:00', (SELECT id FROM court_main), 'Scheduled', NULL, 'Match 2 - First Round'),
((SELECT id FROM round_main), '2026-06-06 10:00:00', (SELECT id FROM court_main), 'Scheduled', NULL, 'Match 3 - First Round')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 17. PARTICIPANTES DEL PARTIDO (MatchParticipant)
-- ============================================================================

WITH match_1 AS (
  SELECT id FROM public."Match" WHERE notes='Match 1 - First Round' LIMIT 1
)
INSERT INTO public."MatchParticipant" (match_id, team_id, side, sets_won, games_won, points_won, is_winner) VALUES
((SELECT id FROM match_1), (SELECT id FROM public."Team" WHERE name='Djokovic Team'), 'A', 0, 0, 0, false),
((SELECT id FROM match_1), (SELECT id FROM public."Team" WHERE name='Murray Team'), 'B', 0, 0, 0, false)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 18. SCHEDULE DE PARTIDOS (MatchSchedule)
-- ============================================================================

WITH match_1 AS (
  SELECT id FROM public."Match" WHERE notes='Match 1 - First Round' LIMIT 1
),
court_main AS (
  SELECT id FROM public."Court" WHERE name='Court 1 - Main' LIMIT 1
),
user_director AS (
  SELECT id FROM public."UserAccount" WHERE email='director@example.com'
)
INSERT INTO public."MatchSchedule" (match_id, planned_datetime, court_id, schedule_status, created_by_user_id) VALUES
((SELECT id FROM match_1), '2026-06-05 10:00:00', (SELECT id FROM court_main), 'Scheduled', (SELECT id FROM user_director))
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 19. ÁRBITROS DEL PARTIDO (MatchOfficial)
-- ============================================================================

WITH match_1 AS (
  SELECT id FROM public."Match" WHERE notes='Match 1 - First Round' LIMIT 1
),
official_chair AS (
  SELECT id FROM public."Official" WHERE first_name='John' AND last_name='Smith'
),
official_line AS (
  SELECT id FROM public."Official" WHERE first_name='Maria' AND last_name='Garcia'
),
user_director AS (
  SELECT id FROM public."UserAccount" WHERE email='director@example.com'
)
INSERT INTO public."MatchOfficial" (match_id, official_id, role, assigned_by_user_id) VALUES
((SELECT id FROM match_1), (SELECT id FROM official_chair), 'Chair Umpire', (SELECT id FROM user_director)),
((SELECT id FROM match_1), (SELECT id FROM official_line), 'Line Umpire', (SELECT id FROM user_director))
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 20. SANCIONES (Sanctions)
-- ============================================================================

WITH tournament_main AS (
  SELECT id FROM public."Tournament" WHERE name='Grand Slam Championship'
),
violation_code AS (
  SELECT id FROM public."ViolationType" WHERE code='UNS01'
),
user_official AS (
  SELECT id FROM public."UserAccount" WHERE email='official1@example.com'
)
INSERT INTO public."Sanction" (tournament_id, violation_type_id, player_id, sanction_type, penalty_points, issued_by_user_id, is_active, notes) VALUES
((SELECT id FROM tournament_main), (SELECT id FROM violation_code), 'DJOK001', 'Code Violation Point', 1, (SELECT id FROM user_official), true, 'Conducta antideportiva en primer set'),
((SELECT id FROM tournament_main), (SELECT id FROM violation_code), 'MURR001', 'Code Violation Game', 2, (SELECT id FROM user_official), true, 'Abuso verbal hacia el árbitro')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 21. REGLAS DE PREMIOS (PrizeRule)
-- ============================================================================

WITH subcategory_main AS (
  SELECT id FROM public."SubCategory" 
  WHERE name='Round 1' AND category_id=(SELECT id FROM public."Category" WHERE name='Men Single' LIMIT 1)
),
round_main AS (
  SELECT id FROM public."Round" 
  WHERE round_number=1 AND subcategory_id=subcategory_main.id
)
INSERT INTO public."PrizeRule" (subcategory_id, round_id, amount, currency)
SELECT sc.id, r.id, 10000, 'USD'
FROM public."SubCategory" sc, public."Round" r
WHERE sc.name='Round 1' AND r.round_number=1 AND r.subcategory_id=sc.id
LIMIT 1
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 22. REGLAS DE PUNTOS DE RANKING (RankingPointsRule)
-- ============================================================================

WITH subcategory_main AS (
  SELECT id FROM public."SubCategory" 
  WHERE name='Round 1' AND category_id=(SELECT id FROM public."Category" WHERE name='Men Single' LIMIT 1)
),
round_main AS (
  SELECT id FROM public."Round" 
  WHERE round_number=1 AND subcategory_id=subcategory_main.id
)
INSERT INTO public."RankingPointsRule" (subcategory_id, round_id, points)
SELECT sc.id, r.id, 10
FROM public."SubCategory" sc, public."Round" r
WHERE sc.name='Round 1' AND r.round_number=1 AND r.subcategory_id=sc.id
LIMIT 1
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 23. TABLA DE POSICIONES (Standing)
-- ============================================================================

WITH subcategory_main AS (
  SELECT id FROM public."SubCategory" 
  WHERE name='Round 1' AND category_id=(SELECT id FROM public."Category" WHERE name='Men Single' LIMIT 1)
)
INSERT INTO public."Standing" (subcategory_id, team_id, played, won, lost, games_for, games_against, points) VALUES
((SELECT id FROM subcategory_main), (SELECT id FROM public."Team" WHERE name='Djokovic Team'), 0, 0, 0, 0, 0, 0),
((SELECT id FROM subcategory_main), (SELECT id FROM public."Team" WHERE name='Murray Team'), 0, 0, 0, 0, 0, 0),
((SELECT id FROM subcategory_main), (SELECT id FROM public."Team" WHERE name='Federer Team'), 0, 0, 0, 0, 0, 0),
((SELECT id FROM subcategory_main), (SELECT id FROM public."Team" WHERE name='Nadal Team'), 0, 0, 0, 0, 0, 0)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 24. EVENTOS
-- ============================================================================

WITH tournament_main AS (
  SELECT id FROM public."Tournament" WHERE name='Grand Slam Championship'
),
subcategory_main AS (
  SELECT id FROM public."SubCategory" 
  WHERE name='Round 1' AND category_id=(SELECT id FROM public."Category" WHERE name='Men Single' LIMIT 1)
)
INSERT INTO public."Event" (tournament_id, subcategory_id, event_type, event_datetime, location, description) VALUES
((SELECT id FROM tournament_main), (SELECT id FROM subcategory_main), 'Round Start', '2026-06-05 09:00:00', 'Main Stadium', 'Inicio de la primera ronda'),
((SELECT id FROM tournament_main), (SELECT id FROM subcategory_main), 'Round End', '2026-06-06 18:00:00', 'Main Stadium', 'Fin de la primera ronda')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 25. SESIONES (Sessions)
-- ============================================================================

WITH tournament_main AS (
  SELECT id FROM public."Tournament" WHERE name='Grand Slam Championship'
)
INSERT INTO public."Session" (tournament_id, name, start_datetime, end_datetime, status, notes) VALUES
((SELECT id FROM tournament_main), 'Morning Session Day 1', '2026-06-05 09:00:00', '2026-06-05 13:00:00', 'Scheduled', 'Sesión matutina del día 1'),
((SELECT id FROM tournament_main), 'Afternoon Session Day 1', '2026-06-05 14:00:00', '2026-06-05 18:00:00', 'Scheduled', 'Sesión vespertina del día 1'),
((SELECT id FROM tournament_main), 'Night Session Day 1', '2026-06-05 19:00:00', '2026-06-05 23:00:00', 'Scheduled', 'Sesión nocturna del día 1')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 26. PARTIDOS EN SESIONES (SessionMatch)
-- ============================================================================

WITH session_morning AS (
  SELECT id FROM public."Session" WHERE name='Morning Session Day 1' LIMIT 1
),
match_1 AS (
  SELECT id FROM public."Match" WHERE notes='Match 1 - First Round' LIMIT 1
),
match_2 AS (
  SELECT id FROM public."Match" WHERE notes='Match 2 - First Round' LIMIT 1
)
INSERT INTO public."SessionMatch" (session_id, match_id, order_in_session) VALUES
((SELECT id FROM session_morning), (SELECT id FROM match_1), 1),
((SELECT id FROM session_morning), (SELECT id FROM match_2), 2)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- REACTIVAR RESTRICCIONES (si fue necesario desactivarlas)
-- ============================================================================

-- SET session_replication_role = 'default';

-- ============================================================================
-- VERIFICACIÓN - Ejecutar estas consultas para verificar los datos
-- ============================================================================

-- SELECT COUNT(*) as "Total Usuarios" FROM public."UserAccount";
-- SELECT COUNT(*) as "Total Jugadores" FROM public."Player";
-- SELECT COUNT(*) as "Total Torneos" FROM public."Tournament";
-- SELECT COUNT(*) as "Total Árbitros" FROM public."Official";
-- SELECT COUNT(*) as "Total Partidos" FROM public."Match";
-- SELECT COUNT(*) as "Total Sanciones" FROM public."Sanction";

-- ============================================================================
-- FIN DE LAS INSERCIONES
-- ============================================================================
