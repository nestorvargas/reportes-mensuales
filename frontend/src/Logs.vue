<template>
  <div>
    <div v-if="loading" class="loading-wrap">
      <div class="preloader-wrapper active">
        <div class="spinner-layer spinner-blue-only">
          <div class="circle-clipper left"><div class="circle"></div></div>
          <div class="gap-patch"><div class="circle"></div></div>
          <div class="circle-clipper right"><div class="circle"></div></div>
        </div>
      </div>
      <span>Cargando historial…</span>
    </div>

    <template v-else>
      <div class="logs-header">
        <div class="logs-stat">
          <span class="stat-val">{{ logs.length }}</span>
          <span class="stat-lbl">envíos totales</span>
        </div>
        <div class="logs-stat">
          <span class="stat-val success-val">{{ successCount }}</span>
          <span class="stat-lbl">exitosos</span>
        </div>
        <div class="logs-stat">
          <span class="stat-val error-val">{{ errorCount }}</span>
          <span class="stat-lbl">con error</span>
        </div>
      </div>

      <div v-if="!logs.length" class="empty-state">
        <i class="material-icons">mark_email_unread</i>
        <p>Todavía no se enviaron correos</p>
      </div>

      <div v-else class="card table-card z-depth-1">
        <div class="table-toolbar">
          <h6>
            <i class="material-icons" style="vertical-align:middle;margin-right:6px;font-size:18px">history</i>
            Historial de correos enviados
          </h6>
          <div class="table-search">
            <i class="material-icons">search</i>
            <input v-model="search" type="text" placeholder="Buscar…" />
          </div>
        </div>
        <div style="overflow-x:auto">
          <table class="summary-table" style="margin:0">
            <thead>
              <tr>
                <th>Fecha y hora</th>
                <th>Período</th>
                <th>Asunto</th>
                <th>Destinatarios</th>
                <th style="text-align:center">Registros</th>
                <th style="text-align:center">Estado</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="log in filteredLogs" :key="log.id">
                <tr :class="{ 'row-error': log.status === 'error' }">
                  <td style="white-space:nowrap">{{ formatDate(log.sent_at) }}</td>
                  <td style="white-space:nowrap">{{ log.date_from }} → {{ log.date_to }}</td>
                  <td>{{ log.subject }}</td>
                  <td>
                    <div class="recipient-list">
                      <span v-for="r in log.recipients" :key="r" class="chip small-chip">{{ r }}</span>
                      <span v-if="!log.recipients.length" style="color:#b0bec5">—</span>
                    </div>
                  </td>
                  <td style="text-align:center">{{ log.total_rows }}</td>
                  <td style="text-align:center">
                    <span class="status-chip" :class="log.status">
                      <i class="material-icons tiny">{{ log.status === 'success' ? 'check_circle' : 'error' }}</i>
                      {{ log.status === 'success' ? 'Enviado' : 'Error' }}
                    </span>
                  </td>
                </tr>
                <tr v-if="log.status === 'error' && log.error" class="error-detail-row">
                  <td colspan="6">
                    <div class="error-msg">
                      <i class="material-icons tiny">warning</i> {{ log.error }}
                    </div>
                  </td>
                </tr>
              </template>
              <tr v-if="!filteredLogs.length">
                <td colspan="6" style="text-align:center;color:#b0bec5;padding:24px">Sin resultados</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({ token: String })

const logs    = ref([])
const loading = ref(true)
const search  = ref('')

onMounted(async () => {
  const res = await fetch('/api/logs', {
    headers: { Authorization: `Bearer ${props.token}` },
  })
  logs.value = await res.json()
  loading.value = false
})

const successCount = computed(() => logs.value.filter(l => l.status === 'success').length)
const errorCount   = computed(() => logs.value.filter(l => l.status === 'error').length)

const filteredLogs = computed(() => {
  const q = search.value.toLowerCase()
  if (!q) return logs.value
  return logs.value.filter(l =>
    l.subject.toLowerCase().includes(q) ||
    l.recipients.some(r => r.toLowerCase().includes(q)) ||
    l.date_from.includes(q) ||
    l.date_to.includes(q)
  )
})

function formatDate(iso) {
  const d = new Date(iso)
  return d.toLocaleString('es-CL', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}
</script>

<style scoped>
.logs-header {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}
.logs-stat {
  background: #fff;
  border-radius: 10px;
  padding: 16px 24px;
  box-shadow: 0 1px 6px rgba(0,0,0,.08);
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 110px;
}
.stat-val {
  font-size: 1.8rem;
  font-weight: 800;
  color: #0f3460;
}
.success-val { color: #2e7d32; }
.error-val   { color: #c62828; }
.stat-lbl {
  font-size: 0.72rem;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: .04em;
  margin-top: 2px;
}
.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
}
.status-chip.success { background: #e8f5e9; color: #2e7d32; }
.status-chip.error   { background: #ffebee; color: #c62828; }
.row-error td { background: #fff8f8; }
.error-detail-row td { padding: 0 !important; }
.error-msg {
  background: #ffebee;
  color: #c62828;
  font-size: 0.8rem;
  padding: 6px 16px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.recipient-list { display: flex; flex-wrap: wrap; gap: 4px; }
.small-chip {
  font-size: 0.72rem !important;
  height: 22px !important;
  line-height: 22px !important;
  padding: 0 8px !important;
  background: #e3f2fd;
  color: #0d47a1;
  border-radius: 11px;
}
</style>
