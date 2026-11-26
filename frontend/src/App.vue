<template>
  <Login v-if="!token" @login="onLogin" />

  <div v-else>
    <nav class="app-nav z-depth-2">
      <div class="nav-wrapper container">
        <span class="brand-logo left" style="display:flex;align-items:center;gap:10px;height:100%">
          <img :src="logo" alt="C360" style="height:40px;width:40px;object-fit:contain;border-radius:6px;background:#fff;padding:2px" />
          <span class="brand-name" style="font-size:1.1rem;font-weight:700">Complemento 360</span>
        </span>
        <ul class="nav-tabs">
          <li :class="{ active: view === 'dashboard' }">
            <a href="/mes" @click="go($event, '/mes')"><i class="material-icons">bar_chart</i> <span class="tab-label">Reportes</span></a>
          </li>
          <li :class="{ active: view === 'importar' }">
            <a href="/importar" @click="go($event, '/importar')"><i class="material-icons">upload_file</i> <span class="tab-label">Importar</span></a>
          </li>
          <li :class="{ active: view === 'logs' }">
            <a href="/historial" @click="go($event, '/historial')"><i class="material-icons">history</i> <span class="tab-label">Historial</span></a>
          </li>
        </ul>
        <ul class="right">
          <li>
            <a class="btn-flat waves-effect" @click="logout">
              <i class="material-icons left">logout</i><span class="logout-label">Salir</span>
            </a>
          </li>
        </ul>
      </div>
    </nav>

    <div class="container dashboard-wrap">
      <Dashboard v-if="view === 'dashboard'" :reports="reports" :token="token" />
      <Importar  v-else-if="view === 'importar'" :token="token" @imported="fetchReports" />
      <Logs      v-else                           :token="token" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { route, segments, navigate } from './router.js'
import Login from './Login.vue'
import Dashboard from './Dashboard.vue'
import Importar from './Importar.vue'
import Logs from './Logs.vue'
import logo from '../image/complemento360_logo.jpeg'

const token   = ref(localStorage.getItem('token') || '')
const reports = ref([])
// Vista según la URL: /importar, /historial; cualquier otra ruta es Reportes
const view    = computed(() => ({ importar: 'importar', historial: 'logs' })[segments()[0]] || 'dashboard')

// Clic normal: navegar dentro de la app; Ctrl/Cmd + clic abre en otra pestaña
function go(e, path) {
  if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return
  e.preventDefault()
  navigate(path)
}

watch(view, v => {
  if (v === 'importar') document.title = 'Importar · Complemento 360'
  else if (v === 'logs') document.title = 'Historial · Complemento 360'
}, { immediate: true })

onMounted(() => { if (token.value) fetchReports() })

function onLogin(t) { token.value = t; fetchReports() }

function logout() {
  localStorage.removeItem('token')
  token.value = ''
  reports.value = []
}

async function fetchReports() {
  const res = await fetch('/api/reports', { headers: { Authorization: `Bearer ${token.value}` } })
  if (res.status === 401) { logout(); return }
  reports.value = await res.json()
}
</script>
