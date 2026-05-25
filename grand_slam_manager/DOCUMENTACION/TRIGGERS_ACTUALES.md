# Triggers actuales

Generado el 2026-05-25 desde PostgreSQL/Neon. Incluye triggers no internos activos en el esquema `public`, junto con la funcion que ejecutan.

## Tabla Category

### biu_category_integrity

- Funcion ejecutada: `trg_validate_category`

```sql
CREATE TRIGGER biu_category_integrity BEFORE INSERT OR UPDATE ON "Category" FOR EACH ROW EXECUTE FUNCTION trg_validate_category();
```

## Tabla Court

### biu_court_integrity

- Funcion ejecutada: `trg_validate_court`

```sql
CREATE TRIGGER biu_court_integrity BEFORE INSERT OR UPDATE ON "Court" FOR EACH ROW EXECUTE FUNCTION trg_validate_court();
```

## Tabla Entry

### biu_entry_integrity

- Funcion ejecutada: `trg_validate_entry`

```sql
CREATE TRIGGER biu_entry_integrity BEFORE INSERT OR UPDATE ON "Entry" FOR EACH ROW EXECUTE FUNCTION trg_validate_entry();
```

## Tabla Injury

### biu_injury_integrity

- Funcion ejecutada: `trg_validate_injury`

```sql
CREATE TRIGGER biu_injury_integrity BEFORE INSERT OR UPDATE ON "Injury" FOR EACH ROW EXECUTE FUNCTION trg_validate_injury();
```

### trg_injury_recovery

- Funcion ejecutada: `fn_injury_recovery_handler`

```sql
CREATE TRIGGER trg_injury_recovery BEFORE INSERT OR UPDATE ON "Injury" FOR EACH ROW EXECUTE FUNCTION fn_injury_recovery_handler();
```

## Tabla Match

### aiu_match_sync_tournament_status

- Funcion ejecutada: `trg_sync_tournament_status_from_match`

```sql
CREATE TRIGGER aiu_match_sync_tournament_status AFTER INSERT OR UPDATE OF status ON "Match" FOR EACH ROW EXECUTE FUNCTION trg_sync_tournament_status_from_match();
```

### biu_match_schedule_integrity

- Funcion ejecutada: `trg_validate_match`

```sql
CREATE TRIGGER biu_match_schedule_integrity BEFORE INSERT OR UPDATE ON "Match" FOR EACH ROW EXECUTE FUNCTION trg_validate_match();
```

## Tabla MatchParticipant

### biu_match_participant_integrity

- Funcion ejecutada: `trg_validate_match_participant`

```sql
CREATE TRIGGER biu_match_participant_integrity BEFORE INSERT OR UPDATE ON "MatchParticipant" FOR EACH ROW EXECUTE FUNCTION trg_validate_match_participant();
```

## Tabla MatchPoint

### bi_match_point_score_integrity

- Funcion ejecutada: `trg_validate_match_point_score`

```sql
CREATE TRIGGER bi_match_point_score_integrity BEFORE INSERT ON "MatchPoint" FOR EACH ROW EXECUTE FUNCTION trg_validate_match_point_score();
```

## Tabla MatchSet

### bi_match_set_requires_in_progress

- Funcion ejecutada: `trg_match_set_requires_in_progress`

```sql
CREATE TRIGGER bi_match_set_requires_in_progress BEFORE INSERT ON "MatchSet" FOR EACH ROW EXECUTE FUNCTION trg_match_set_requires_in_progress();
```

### biu_match_set_integrity

- Funcion ejecutada: `trg_validate_match_set`

```sql
CREATE TRIGGER biu_match_set_integrity BEFORE INSERT OR UPDATE ON "MatchSet" FOR EACH ROW EXECUTE FUNCTION trg_validate_match_set();
```

## Tabla Round

### biu_round_integrity

- Funcion ejecutada: `trg_validate_round`

```sql
CREATE TRIGGER biu_round_integrity BEFORE INSERT OR UPDATE ON "Round" FOR EACH ROW EXECUTE FUNCTION trg_validate_round();
```

## Tabla Sanction

### biu_sanction_target_integrity

- Funcion ejecutada: `trg_validate_sanction_target`

```sql
CREATE TRIGGER biu_sanction_target_integrity BEFORE INSERT OR UPDATE ON "Sanction" FOR EACH ROW EXECUTE FUNCTION trg_validate_sanction_target();
```

## Tabla Session

### biu_session_integrity

- Funcion ejecutada: `trg_validate_session`

```sql
CREATE TRIGGER biu_session_integrity BEFORE INSERT OR UPDATE ON "Session" FOR EACH ROW EXECUTE FUNCTION trg_validate_session();
```

## Tabla SubCategory

### biu_subcategory_integrity

- Funcion ejecutada: `trg_validate_subcategory`

```sql
CREATE TRIGGER biu_subcategory_integrity BEFORE INSERT OR UPDATE ON "SubCategory" FOR EACH ROW EXECUTE FUNCTION trg_validate_subcategory();
```

## Tabla TeamMember

### biu_team_member_integrity

- Funcion ejecutada: `trg_validate_team_member`

```sql
CREATE TRIGGER biu_team_member_integrity BEFORE INSERT OR UPDATE ON "TeamMember" FOR EACH ROW EXECUTE FUNCTION trg_validate_team_member();
```

## Tabla Tournament

### biu_tournament_dates

- Funcion ejecutada: `trg_validate_tournament_dates`

```sql
CREATE TRIGGER biu_tournament_dates BEFORE INSERT OR UPDATE ON "Tournament" FOR EACH ROW EXECUTE FUNCTION trg_validate_tournament_dates();
```

## Tabla UserAccount

### biu_user_account_normalize

- Funcion ejecutada: `trg_normalize_user_account`

```sql
CREATE TRIGGER biu_user_account_normalize BEFORE INSERT OR UPDATE ON "UserAccount" FOR EACH ROW EXECUTE FUNCTION trg_normalize_user_account();
```

## Funciones ejecutadas por triggers

### CREATE OR REPLACE FUNCTION public.trg_validate_category()
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_category()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF NEW.gender NOT IN ('M', 'F') THEN
        RAISE EXCEPTION 'invalid_category_gender';
    END IF;
    IF NEW.mode NOT IN ('Singles', 'Doubles') THEN
        RAISE EXCEPTION 'invalid_category_mode';
    END IF;
    RETURN NEW;
END;
$function$
```

### CREATE OR REPLACE FUNCTION public.trg_validate_court()
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_court()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    tournament_surface text;
BEGIN
    IF NEW.capacity IS NOT NULL AND NEW.capacity < 0 THEN
        RAISE EXCEPTION 'invalid_court_capacity';
    END IF;

    SELECT "surface"::text INTO tournament_surface
    FROM "Tournament"
    WHERE "id" = NEW.tournament_id;

    IF tournament_surface IS NOT NULL
       AND NEW.surface IS NOT NULL
       AND tournament_surface <> NEW.surface::text THEN
        RAISE EXCEPTION 'court_surface_must_match_tournament';
    END IF;

    RETURN NEW;
END;
$function$
```

### CREATE OR REPLACE FUNCTION public.trg_validate_entry()
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_entry()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
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
$function$
```

### CREATE OR REPLACE FUNCTION public.trg_validate_injury()
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_injury()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF NEW.recovery_date IS NOT NULL AND NEW.injury_date IS NOT NULL AND NEW.recovery_date < NEW.injury_date THEN
        RAISE EXCEPTION 'invalid_recovery_date';
    END IF;
    IF NEW.recovery_date IS NOT NULL THEN
        NEW.active := FALSE;
    END IF;
    RETURN NEW;
END;
$function$
```

### CREATE OR REPLACE FUNCTION public.fn_injury_recovery_handler()
```sql
CREATE OR REPLACE FUNCTION public.fn_injury_recovery_handler()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Si se modifica recovery_date en la inserción/actualización
  IF NEW.recovery_date IS NOT NULL THEN
    -- Si antes no había fecha de recuperación, marcar inactivo
    NEW.active := FALSE;
  END IF;
  -- No permitir que se modifique recovery_date en una lesión ya
  -- recuperada (protección contra reactivaciones).
  IF TG_OP = 'UPDATE' AND OLD.recovery_date IS NOT NULL THEN
    RAISE EXCEPTION 'No se puede modificar una lesión ya recuperada.';
  END IF;
  RETURN NEW;
END;
$function$
```

### CREATE OR REPLACE FUNCTION public.trg_sync_tournament_status_from_match()
```sql
CREATE OR REPLACE FUNCTION public.trg_sync_tournament_status_from_match()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_tournament_id integer;
    v_open_matches integer;
    v_total_matches integer;
BEGIN
    SELECT c.tournament_id
    INTO v_tournament_id
    FROM "Round" r
    JOIN "SubCategory" sc ON sc.id = r.subcategory_id
    JOIN "Category" c ON c.id = sc.category_id
    WHERE r.id = NEW.round_id;

    IF v_tournament_id IS NULL THEN
        RETURN NEW;
    END IF;

    IF NEW.status::text = 'InProgress' THEN
        UPDATE "Tournament"
        SET status = 'En proceso'
        WHERE id = v_tournament_id
          AND status <> 'Finalizado';
    END IF;

    SELECT COUNT(*),
           COUNT(*) FILTER (WHERE m.status::text NOT IN ('Completed', 'Retired', 'Walkover', 'Cancelled', 'Disqualified'))
    INTO v_total_matches, v_open_matches
    FROM "Match" m
    JOIN "Round" r ON r.id = m.round_id
    JOIN "SubCategory" sc ON sc.id = r.subcategory_id
    JOIN "Category" c ON c.id = sc.category_id
    WHERE c.tournament_id = v_tournament_id;

    IF v_total_matches > 0 AND v_open_matches = 0 THEN
        UPDATE "Tournament"
        SET status = 'Finalizado'
        WHERE id = v_tournament_id;
    END IF;

    RETURN NEW;
END;
$function$
```

### CREATE OR REPLACE FUNCTION public.trg_validate_match()
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_match()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    conflict_count integer;
BEGIN
    IF NEW.scheduled_datetime IS NOT NULL AND NEW.court_id IS NOT NULL THEN
        SELECT COUNT(*) INTO conflict_count
        FROM "Match"
        WHERE "court_id" = NEW.court_id
          AND "scheduled_datetime" = NEW.scheduled_datetime
          AND "id" <> COALESCE(NEW.id, -1)
          AND COALESCE("status"::text, '') NOT IN ('Cancelled');

        IF conflict_count > 0 THEN
            RAISE EXCEPTION 'court_schedule_conflict';
        END IF;
    END IF;
    RETURN NEW;
END;
$function$
```

### CREATE OR REPLACE FUNCTION public.trg_validate_match_participant()
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_match_participant()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
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
$function$
```

### CREATE OR REPLACE FUNCTION public.trg_validate_match_point_score()
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_match_point_score()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
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
$function$
```

### CREATE OR REPLACE FUNCTION public.trg_match_set_requires_in_progress()
```sql
CREATE OR REPLACE FUNCTION public.trg_match_set_requires_in_progress()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    match_status text;
BEGIN
    EXECUTE format('SELECT status::text FROM %I WHERE id = $1', 'Match')
    INTO match_status
    USING NEW.match_id;

    IF match_status IS NULL THEN
        RAISE EXCEPTION 'Match not found for set registration.';
    END IF;
    IF match_status <> 'InProgress' THEN
        RAISE EXCEPTION 'Sets can only be registered while match is InProgress.';
    END IF;
    RETURN NEW;
END;
$function$
```

### CREATE OR REPLACE FUNCTION public.trg_validate_match_set()
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_match_set()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF NEW.set_number IS NULL OR NEW.set_number < 1 THEN
        RAISE EXCEPTION 'invalid_set_number';
    END IF;

    IF NEW.team_a_games IS NOT NULL AND NEW.team_a_games < 0 THEN
        RAISE EXCEPTION 'invalid_team_a_games';
    END IF;
    IF NEW.team_b_games IS NOT NULL AND NEW.team_b_games < 0 THEN
        RAISE EXCEPTION 'invalid_team_b_games';
    END IF;

    IF NEW.winner_team_id IS NOT NULL
       AND NEW.team_a_games IS NOT NULL
       AND NEW.team_b_games IS NOT NULL
       AND NEW.team_a_games = NEW.team_b_games THEN
        RAISE EXCEPTION 'set_must_have_winner';
    END IF;

    RETURN NEW;
END;
$function$
```

### CREATE OR REPLACE FUNCTION public.trg_validate_round()
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_round()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF NEW.round_number IS NULL OR NEW.round_number < 1 THEN
        RAISE EXCEPTION 'invalid_round_number';
    END IF;
    IF NEW.best_of_sets NOT IN (1, 3, 5) THEN
        RAISE EXCEPTION 'invalid_best_of_sets';
    END IF;
    RETURN NEW;
END;
$function$
```

### CREATE OR REPLACE FUNCTION public.trg_validate_sanction_target()
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_sanction_target()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    payload jsonb := to_jsonb(NEW);
    target_count integer := 0;
BEGIN
    IF payload ? 'player_id' AND payload ->> 'player_id' IS NOT NULL AND payload ->> 'player_id' <> '' THEN
        target_count := target_count + 1;
    END IF;
    IF payload ? 'team_id' AND payload ->> 'team_id' IS NOT NULL AND payload ->> 'team_id' <> '' THEN
        target_count := target_count + 1;
    END IF;
    IF payload ? 'official_id' AND payload ->> 'official_id' IS NOT NULL AND payload ->> 'official_id' <> '' THEN
        target_count := target_count + 1;
    END IF;

    IF target_count <> 1 THEN
        RAISE EXCEPTION 'sanction_requires_one_target';
    END IF;
    RETURN NEW;
END;
$function$
```

### CREATE OR REPLACE FUNCTION public.trg_validate_session()
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_session()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF NEW.start_datetime IS NOT NULL AND NEW.end_datetime IS NOT NULL AND NEW.start_datetime > NEW.end_datetime THEN
        RAISE EXCEPTION 'invalid_session_dates';
    END IF;
    RETURN NEW;
END;
$function$
```

### CREATE OR REPLACE FUNCTION public.trg_validate_subcategory()
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_subcategory()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF NEW.draw_size IS NULL OR NEW.draw_size NOT IN (2, 4, 8, 16, 32, 64, 128) THEN
        RAISE EXCEPTION 'invalid_grand_slam_draw_size';
    END IF;
    RETURN NEW;
END;
$function$
```

### CREATE OR REPLACE FUNCTION public.trg_validate_team_member()
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_team_member()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    members_count integer;
BEGIN
    IF NEW.player_id IS NULL OR NEW.team_id IS NULL THEN
        RAISE EXCEPTION 'invalid_team_member';
    END IF;

    EXECUTE format('SELECT COUNT(*) FROM %I WHERE team_id = $1 AND player_id <> $2', TG_TABLE_NAME)
    INTO members_count
    USING NEW.team_id, NEW.player_id;

    IF members_count >= 2 THEN
        RAISE EXCEPTION 'team_member_limit_exceeded';
    END IF;

    RETURN NEW;
END;
$function$
```

### CREATE OR REPLACE FUNCTION public.trg_validate_tournament_dates()
```sql
CREATE OR REPLACE FUNCTION public.trg_validate_tournament_dates()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    open_matches integer := 0;
BEGIN
    IF NEW.start_date IS NOT NULL AND NEW.end_date IS NOT NULL AND NEW.start_date > NEW.end_date THEN
        RAISE EXCEPTION 'invalid_tournament_dates';
    END IF;

    IF NEW.status IS NULL OR NEW.status NOT IN ('Pendiente por inscripciones', 'Activo', 'En proceso', 'Finalizado') THEN
        RAISE EXCEPTION 'invalid_tournament_status';
    END IF;

    IF NEW.status IN ('Activo', 'En proceso') AND NOT public.fn_tournament_entries_complete(NEW.id) THEN
        RAISE EXCEPTION 'tournament_entries_incomplete';
    END IF;

    IF NEW.status = 'Finalizado' THEN
        SELECT COUNT(*)
        INTO open_matches
        FROM "Match" m
        JOIN "Round" r ON r.id = m.round_id
        JOIN "SubCategory" sc ON sc.id = r.subcategory_id
        JOIN "Category" c ON c.id = sc.category_id
        WHERE c.tournament_id = NEW.id
          AND m.status::text NOT IN ('Completed', 'Retired', 'Walkover', 'Cancelled', 'Disqualified');

        IF open_matches > 0 THEN
            RAISE EXCEPTION 'tournament_has_open_matches';
        END IF;
    END IF;

    RETURN NEW;
END;
$function$
```

### CREATE OR REPLACE FUNCTION public.trg_normalize_user_account()
```sql
CREATE OR REPLACE FUNCTION public.trg_normalize_user_account()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.email := lower(btrim(NEW.email));
    RETURN NEW;
END;
$function$
```
