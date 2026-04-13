<template>
  <div class="importar-wrap">
    <div class="card z-depth-1" style="border-radius:10px">
      <div class="card-content">
        <div class="table-toolbar">
          <h6><i class="material-icons" style="vertical-align:middle;margin-right:6px;font-size:18px">folder_open</i> Archivos en reportes_mensuales</h6>
          <a class="btn btn-outline btn-small waves-effect" @click="fetchReports">
            <i class="material-icons left">refresh</i>Actualizar
          </a>
        </div>

        <div v-if="loading" class="loading-wrap" style="padding:32px 0">
          <div class="preloader-wrapper active small">
            <div class="spinner-layer spinner-blue-only">
              <div class="circle-clipper left"><div class="circle"></div></div>
              <div class="gap-patch"><div class="circle"></div></div>
              <div class="circle-clipper right"><div class="circle"></div></div>
            </div>
          </div>
        </div>

        <div v-else-if="!reports.length" class="empty-state" style="padding:32px 0">
          <i class="material-icons">inbox</i>
          <p>No hay archivos CSV en reportes_mensuales</p>
        </div>

        <table v-else class="summary-table" style="margin-top:12px">
          <thead>
            <tr>
              <th>Archivo</th>
              <th>Período</th>
              <th style="text-align:center">Estado</th>
              <th style="text-align:right">Acción</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in csvReports" :key="r.filename">
              <td style="font-family:monospace;font-size:.85rem">{{ r.filename }}</td>
              <td>{{ r.label }}</td>
              <td style="text-align:center">
                <span class="tag-chip" :class="r.in_db ? 'dev' : 'default'">
                  <i class="material-icons tiny" style="vertical-align:middle;margin-right:2px">
                    {{ r.in_db ? 'check_circle' : 'radio_button_unchecked' }}
                  </i>
                  {{ r.in_db ? 'Importado' : 'Sin importar' }}
                </span>
              </td>
              <td style="text-align:right">
                <a
                  class="btn btn-small waves-effect waves-light"
                  :class="[r.in_db ? 'btn-outline' : 'btn-primary', { disabled: !!importing }]"
                  @click="!importing && importReport(r)"
                >
                  <i class="material-icons left">{{ r.in_db ? 'sync' : 'upload' }}</i>
                  {{ importing === r.filename ? 'Importando…' : (r.in_db ? 'Re-importar' : 'Importar') }}
                </a>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="successMsg" class="import-success" style="margin-top:16px">
          <i class="material-icons">check_circle</i> {{ successMsg }}
        </div>
        <div v-if="errorMsg" class="import-error" style="margin-top:16px">
          <i class="material-icons">error</i> {{ errorMsg }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({ token: String })
const emit = defineEmits(['imported'])

const reports  = ref([])
const loading  = ref(false)
const importing = ref(null)
const successMsg = ref('')
const errorMsg   = ref('')

const csvReports = computed(() => reports.value.filter(r => r.filename))

onMounted(fetchReports)

function headers() { return { Authorization: `Bearer ${props.token}` } }

async function fetchReports() {
  loading.value = true
  successMsg.value = ''
  errorMsg.value = ''
  const res = await fetch('/api/reports', { headers: headers() })
  reports.value = await res.json()
  loading.value = false
}

async function importReport(r) {
  if (importing.value) return
  importing.value = r.filename
  successMsg.value = ''
  errorMsg.value = ''
  try {
    const res = await fetch(`/api/reports/${r.filename}/import`, {
      method: 'POST',
      headers: headers(),
    })
    const d = await res.json()
    if (!res.ok) { errorMsg.value = d.detail; return }
    successMsg.value = `✓ ${r.label} importado — ${d.imported} registros`
    emit('imported')
    await fetchReports()
  } catch {
    errorMsg.value = 'Error al conectar con el servidor'
  } finally {
    importing.value = null
  }
}
</script>
