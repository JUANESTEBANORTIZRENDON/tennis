# Flujo publico y administrativo de Victory's

## Pagina publica

La ruta `/` muestra una landing de consulta.

Incluye:

- Resumen de torneos vigentes.
- Cantidad de torneos y jugadores consultables.
- Busqueda de jugadores.
- Ficha resumida de jugador en la misma pagina.

No muestra formularios de registro ni acceso de usuarios finales.

## Panel administrativo

La ruta `/login/` es el unico acceso al panel.

Roles permitidos:

- `Administrator`
- `Administrador`
- `Admin`
- `Tournament Director`
- `Director del Torneo`

Despues del login el usuario entra a `/dashboard/`.

## Diferencia visual y funcional

Administrador:

- Interfaz `Admin Hub`.
- Menu enfocado en sistema.
- Acceso a usuarios y auditoria.
- Crea cuentas internas.

Director de torneo:

- Interfaz `Tournament Desk`.
- Menu enfocado en operacion deportiva.
- Acceso a torneos, jugadores, partidos, programacion y oficiales.
- No administra usuarios ni auditoria.

## Creacion de cuentas

Las cuentas se crean desde:

```text
/users/create/
```

El formulario pide:

- Correo.
- Nombre completo.
- Telefono opcional.
- Contrasena temporal.
- Rol.
- Estado activo/inactivo.

La contrasena se guarda con hash de Django.

## Archivos relacionados

- `apps/core/services/public_service.py`
- `apps/core/views.py`
- `templates/core/landing.html`
- `apps/accounts/views.py`
- `apps/accounts/services/user_service.py`
- `apps/core/permissions.py`
