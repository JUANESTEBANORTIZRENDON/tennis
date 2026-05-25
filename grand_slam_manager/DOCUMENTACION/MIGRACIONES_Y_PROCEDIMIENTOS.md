# Migraciones y procedimientos en Victory's

## Se pueden usar migraciones?

Si. La recomendacion para este proyecto es usar migraciones de Django para versionar SQL, no para que Django administre automaticamente las tablas existentes.

Las tablas actuales vienen de Neon/PostgreSQL y los modelos tienen:

```python
managed = False
```

Eso debe mantenerse para evitar que Django intente crear, borrar o alterar tablas que ya controla la base de datos.

## Estrategia recomendada

Usar `apps/core/migrations/` como carpeta central de migraciones SQL.

La migracion inicial:

```text
apps/core/migrations/0001_baseline_neon_schema.py
```

no cambia la base. Solo marca el punto de partida del esquema existente.

Las futuras migraciones deben usar:

```python
migrations.RunSQL(sql=..., reverse_sql=...)
```

para versionar:

- Cambios de columnas o tablas.
- Indices.
- Procedimientos almacenados.
- Funciones.
- Triggers.
- Vistas o consultas materializadas si se agregan.

## Flujo de trabajo propuesto

1. Definir el cambio de base de datos.
2. Crear una migracion SQL en `apps/core/migrations/`.
3. Incluir `reverse_sql` cuando sea posible.
4. Probar localmente o en una base Neon de desarrollo.
5. Ejecutar `python manage.py migrate core`.
6. Ajustar servicios/formularios/templates si la app debe usar el cambio.

## Comandos utiles

Ver migraciones pendientes:

```powershell
.\.venv\Scripts\python.exe manage.py showmigrations core
```

Crear una migracion vacia para SQL:

```powershell
.\.venv\Scripts\python.exe manage.py makemigrations core --empty --name nombre_del_cambio
```

Aplicar migraciones del modulo core:

```powershell
.\.venv\Scripts\python.exe manage.py migrate core
```

Ver SQL planificado por una migracion:

```powershell
.\.venv\Scripts\python.exe manage.py sqlmigrate core 0002
```

## Como llama Django a los procedimientos

La app no hace CRUD directo desde los modelos. Las vistas usan formularios y luego llaman servicios.

Flujo:

```text
Vista -> Formulario -> Servicio -> Procedimiento almacenado -> Triggers/PostgreSQL
```

Ejemplo:

```python
tournament_service.create_tournament(form.cleaned_data)
```

Ese servicio llama:

```python
call_stored_procedure("sp_create_tournament", data)
```

El helper `call_stored_procedure`:

1. Consulta en PostgreSQL los parametros del procedimiento con `pg_proc`.
2. Ordena los valores del formulario segun esos parametros.
3. Convierte JSON cuando aplica.
4. Ejecuta:

```sql
CALL "sp_create_tournament"(...)
```

Los triggers configurados en PostgreSQL se ejecutan automaticamente cuando el procedimiento inserta, actualiza o elimina datos.

## Reglas para no generar incongruencias

- Mantener `managed = False` en modelos que representan tablas existentes.
- No usar `Model.objects.create()` para CRUD principal.
- No hacer escrituras directas desde templates o vistas.
- Crear o modificar procedimientos mediante migraciones SQL.
- Si una migracion cambia columnas, actualizar tambien modelos, servicios, formularios y documentacion.
- Probar primero en una base de desarrollo antes de ejecutar sobre Neon principal.

## Formularios con datos de la base

Los formularios administrativos no deben pedir IDs escritos a mano cuando el dato ya existe en Neon.

Ejemplos:

- Torneo.
- Partido.
- Jugador.
- Equipo.
- Oficial.
- Sancion.
- Categoria, cuadro y ronda.

Para eso se usa:

```text
apps/core/form_choices.py
```

Ese helper consulta las tablas y arma opciones como:

```text
1 - Grand Slam Medellin Open - 2026
P-AUS-008 - Noah Brown - AUS
1 - 2026-06-29 12:00:00 - Scheduled
```

El formulario envia el ID real al procedimiento almacenado, pero el usuario ve una opcion legible.

## Confirmacion pendiente

El punto de partida ya fue aplicado en Neon:

```text
core.0001_baseline_neon_schema
```

Tambien se aplico una migracion real:

```text
core.0002_location_fields_as_text
```

Esta migracion hizo lo siguiente:

- Cambio `Tournament.location` de `jsonb` a `text`.
- Cambio `Court.location` de `jsonb` a `text`.
- Reemplazo `sp_create_tournament` para recibir `p_location text`.
- Reemplazo `sp_update_tournament` para recibir `p_location text`.
- Reemplazo `sp_create_court` para recibir `p_location text`.
- Django ahora muestra campos de direccion normal, no JSON.

## Ubicaciones como texto

Antes los formularios pedian una ubicacion en formato JSON, por ejemplo:

```json
{"city":"Bogota","country":"Colombia"}
```

Ahora piden una direccion comun:

```text
Carrera 30 # 12-45, Bogota, Colombia
```

Los formularios afectados estan en:

- `apps/tournaments/forms.py`

Los servicios afectados estan en:

- `apps/tournaments/services/tournament_service.py`
- `apps/core/procedures.py`

## Pendiente recomendado

Para seguir trabajando con seguridad conviene confirmar:

- Si usaremos la base Neon actual como desarrollo.
- O si crearemos una base Neon separada para desarrollo y pruebas.
- Si cada cambio de procedimiento/trigger se versionara siempre como migracion SQL.
