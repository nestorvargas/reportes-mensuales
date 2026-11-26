// Enrutador mínimo basado en la History API (sin dependencias).
// Rutas de la app:
//   /mes/2026-11                         → Reportes · por mes (mes calendario)
//   /cuenta-cobro/2026-11                → Reportes · por cuenta de cobro (ciclo 25 al 24)
//   /rango?desde=2026-11-01&hasta=…      → Reportes · por rango de fechas
//   /importar, /historial                → otras vistas
// Vite (dev y preview) responde index.html para cualquier ruta, así que recargar funciona.
import { reactive } from 'vue'

function readLocation() {
  return {
    path: location.pathname,
    query: Object.fromEntries(new URLSearchParams(location.search)),
  }
}

export const route = reactive(readLocation())

window.addEventListener('popstate', () => Object.assign(route, readLocation()))

/** Segmentos de la ruta actual: '/mes/2026-11' → ['mes', '2026-11'] */
export function segments() {
  return route.path.split('/').filter(Boolean)
}

/**
 * Cambia la URL y actualiza `route`. Devuelve false si ya estaba en esa URL.
 * replace=true reemplaza la entrada del historial (para redirecciones, no para clics).
 */
export function navigate(path, query = {}, replace = false) {
  const qs = new URLSearchParams(Object.entries(query).filter(([, v]) => v)).toString()
  const url = path + (qs ? `?${qs}` : '')
  if (url === location.pathname + location.search) return false
  history[replace ? 'replaceState' : 'pushState']({}, '', url)
  Object.assign(route, readLocation())
  return true
}
