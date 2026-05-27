# Victory's

Victory's es una aplicacion web en Django 5 para administrar torneos deportivos. La idea nace de sistematizar torneos tipo Grand Slam, pero el nombre publico del sistema es Victory's.

## Flujo actual

- `/` es una landing publica de una sola pagina.
- La landing muestra torneos vigentes, resumen general y consulta publica de jugadores.
- `/login/` es exclusivo para administradores y directores del torneo.
- No existe registro publico de usuarios.
- Las cuentas internas se crean desde el panel administrativo en `/users/create/`.

## Que incluye

- Login propio contra `UserAccount`, `UserRole` y `Role`.
- Segundo factor por correo si `EMAIL_2FA_ENABLED=True`.
- Acceso interno limitado a roles administrativos: `Administrator`, `Administrador`, `Admin`, `Tournament Director` y `Director del Torneo`.
- Interfaz diferenciada por rol: administrador para control del sistema y director para operacion deportiva.
- Modelos Django `managed = False` para tablas existentes.
- Servicios por modulo para consultas SQL y procedimientos almacenados `sp_*`.
- Landing publica con datos resumidos y sin datos sensibles.
- Panel administrativo con torneos, jugadores, partidos, oficiales, sanciones, auditoria, usuarios y CRUD tecnico de tablas.

## Requisitos

- Python 3.12 o superior.
- Entorno virtual del proyecto o dependencias instaladas.
- Base PostgreSQL/Neon. La carpeta `DOCUMENTACION/` contiene DDL, procedimientos, triggers y datos de prueba para pgAdmin.
- Variables de entorno en `.env`.

## Instalacion local

```powershell
cd "C:\Users\USER\grand slam\grand_slam_manager"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Variables de entorno

El archivo `.env` local contiene la configuracion sensible y no debe subirse a Git.

```env
DATABASE_URL=postgresql://USUARIO:CLAVE@HOST.neon.tech/NOMBRE_DB?sslmode=require
SECRET_KEY=colocar_clave_segura
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_correo@gmail.com
EMAIL_HOST_PASSWORD=tu_clave_de_aplicacion
DEFAULT_FROM_EMAIL=Victory's <tu_correo@gmail.com>
EMAIL_2FA_ENABLED=True
```

Para probar sin envio de correo:

```env
EMAIL_2FA_ENABLED=False
```

## Ejecutar

Las migraciones del proyecto son SQL controlado con `RunSQL`; no se usan migraciones automaticas de modelos gestionados.

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Abre la landing publica:

```text
http://127.0.0.1:8000/
```

El panel interno queda en:

```text
http://127.0.0.1:8000/login/
```

## Usuarios internos

El login compara contrasenas con hash de Django. En desarrollo tambien permite valores temporales si ya existen en la base.

Ejemplos de prueba detectados:

```text
admin@example.com / hash123
director@example.com / hash456
```

En produccion guarda `password_hash` con `make_password` y usa contrasenas temporales solo al crear cuentas internas.

## Diferencias de roles

Administrador:

- Ve el panel con identidad `Admin Hub`.
- Tiene menu orientado a sistema, usuarios, auditoria y supervision.
- Puede crear cuentas internas en `/users/create/`.
- Puede consultar auditoria en `/audit/`.

Director de torneo:

- Ve el panel con identidad `Tournament Desk`.
- Tiene menu orientado a torneos, jugadores, partidos, programacion y oficiales.
- Puede gestionar la operacion deportiva.
- No puede entrar a `/users/` ni `/audit/`.

## Rutas principales

Publicas:

- `/`

Administrativas:

- `/login/`
- `/login/verify/`
- `/logout/`
- `/dashboard/`
- `/tournaments/`
- `/courts/`
- `/categories/`
- `/players/`
- `/matches/`
- `/schedule/`
- `/officials/`
- `/sanctions/`
- `/users/`
- `/users/create/`
- `/admin-data/`
- `/audit/`

## Notas tecnicas

- La landing publica de Victory's usa `apps/core/services/public_service.py`.
- El dashboard interno usa `apps/core/services/dashboard_service.py`.
- Las escrituras deportivas siguen concentradas en servicios y procedimientos almacenados.
- La creacion de usuarios internos se realiza desde `apps/accounts/services/user_service.py`.
- Las migraciones recomendadas son SQL con `RunSQL`, no migraciones automaticas sobre modelos existentes.
- El estado de un torneo nuevo siempre inicia como `Pendiente por inscripciones`.
- Un jugador solo puede tener un equipo activo a la vez; PostgreSQL lo valida con trigger e indice unico parcial.
- Las canchas son globales y se asignan al programar partidos o al crear emparejamientos de primera ronda.
- Match Center organiza solo la primera ronda; las rondas siguientes se alimentan automaticamente con ganadores.
- Ya se aplico una migracion para que `Tournament.location` y `Court.location` sean texto, no JSON.
- Los datos sensibles se enmascaran o se omiten en vistas publicas.
- `.env` esta ignorado por `.gitignore`.
