from django.db import migrations


SQL = r"""
CREATE OR REPLACE PROCEDURE public.sp_seed_incomplete_bracket_demo()
LANGUAGE plpgsql
AS $$
DECLARE
    v_tournament_id integer;
    v_category_id integer;
    v_subcategory_id integer;
    v_court_id integer;
    v_team_id integer;
    player_ids text[] := ARRAY[
        'P-DEMO-101',
        'P-DEMO-102',
        'P-DEMO-103',
        'P-DEMO-104',
        'P-DEMO-105',
        'P-DEMO-106',
        'P-DEMO-107',
        'P-DEMO-108'
    ];
    first_names text[] := ARRAY['Mateo','Lucas','Nicolas','Samuel','Tomas','Emiliano','Sebastian','Martin'];
    last_names text[] := ARRAY['Rivera','Morales','Cortes','Vargas','Herrera','Rojas','Navarro','Salazar'];
    i integer;
BEGIN
    SELECT id INTO v_tournament_id
    FROM "Tournament"
    WHERE name = 'Grand Slam Demo Pendiente - Inscripciones'
      AND year = EXTRACT(YEAR FROM CURRENT_DATE)::integer;

    IF v_tournament_id IS NULL THEN
        INSERT INTO "Tournament" (name, year, start_date, end_date, location, surface, description, status)
        VALUES (
            'Grand Slam Demo Pendiente - Inscripciones',
            EXTRACT(YEAR FROM CURRENT_DATE)::integer,
            CURRENT_DATE + 10,
            CURRENT_DATE + 23,
            'Victory Tennis Park, Medellin, COL',
            'Hard'::surface_type,
            'Torneo demo con cuadro de 8 y cupos pendientes para probar inscripciones.',
            'Pendiente por inscripciones'
        )
        RETURNING id INTO v_tournament_id;
    END IF;

    SELECT id INTO v_court_id
    FROM "Court"
    WHERE tournament_id = v_tournament_id
      AND name = 'Victory Central Court'
    LIMIT 1;

    IF v_court_id IS NULL THEN
        INSERT INTO "Court" (tournament_id, name, capacity, surface, indoor, location)
        VALUES (v_tournament_id, 'Victory Central Court', 6500, 'Hard'::surface_type, false, 'Medellin')
        RETURNING id INTO v_court_id;
    END IF;

    SELECT id INTO v_category_id
    FROM "Category"
    WHERE tournament_id = v_tournament_id
      AND name = 'Men Singles'
    LIMIT 1;

    IF v_category_id IS NULL THEN
        INSERT INTO "Category" (tournament_id, name, gender, mode, description)
        VALUES (v_tournament_id, 'Men Singles', 'M'::gender_type, 'Singles'::mode_type, 'Categoria masculina demo.')
        RETURNING id INTO v_category_id;
    END IF;

    SELECT id INTO v_subcategory_id
    FROM "SubCategory"
    WHERE category_id = v_category_id
      AND name = 'Main Draw Demo 8'
    LIMIT 1;

    IF v_subcategory_id IS NULL THEN
        INSERT INTO "SubCategory" (category_id, name, draw_size, description)
        VALUES (v_category_id, 'Main Draw Demo 8', 8, 'Cuadro de 8: seis inscritos y dos cupos pendientes.')
        RETURNING id INTO v_subcategory_id;
    END IF;

    FOR i IN 1..array_length(player_ids, 1) LOOP
        INSERT INTO "Player" (
            id, document_type, issuer_country, first_name, last_name, gender, birth_date,
            country_code, height_cm, weight_kg, hand, turned_pro_year, biography
        )
        VALUES (
            player_ids[i], 'Passport', 'COL', first_names[i], last_names[i], 'M'::gender_type,
            DATE '1998-01-01' + (i * 410),
            'COL', 178 + i, 70 + i, (CASE WHEN i % 3 = 0 THEN 'L' ELSE 'R' END)::hand_type,
            2018 + (i % 4), 'Jugador demo para completar inscripciones.'
        )
        ON CONFLICT (id) DO NOTHING;

        SELECT tm.team_id INTO v_team_id
        FROM "TeamMember" tm
        WHERE tm.player_id = player_ids[i]
        LIMIT 1;

        IF v_team_id IS NULL THEN
            INSERT INTO "Team" (name, notes)
            VALUES (first_names[i] || ' ' || last_names[i], 'Equipo singles demo')
            RETURNING id INTO v_team_id;

            INSERT INTO "TeamMember" (team_id, player_id, role, start_date)
            VALUES (v_team_id, player_ids[i], 'Player', CURRENT_DATE);
        END IF;

        IF i <= 6 THEN
            INSERT INTO "Entry" (subcategory_id, team_id, seed, ranking_at_entry, qualifying_method)
            SELECT v_subcategory_id, v_team_id, i, 80 + i, 'Direct'
            WHERE NOT EXISTS (
                SELECT 1 FROM "Entry"
                WHERE subcategory_id = v_subcategory_id
                  AND team_id = v_team_id
            );
        END IF;
    END LOOP;
END;
$$;

CALL public.sp_seed_incomplete_bracket_demo();
"""


REVERSE_SQL = "DROP PROCEDURE IF EXISTS public.sp_seed_incomplete_bracket_demo();"


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0019_tournament_brackets_and_status"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
