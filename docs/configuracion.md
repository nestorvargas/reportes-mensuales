# Configuración

## Variables de entorno

Crear el archivo `backend/.env` con las siguientes variables:

```env
# ── Base de datos ──────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://c360:c360pass@localhost:5433/complemento360

# ── Autenticación ──────────────────────────────────────────
APP_USER=nestor
APP_PASSWORD=complemento360
SECRET_KEY=cambia-esto-por-un-secreto-largo-y-aleatorio

# ── SMTP (correo saliente) ─────────────────────────────────
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-cuenta@gmail.com
SMTP_PASSWORD=tu-app-password
SMTP_FROM=tu-cuenta@gmail.com
```

### Descripción de cada variable

| Variable | Default | Descripción |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://c360:c360pass@localhost:5432/complemento360` | URL de conexión a PostgreSQL (usar puerto `5433` si se levanta con Docker Compose) |
| `APP_USER` | `nestor` | Usuario del login web |
| `APP_PASSWORD` | `complemento360` | Contraseña del login web |
| `SECRET_KEY` | `dev-secret-key` | Clave para firmar los tokens JWT. **Cambiar en producción** |
| `SMTP_HOST` | `smtp.gmail.com` | Host del servidor de correo |
| `SMTP_PORT` | `587` | Puerto SMTP (587 = STARTTLS) |
| `SMTP_USER` | — | Cuenta de correo para autenticarse |
| `SMTP_PASSWORD` | — | Contraseña o App Password de la cuenta |
| `SMTP_FROM` | igual que `SMTP_USER` | Dirección que aparece en el campo "De" |

## Base de datos con Docker

El archivo `docker-compose.yml` levanta PostgreSQL 16 en el puerto `5433` del host:

```bash
docker compose up -d      # inicia
docker compose down       # detiene (los datos persisten en el volumen pgdata)
docker compose down -v    # detiene y borra el volumen
```

La tabla `time_entries` se crea automáticamente al arrancar el backend por primera vez.

## Configurar Gmail como SMTP

1. Activar la verificación en dos pasos en tu cuenta de Google.
2. Ir a **Cuenta → Seguridad → Contraseñas de aplicación**.
3. Generar una contraseña de aplicación (16 caracteres).
4. Usar esa contraseña en `SMTP_PASSWORD`.

## CSVs de Azure DevOps

Colocar los archivos en la carpeta `reportes_mensuales/` con el formato de nombre:

```
{mes_en_español}-{año}.csv
```

Ejemplos válidos:
- `marzo-2026.csv`
- `febrero-2026.csv`
- `enero-2025.csv`

### Columnas esperadas en el CSV

| Columna CSV | Campo en BD |
|-------------|-------------|
| `Minutes` | `minutes` |
| `User` | `user` |
| `User Id` | `user_id` |
| `Work Item Id` | `work_item_id` |
| `Work Item Title` | `work_item_title` |
| `Date` | `date` |
| `Week` | `week` |
| `Type` | `type` |
| `Comment` | `comment` |
| `Project` | `project` |
| `Parent Id` | `parent_id` |
| `Parent Title` | `parent_title` |

El CSV debe estar codificado en **UTF-8** o **UTF-8 con BOM** (que es el default de ADO).
