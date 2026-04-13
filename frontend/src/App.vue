<template>
  <Login v-if="!token" @login="onLogin" />

  <div v-else>
    <nav class="app-nav z-depth-2">
      <div class="nav-wrapper container">
        <span class="brand-logo left" style="display:flex;align-items:center;gap:10px;height:100%">
          <img :src="logo" alt="C360" style="height:40px;width:40px;object-fit:contain;border-radius:6px;background:#fff;padding:2px" />
          <span style="font-size:1.1rem;font-weight:700">Complemento 360</span>
        </span>
        <ul class="nav-tabs">
          <li :class="{ active: view === 'dashboard' }" @click="view = 'dashboard'">
            <i class="material-icons">bar_chart</i> Reportes
          </li>
          <li :class="{ active: view === 'importar' }" @click="view = 'importar'">
            <i class="material-icons">upload_file</i> Importar
          </li>
          <li :class="{ active: view === 'logs' }" @click="view = 'logs'">
            <i class="material-icons">history</i> Historial
          </li>
        </ul>
        <ul class="right">
          <li>
            <a class="btn-flat waves-effect" @click="logout">
              <i class="material-icons left">logout</i>Salir
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
import { ref, onMounted } from 'vue'
import Login from './Login.vue'
import Dashboard from './Dashboard.vue'
import Importar from './Importar.vue'
import Logs from './Logs.vue'
import logo from '../image/complemento360_logo.jpeg'

const token   = ref(localStorage.getItem('token') || '')
const reports = ref([])
const view    = ref('dashboard')

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
