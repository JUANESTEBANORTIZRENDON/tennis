"""Refuerza que un jugador solo tenga un equipo activo."""

from django.db import migrations


SQL = r"""
WITH ranked_members AS (
    SELECT
        ctid,
        player_id,
        start_date,
        ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY start_date DESC, team_id DESC) AS rn,
        MAX(start_date) OVER (PARTITION BY player_id) AS keep_start_date
    FROM "TeamMember"
    WHERE end_date IS NULL
)
UPDATE "TeamMember" tm
SET end_date = GREATEST(tm.start_date, ranked_members.keep_start_date - INTERVAL '1 day')::date
FROM ranked_members
WHERE tm.ctid = ranked_members.ctid
  AND ranked_members.rn > 1;

CREATE UNIQUE INDEX IF NOT EXISTS uq_teammember_one_active_team_per_player
ON "TeamMember" (player_id)
WHERE end_date IS NULL;
"""


REVERSE_SQL = r"""
DROP INDEX IF EXISTS uq_teammember_one_active_team_per_player;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0030_admin_crud_and_team_entry_rules"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
