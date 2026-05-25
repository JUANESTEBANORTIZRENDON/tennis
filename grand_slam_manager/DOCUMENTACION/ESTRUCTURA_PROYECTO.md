# Documentacion del proyecto Victory's

## 1. Resumen

Victory's es una aplicacion Django 5 para administrar torneos deportivos. El concepto inicial proviene de sistematizar torneos tipo Grand Slam.

El proyecto tiene dos zonas:

- Zona publica: landing en `/` con torneos vigentes y consulta de jugadores.
- Zona interna: panel administrativo protegido por login en `/login/`.

La base de datos es PostgreSQL/Neon y ya existe. Los modelos usan `managed = False`, por eso Django no crea ni modifica las tablas con migraciones.

## 2. Flujo de navegacion

```text
/                  -> landing publica
/login/            -> acceso administrador/director
/dashboard/        -> panel interno
/users/create/     -> crear cuentas internas
```

Los usuarios finales no crean cuentas. Las cuentas se crean desde el panel administrativo.

## 3. Estructura general

```text
grand_slam_manager/
├── manage.py
├── requirements.txt
├── README.md
├── PRUEBAS_LOCALES.md
├── grand_slam_manager/
├── apps/
├── templates/
├── static/
└── DOCUMENTACION/
```

## 4. Configuracion principal

### `grand_slam_manager/settings.py`

Contiene apps instaladas, conexion a base de datos, correo, sesiones, archivos estaticos y seguridad de cookies.

Variables importantes:

- `DATABASE_URL`: conexion a Neon/PostgreSQL.
- `SECRET_KEY`: clave de Django.
- `EMAIL_2FA_ENABLED`: activa o desactiva segundo factor por correo.
- `LOGIN_URL`: apunta a `/login/`.

### `grand_slam_manager/urls.py`

Une las rutas de todos los modulos. La ruta raiz usa `apps.core.views.home`.

## 5. Modulo `apps/core`

Contiene la base comun del sistema:

- `views.py`: landing publica y dashboard interno.
- `permissions.py`: reglas de acceso.
- `context_processors.py`: menu y usuario actual.
- `db.py`: helpers SQL seguros.
- `procedures.py`: llamadas a procedimientos almacenados.
- `services/public_service.py`: datos resumidos para la landing.
- `services/dashboard_service.py`: metricas del panel interno.
- `migrations/`: migraciones SQL para sincronizar cambios de Neon.

Permisos actuales:

- Solo roles administrativos entran al panel.
- `admin_required` permite administrar usuarios y auditoria.
- `director_required` permite operaciones deportivas a administradores y directores.
- Los usuarios sin rol administrativo se expulsan del panel y vuelven al login.

## 6. Modulo `apps/accounts`

Gestiona login, doble factor, logout y cuentas internas.

Rutas:

- `/login/`
- `/login/verify/`
- `/logout/`
- `/users/`
- `/users/create/`

Piezas principales:

- `forms.py`: formularios de login, 2FA y creacion de usuario.
- `views.py`: flujo de acceso y administracion de usuarios.
- `services/user_service.py`: autenticacion, consulta de roles y creacion de cuentas.

La creacion de usuarios guarda la contrasena con `make_password` y relaciona el usuario con un rol en `UserRole` si la tabla esta disponible.

## 7. Modulos deportivos

### `apps/tournaments`

Gestiona torneos, canchas, categorias, subcategorias y rondas.

Rutas principales:

- `/tournaments/`
- `/tournaments/create/`
- `/courts/`
- `/categories/`

### `apps/players`

Gestiona jugadores, lesiones, equipos e inscripciones.

Rutas principales:

- `/players/`
- `/players/create/`
- `/players/<id>/`
- `/injuries/`
- `/teams/`
- `/entries/`

La landing publica reutiliza consultas seguras de jugadores, pero solo muestra datos resumidos.

### `apps/matches`

Gestiona partidos, participantes, sets, programacion y sesiones.

Rutas principales:

- `/matches/`
- `/matches/create/`
- `/matches/<id>/center/`
- `/schedule/`

### `apps/officials`

Gestiona oficiales y asignaciones.

Rutas principales:

- `/officials/`
- `/officials/create/`
- `/officials/assign/`

### `apps/sanctions`

Gestiona sanciones y apelaciones.

Rutas principales:

- `/sanctions/`
- `/sanctions/create/`
- `/sanctions/appeals/create/`

### `apps/audit`

Gestiona trazabilidad del sistema.

Ruta principal:

- `/audit/`

## 8. Plantillas

```text
templates/
├── base.html
├── accounts/
├── core/
├── shared/
├── tournaments/
├── players/
├── matches/
├── officials/
├── sanctions/
└── audit/
```

Plantillas clave:

- `templates/core/landing.html`: pagina publica.
- `templates/core/dashboard.html`: inicio del panel interno.
- `templates/base.html`: layout del panel administrativo.
- `templates/shared/table.html`: tabla reutilizable.
- `templates/shared/form_page.html`: formulario reutilizable.

## 9. Archivos estaticos

`static/css/app.css` contiene estilos del panel y de la landing publica.

La landing usa clases con prefijo `public-` para mantener separado su estilo del panel administrativo.

## 10. Base de datos

La aplicacion depende de tablas y procedimientos existentes.

Procedimientos usados por los modulos:

- `sp_create_tournament`
- `sp_update_tournament`
- `sp_create_court`
- `sp_create_category`
- `sp_create_subcategory`
- `sp_create_round`
- `sp_create_player`
- `sp_create_injury`
- `sp_assign_injury_to_player`
- `sp_close_injury`
- `sp_create_team`
- `sp_add_team_member`
- `sp_create_entry`
- `sp_create_match`
- `sp_add_match_participant`
- `sp_register_match_set`
- `sp_finish_match`
- `sp_schedule_match`
- `sp_reschedule_match`
- `sp_create_session`
- `sp_add_match_to_session`
- `sp_create_official`
- `sp_assign_official_to_match`
- `sp_create_sanction`
- `sp_create_sanction_appeal`
- `sp_create_audit_log`

La creacion de usuarios usa inserciones directas controladas porque pertenece a la administracion de acceso, no a la operacion deportiva.

## 10.1 Migraciones aplicadas

El proyecto ya registra migraciones Django para cambios SQL controlados:

- `core.0001_baseline_neon_schema`: punto de partida del esquema existente.
- `core.0002_location_fields_as_text`: cambio de ubicaciones de `jsonb` a `text` en `Tournament` y `Court`, junto con sus procedimientos.

Los modelos principales siguen con `managed = False`; las migraciones se usan para SQL explicito.

## 11. Mapa rapido

| Necesidad | Donde mirar |
| --- | --- |
| Landing publica | `apps/core/views.py`, `apps/core/services/public_service.py`, `templates/core/landing.html` |
| Login administrativo | `apps/accounts/views.py`, `templates/accounts/login.html` |
| Crear usuarios | `apps/accounts/forms.py`, `apps/accounts/services/user_service.py` |
| Permisos | `apps/core/permissions.py` |
| Menu interno | `apps/core/context_processors.py` |
| Dashboard | `apps/core/services/dashboard_service.py`, `templates/core/dashboard.html` |
| Torneos | `apps/tournaments/` |
| Jugadores | `apps/players/` |
| Partidos | `apps/matches/` |
| Estilos | `static/css/app.css` |

## 12. Recomendaciones

- Mantener consultas en servicios, no en plantillas.
- No ejecutar migraciones sobre las tablas existentes de Neon.
- No agregar registro publico de usuarios.
- Actualizar README y esta documentacion si cambian rutas o permisos.
- Probar `/` y `/login/` despues de cambios de acceso.
