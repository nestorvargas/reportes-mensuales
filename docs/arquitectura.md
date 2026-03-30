# Arquitectura

## Diagrama general

```
┌─────────────────────────────────────────────────────┐
│                    Navegador                        │
│   Vue 3 + Vite · Materialize CSS · Chart.js        │
│   Login.vue  ──  App.vue  ──  Dashboard.vue        │
└─────────────────────┬───────────────────────────────┘
                      │ HTTP / JSON (Bearer JWT)
┌─────────────────────▼───────────────────────────────┐
│                 FastAPI (uvicorn)                   │
│  /api/auth/login                                    │
│  /api/reports          /api/reports/{m}/data        │
│  /api/reports/{f}/import                            │
│  /api/entries          /api/email/send              │
│                                                     │
│  auth.py · database.py · email_service.py           │
│  report_generator.py                               │
└───────────┬─────────────────────┬───────────────────┘
            │ asyncpg             │ SMTP (STARTTLS)
┌───────────▼──────────┐  ┌──────▼──────────────────┐
│  PostgreSQL 16        │  │  Servidor de correo      │
│  tabla: time_entries  │  │  (Gmail u otro SMTP)    │
└───────────────────────┘  └──────────────────────────┘
```

## Flujo de datos

### Importación de CSV

1. Los archivos CSV exportados desde Azure DevOps se depositan en `reportes_mensuales/`.
2. El backend lista los archivos al arrancar (`GET /api/reports`).
3. El usuario hace clic en **Importar** en el Dashboard.
4. `POST /api/reports/{filename}/import` lee el CSV, elimina los registros previos del mes y graba los nuevos en `time_entries`.

### Visualización

1. El Dashboard solicita `GET /api/reports/{month}/data` (por mes) o `GET /api/entries?date_from=…&date_to=…` (por rango).
2. El backend ejecuta la consulta en PostgreSQL y devuelve `{ rows, summary }`.
3. Vue renderiza KPIs, gráficos Chart.js y tabla de detalle con búsqueda.

### Envío de correo

1. El usuario abre el modal, agrega destinatarios, asunto y mensaje opcional.
2. `POST /api/email/send` obtiene las entradas del rango, genera Excel (openpyxl) y PDF (ReportLab) en memoria, construye el HTML del correo y lo envía con aiosmtplib.

## Modelo de datos — `time_entries`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `report_month` | String(20) | Clave del mes, ej. `"2026-03"` (indexada) |
| `minutes` | Integer | Duración del registro |
| `user` | String(200) | Nombre del usuario en ADO |
| `user_id` | String(100) | ID del usuario en ADO |
| `work_item_id` | String(50) | ID del work item |
| `work_item_title` | Text | Título del work item |
| `date` | String(10) | Fecha `YYYY-MM-DD` |
| `week` | String(10) | Identificador de semana (ADO) |
| `type` | String(100) | Tipo de actividad |
| `comment` | Text | Comentario del registro |
| `project` | String(200) | Proyecto en ADO |
| `parent_id` | String(50) | ID del work item padre |
| `parent_title` | Text | Título del work item padre |

## Autenticación

- Usuario y contraseña únicos, configurados en `.env` (`APP_USER`, `APP_PASSWORD`).
- La contraseña se hashea con **bcrypt** al iniciar el proceso.
- El login devuelve un JWT firmado con HS256, válido por **8 horas**.
- Todos los endpoints (excepto `/api/auth/login`) requieren `Authorization: Bearer <token>`.

## Formato de nombre de archivo CSV

El nombre del archivo determina el `report_month`:

```
{mes}-{año}.csv
```

Ejemplos: `marzo-2026.csv` → `2026-03`, `enero-2025.csv` → `2025-01`

Los nombres de mes se parsean en español (enero–diciembre).
