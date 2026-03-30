# API Reference

Base URL: `http://localhost:8000`

Todos los endpoints (excepto login) requieren header:
```
Authorization: Bearer <token>
```

---

## Autenticación

### `POST /api/auth/login`

Obtiene un token JWT.

**Body** (`application/x-www-form-urlencoded`):
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `username` | string | Usuario configurado en `.env` |
| `password` | string | Contraseña configurada en `.env` |

**Respuesta 200:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

**Respuesta 401:** Usuario o contraseña incorrectos.

---

## Reportes

### `GET /api/reports`

Lista todos los reportes disponibles (CSVs en disco + meses en base de datos).

**Respuesta 200:**
```json
[
  {
    "filename": "marzo-2026.csv",
    "month": "2026-03",
    "label": "Marzo 2026",
    "in_db": true
  },
  {
    "filename": "febrero-2026.csv",
    "month": "2026-02",
    "label": "Febrero 2026",
    "in_db": false
  }
]
```

`in_db: false` indica que el CSV existe pero aún no fue importado.

---

### `POST /api/reports/{filename}/import`

Importa un CSV a la base de datos. Si ya existían registros para ese mes, los reemplaza.

**Path param:** `filename` — nombre del archivo CSV (ej. `marzo-2026.csv`).

**Respuesta 200:**
```json
{
  "imported": 142,
  "month": "2026-03"
}
```

**Errores:**
- `400` — nombre de archivo inválido (no `.csv` o contiene `/`)
- `404` — archivo no encontrado en `reportes_mensuales/`

---

### `GET /api/reports/{month}/data`

Obtiene los registros y resumen de un mes.

**Path param:** `month` — formato `YYYY-MM` (ej. `2026-03`).

**Query params opcionales:**
| Param | Tipo | Descripción |
|-------|------|-------------|
| `date_from` | string | Fecha desde `YYYY-MM-DD` |
| `date_to` | string | Fecha hasta `YYYY-MM-DD` |

**Respuesta 200:**
```json
{
  "month": "2026-03",
  "rows": [ { "date": "2026-03-02", "minutes": 120, "work_item_title": "...", ... } ],
  "summary": {
    "total_minutes": 8640,
    "total_hours": 144.0,
    "by_type": [ { "type": "Development", "minutes": 5000 } ],
    "by_work_item": [ { "title": "Feature X", "minutes": 1200 } ],
    "by_week": [ { "week": "W10", "minutes": 2400 } ]
  }
}
```

**Error 404:** Mes no encontrado en la base de datos.

---

## Entradas por rango

### `GET /api/entries`

Consulta registros cruzando cualquier rango de fechas, sin importar los límites de mes.

**Query params requeridos:**
| Param | Tipo | Descripción |
|-------|------|-------------|
| `date_from` | string | Fecha desde `YYYY-MM-DD` |
| `date_to` | string | Fecha hasta `YYYY-MM-DD` |

**Respuesta 200:** Mismo schema que `/api/reports/{month}/data`.

---

## Email

### `POST /api/email/send`

Genera Excel y PDF del rango indicado y los envía por correo.

**Body** (`application/json`):
```json
{
  "date_from": "2026-03-01",
  "date_to": "2026-03-31",
  "extra_recipients": ["jefe@empresa.com", "otro@empresa.com"],
  "subject": "Reporte de horas — Marzo 2026",
  "message": "Texto libre que aparece al inicio del correo."
}
```

| Campo | Requerido | Descripción |
|-------|-----------|-------------|
| `date_from` | Sí | Inicio del período |
| `date_to` | Sí | Fin del período |
| `extra_recipients` | No | Lista de destinatarios |
| `subject` | No | Asunto; si se omite se genera automáticamente |
| `message` | No | Mensaje personal que aparece en el cuerpo del correo |

**Respuesta 200:**
```json
{
  "sent_to": ["jefe@empresa.com"],
  "total_rows": 142
}
```

**Errores:**
- `400` — falta `date_from` o `date_to`
- `404` — sin datos en ese rango
- `500` — error SMTP (credenciales no configuradas, etc.)
