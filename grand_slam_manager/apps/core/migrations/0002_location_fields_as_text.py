"""Convierte ubicaciones JSONB a texto y actualiza procedimientos relacionados."""

from django.db import migrations


JSONB_TO_TEXT = """
CASE
    WHEN "location" IS NULL THEN NULL
    WHEN jsonb_typeof("location") = 'object' THEN NULLIF(
        concat_ws(
            ', ',
            "location" ->> 'address',
            "location" ->> 'venue',
            "location" ->> 'city',
            "location" ->> 'state',
            "location" ->> 'country'
        ),
        ''
    )
    WHEN jsonb_typeof("location") = 'string' THEN "location" #>> '{}'
    ELSE "location"::text
END
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_baseline_neon_schema"),
    ]

    operations = [
        migrations.RunSQL(
            sql=f"""
            DROP PROCEDURE IF EXISTS public.sp_create_tournament(
                character varying, integer, date, date, jsonb, surface_type, text
            );
            DROP PROCEDURE IF EXISTS public.sp_update_tournament(
                integer, character varying, integer, date, date, jsonb, surface_type, text
            );
            DROP PROCEDURE IF EXISTS public.sp_create_court(
                integer, character varying, integer, surface_type, boolean, jsonb
            );

            ALTER TABLE "Tournament"
            ALTER COLUMN "location" TYPE text
            USING {JSONB_TO_TEXT};

            ALTER TABLE "Court"
            ALTER COLUMN "location" TYPE text
            USING {JSONB_TO_TEXT};

            CREATE OR REPLACE PROCEDURE public.sp_create_tournament(
                IN p_name character varying,
                IN p_year integer,
                IN p_start date,
                IN p_end date,
                IN p_location text,
                IN p_surface surface_type,
                IN p_description text
            )
            LANGUAGE plpgsql
            AS $procedure$
            BEGIN
                INSERT INTO "Tournament" (
                    "name", "year", "start_date", "end_date", "location", "surface", "description"
                )
                VALUES (
                    p_name, p_year, p_start, p_end, p_location, p_surface, p_description
                );
            END;
            $procedure$;

            CREATE OR REPLACE PROCEDURE public.sp_update_tournament(
                IN p_id integer,
                IN p_name character varying,
                IN p_year integer,
                IN p_start date,
                IN p_end date,
                IN p_location text,
                IN p_surface surface_type,
                IN p_description text
            )
            LANGUAGE plpgsql
            AS $procedure$
            BEGIN
                UPDATE "Tournament"
                SET
                    "name" = p_name,
                    "year" = p_year,
                    "start_date" = p_start,
                    "end_date" = p_end,
                    "location" = p_location,
                    "surface" = p_surface,
                    "description" = p_description,
                    "updated_at" = CURRENT_TIMESTAMP
                WHERE "id" = p_id;
            END;
            $procedure$;

            CREATE OR REPLACE PROCEDURE public.sp_create_court(
                IN p_tournament_id integer,
                IN p_name character varying,
                IN p_capacity integer,
                IN p_surface surface_type,
                IN p_indoor boolean,
                IN p_location text
            )
            LANGUAGE plpgsql
            AS $procedure$
            BEGIN
                INSERT INTO "Court" (
                    "tournament_id", "name", "capacity", "surface", "indoor", "location"
                )
                VALUES (
                    p_tournament_id, p_name, p_capacity, p_surface, p_indoor, p_location
                );
            END;
            $procedure$;
            """,
            reverse_sql="""
            DROP PROCEDURE IF EXISTS public.sp_create_tournament(
                character varying, integer, date, date, text, surface_type, text
            );
            DROP PROCEDURE IF EXISTS public.sp_update_tournament(
                integer, character varying, integer, date, date, text, surface_type, text
            );
            DROP PROCEDURE IF EXISTS public.sp_create_court(
                integer, character varying, integer, surface_type, boolean, text
            );

            ALTER TABLE "Tournament"
            ALTER COLUMN "location" TYPE jsonb
            USING CASE
                WHEN "location" IS NULL OR btrim("location") = '' THEN NULL
                ELSE jsonb_build_object('address', "location")
            END;

            ALTER TABLE "Court"
            ALTER COLUMN "location" TYPE jsonb
            USING CASE
                WHEN "location" IS NULL OR btrim("location") = '' THEN NULL
                ELSE jsonb_build_object('address', "location")
            END;

            CREATE OR REPLACE PROCEDURE public.sp_create_tournament(
                IN p_name character varying,
                IN p_year integer,
                IN p_start date,
                IN p_end date,
                IN p_location jsonb,
                IN p_surface surface_type,
                IN p_description text
            )
            LANGUAGE plpgsql
            AS $procedure$
            BEGIN
                INSERT INTO "Tournament" (
                    "name", "year", "start_date", "end_date", "location", "surface", "description"
                )
                VALUES (
                    p_name, p_year, p_start, p_end, p_location, p_surface, p_description
                );
            END;
            $procedure$;

            CREATE OR REPLACE PROCEDURE public.sp_update_tournament(
                IN p_id integer,
                IN p_name character varying,
                IN p_year integer,
                IN p_start date,
                IN p_end date,
                IN p_location jsonb,
                IN p_surface surface_type,
                IN p_description text
            )
            LANGUAGE plpgsql
            AS $procedure$
            BEGIN
                UPDATE "Tournament"
                SET
                    "name" = p_name,
                    "year" = p_year,
                    "start_date" = p_start,
                    "end_date" = p_end,
                    "location" = p_location,
                    "surface" = p_surface,
                    "description" = p_description,
                    "updated_at" = CURRENT_TIMESTAMP
                WHERE "id" = p_id;
            END;
            $procedure$;

            CREATE OR REPLACE PROCEDURE public.sp_create_court(
                IN p_tournament_id integer,
                IN p_name character varying,
                IN p_capacity integer,
                IN p_surface surface_type,
                IN p_indoor boolean,
                IN p_location jsonb
            )
            LANGUAGE plpgsql
            AS $procedure$
            BEGIN
                INSERT INTO "Court" (
                    "tournament_id", "name", "capacity", "surface", "indoor", "location"
                )
                VALUES (
                    p_tournament_id, p_name, p_capacity, p_surface, p_indoor, p_location
                );
            END;
            $procedure$;
            """,
        ),
    ]
