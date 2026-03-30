<template>
  <Login v-if="!token" @login="onLogin" />

  <div v-else>
    <nav class="app-nav z-depth-2">
      <div class="nav-wrapper container">
        <span class="brand-logo left" style="display:flex;align-items:center;gap:10px;height:100%">
          <img :src="logo" alt="C360" style="height:40px;width:40px;object-fit:contain;border-radius:6px;background:#fff;padding:2px" />
          <span style="font-size:1.1rem;font-weight:700">Complemento 360</span>
          <span class="nav-badge">Reportes</span>
        </span>
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
      <Dashboard :reports="reports" :token="token" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Login from './Login.vue'
import Dashboard from './Dashboard.vue'
import logo from '../image/complemento360_logo.jpeg'

const token = ref(localStorage.getItem('token') || '')
const reports = ref([])

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
