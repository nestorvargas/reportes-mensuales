# Complemento 360 — Reportes de horas

Aplicación web para visualizar, importar y enviar reportes mensuales de horas trabajadas, generados desde Azure DevOps (formato CSV).

## Características

- Login con JWT (usuario único configurable por `.env`)
- Importación de CSVs mensuales a PostgreSQL
- Dashboard con KPIs y gráficos (Chart.js)
- Consulta por mes o por rango de fechas libre
- Envío de reportes por correo con adjuntos Excel y PDF
- Exportación con tres hojas: Resumen, Pivot por día y Detalle

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12 · FastAPI · SQLAlchemy async |
| Base de datos | PostgreSQL 16 (Docker) |
| Frontend | Vue 3 · Vite · Materialize CSS · Chart.js |
| Reportes | openpyxl (Excel) · ReportLab (PDF) |
| Email | aiosmtplib (SMTP con STARTTLS) |

## Inicio rápido

```bash
# 1. Levantar la base de datos
docker compose up -d

# 2. Configurar variables de entorno
cp backend/.env.example backend/.env
# Editar backend/.env con tus credenciales

# 3. Instalar dependencias del backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# 4. Instalar dependencias del frontend (otra terminal)
cd frontend
npm install
npm run dev
```

La app queda disponible en `http://localhost:5173` (dev) o sirviendo el `dist/` desde el backend en producción.

## Estructura del proyecto

```
complemento360/
├── backend/
│   ├── main.py              # Endpoints FastAPI
│   ├── auth.py              # JWT y bcrypt
│   ├── database.py          # Modelos SQLAlchemy + init DB
│   ├── email_service.py     # Envío SMTP y HTML del correo
│   ├── report_generator.py  # Generación Excel y PDF
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.vue          # Shell principal + auth
│   │   ├── Dashboard.vue    # Vista de reportes y gráficos
│   │   ├── Login.vue        # Formulario de login
│   │   └── style.scss
│   └── package.json
├── reportes_mensuales/      # CSVs fuente (no versionados)
└── docker-compose.yml       # PostgreSQL
```

## Documentación adicional

- [Arquitectura](docs/arquitectura.md)
- [API Reference](docs/api.md)
- [Configuración y variables de entorno](docs/configuracion.md)
- [Guía de desarrollo](docs/desarrollo.md)
