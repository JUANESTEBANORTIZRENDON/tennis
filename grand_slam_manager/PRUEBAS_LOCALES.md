# Prueba local manual

Estos pasos son para iniciar el proyecto de forma manual.

## 1. Entrar al directorio correcto

```powershell
cd "C:\Users\USER\grand slam\grand_slam_manager"
```

Este directorio es correcto porque aqui esta `manage.py`.

## 2. Ejecutar usando el Python del entorno virtual

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

No uses `python.exe manage.py runserver`, porque ese comando usa el Python global y puede no tener Django instalado.

## 3. Abrir la aplicacion

Landing publica:

```text
http://127.0.0.1:8000/
```

Panel administrativo:

```text
http://127.0.0.1:8000/login/
```

## Usuarios de prueba detectados en Neon

```text
admin@example.com / hash123
Rol: Administrator
```

```text
director@example.com / hash456
Rol: Tournament Director
```

Para la prueba local, `.env` queda con:

```env
EMAIL_2FA_ENABLED=False
```

Asi puedes entrar sin codigo de correo. Si activas `EMAIL_2FA_ENABLED=True`, el sistema enviara codigo al correo guardado en `UserAccount`.

## Pruebas rapidas del nuevo flujo

1. Abrir `/` sin iniciar sesion y validar que no redirige al login.
2. Buscar un jugador desde la landing.
3. Entrar a `/login/` con `admin@example.com` o `director@example.com`.
4. Abrir `/users/` y usar el boton `Crear usuario`.
5. Cerrar sesion y confirmar que el panel vuelve al login.
