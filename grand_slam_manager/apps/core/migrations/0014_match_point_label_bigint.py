from django.db import migrations


SQL = r"""
CREATE OR REPLACE FUNCTION public.fn_tennis_point_label(p_points_for bigint, p_points_against bigint)
RETURNS text
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    RETURN public.fn_tennis_point_label(p_points_for::integer, p_points_against::integer);
END;
$$;
"""


REVERSE_SQL = r"""
DROP FUNCTION IF EXISTS public.fn_tennis_point_label(bigint, bigint);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0013_match_point_scoring"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
