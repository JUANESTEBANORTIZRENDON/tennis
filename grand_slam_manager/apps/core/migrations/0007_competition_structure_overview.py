"""Agrega lecturas enriquecidas para cuadros competitivos y rondas."""

from django.db import migrations


SQL = r"""
CREATE OR REPLACE FUNCTION public.sp_subcategories_overview_json(p_limit integer DEFAULT 300)
RETURNS SETOF jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    safe_limit integer := LEAST(GREATEST(COALESCE(p_limit, 300), 1), 1000);
BEGIN
    IF NOT public.fn_crud_table_exists('SubCategory') THEN
        RETURN;
    END IF;

    RETURN QUERY EXECUTE format(
        'SELECT to_jsonb(row_data)
        FROM (
            SELECT
                sc.id,
                sc.name,
                sc.category_id,
                COALESCE(c.name, ''-'') AS categoria,
                COALESCE(t.name, ''-'') AS torneo,
                sc.draw_size,
                sc.description
            FROM %1$I sc
            LEFT JOIN %2$I c ON c.id = sc.category_id
            LEFT JOIN %3$I t ON t.id = c.tournament_id
            ORDER BY t.name NULLS LAST, c.id, sc.name, sc.id
            LIMIT %4$s
        ) row_data',
        'SubCategory',
        'Category',
        'Tournament',
        safe_limit
    );
END;
$$;

CREATE OR REPLACE FUNCTION public.sp_rounds_overview_json(p_limit integer DEFAULT 300)
RETURNS SETOF jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    safe_limit integer := LEAST(GREATEST(COALESCE(p_limit, 300), 1), 1000);
BEGIN
    IF NOT public.fn_crud_table_exists('Round') THEN
        RETURN;
    END IF;

    RETURN QUERY EXECUTE format(
        'SELECT to_jsonb(row_data)
        FROM (
            SELECT
                r.id,
                r.round_name,
                r.round_number,
                r.best_of_sets,
                r.subcategory_id,
                COALESCE(sc.name, ''-'') AS cuadro,
                COALESCE(c.name, ''-'') AS categoria,
                c.id AS category_id,
                COALESCE(t.name, ''-'') AS torneo,
                r.description
            FROM %1$I r
            LEFT JOIN %2$I sc ON sc.id = r.subcategory_id
            LEFT JOIN %3$I c ON c.id = sc.category_id
            LEFT JOIN %4$I t ON t.id = c.tournament_id
            ORDER BY t.name NULLS LAST, c.id, sc.id, r.round_number, r.id
            LIMIT %5$s
        ) row_data',
        'Round',
        'SubCategory',
        'Category',
        'Tournament',
        safe_limit
    );
END;
$$;
"""


REVERSE_SQL = r"""
DROP FUNCTION IF EXISTS public.sp_rounds_overview_json(integer);
DROP FUNCTION IF EXISTS public.sp_subcategories_overview_json(integer);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_sanctions_overview"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
