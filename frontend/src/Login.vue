<template>
  <div class="login-wrap">
    <div class="card login-card z-depth-4">
      <div class="login-logo-img">
        <img :src="logo" alt="Complemento 360" />
      </div>
      <h5>Complemento 360</h5>
      <p class="subtitle">Reportes mensuales de horas</p>

      <form @submit.prevent="submit">
        <div class="input-field">
          <i class="material-icons prefix" style="color:#0d47a1">person</i>
          <input id="username" v-model="username" type="text" autocomplete="username" required />
          <label for="username">Usuario</label>
        </div>
        <div class="input-field">
          <i class="material-icons prefix" style="color:#0d47a1">lock</i>
          <input id="password" v-model="password" type="password" autocomplete="current-password" required />
          <label for="password">Contraseña</label>
        </div>

        <div v-if="error" class="login-error">{{ error }}</div>

        <button type="submit" class="btn waves-effect waves-light" :disabled="loading">
          <i class="material-icons left">login</i>
          {{ loading ? 'Ingresando…' : 'Ingresar' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import M from 'materialize-css'
import logo from '../image/complemento360_logo.jpeg'

const emit = defineEmits(['login'])
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

onMounted(() => M.AutoInit())

async function submit() {
  error.value = ''
  loading.value = true
  try {
    const form = new URLSearchParams()
    form.append('username', username.value)
    form.append('password', password.value)
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form,
    })
    if (!res.ok) { error.value = (await res.json()).detail || 'Error al ingresar'; return }
    const { access_token } = await res.json()
    localStorage.setItem('token', access_token)
    emit('login', access_token)
  } catch { error.value = 'No se pudo conectar con el servidor' }
  finally { loading.value = false }
}
</script>
