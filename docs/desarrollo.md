# Guía de desarrollo

## Requisitos previos

- Python 3.12+
- Node.js 20+
- Docker Desktop

## Levantar el entorno local

```bash
# Base de datos
docker compose up -d

# Backend (desde backend/)
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (desde frontend/)
npm install
npm run dev          # Vite en http://localhost:5173
```

Vite redirige `/api/*` al backend en `:8000` gracias a la configuración en `vite.config.js`.

## Build de producción

```bash
# 1. Compilar el frontend
cd frontend
npm run build        # genera frontend/dist/

# 2. Servir con uvicorn (monta dist/ como archivos estáticos)
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

> En producción el frontend compilado puede servirse desde Nginx o montarse directamente desde FastAPI con `StaticFiles`.

## Estructura del backend

```
backend/
├── main.py             # Rutas y lógica de negocio principal
├── auth.py             # JWT (python-jose) + bcrypt
├── database.py         # Engine async, SessionLocal, modelo TimeEntry
├── email_service.py    # HTML del correo, adjuntos y envío SMTP
└── report_generator.py # Excel (openpyxl) y PDF (ReportLab)
```

### Agregar un nuevo endpoint

1. Definir la función en `main.py` con `@app.get/post(...)`.
2. Añadir `db: AsyncSession = Depends(get_session)` y `_: str = Depends(get_current_user)` para acceso a BD y autenticación.
3. Documentar el endpoint en `docs/api.md`.

### Agregar columnas al modelo

1. Añadir `Mapped[...]` en `TimeEntry` (`database.py`).
2. Actualizar `parse_csv_file` en `main.py` para leer la columna nueva.
3. Actualizar `entry_to_dict` en `main.py` para incluirla en la respuesta.
4. Recrear la tabla (bajar el volumen Docker o usar migraciones Alembic).

## Estructura del frontend

```
frontend/src/
├── App.vue         # Shell: maneja token JWT y monta Login o Dashboard
├── Login.vue       # Formulario de autenticación
├── Dashboard.vue   # Vista principal con tabs, gráficos y modal de email
└── style.scss      # Estilos globales y componentes
```

### Flujo de autenticación en el frontend

1. `App.vue` busca `localStorage.getItem('token')` al montar.
2. Si existe, muestra `Dashboard`; si no, muestra `Login`.
3. `Login.vue` emite el evento `login` con el token al autenticarse.
4. Para cerrar sesión se borra el token de `localStorage` y se recarga.

### Agregar un gráfico nuevo

1. Agregar un `<canvas ref="miChart">` en el template de `Dashboard.vue`.
2. Declarar el ref: `const miChart = ref(null)`.
3. Inicializar el chart dentro de `renderCharts()` y agregar `chart.destroy()` en `destroyCharts()`.

## Dependencias del backend

| Paquete | Versión | Uso |
|---------|---------|-----|
| `fastapi` | 0.115.6 | Framework web |
| `uvicorn` | 0.32.1 | Servidor ASGI |
| `sqlalchemy[asyncio]` | 2.0.36 | ORM async |
| `asyncpg` | 0.30.0 | Driver PostgreSQL async |
| `python-jose[cryptography]` | 3.3.0 | JWT |
| `bcrypt` | 4.2.1 | Hash de contraseñas |
| `python-multipart` | 0.0.20 | Parseo de form-data (login) |
| `python-dotenv` | 1.0.1 | Variables de entorno |
| `aiosmtplib` | — | SMTP async |
| `openpyxl` | — | Generación de Excel |
| `reportlab` | — | Generación de PDF |

## Dependencias del frontend

| Paquete | Uso |
|---------|-----|
| `vue` 3.x | Framework reactivo |
| `vite` | Bundler y dev server |
| `chart.js` | Gráficos |
| `materialize-css` | UI components y estilos |
| `sass` | Preprocesador CSS |
