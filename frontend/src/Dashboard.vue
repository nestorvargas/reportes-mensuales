<template>
  <div>
    <!-- ── Mode tabs ── -->
    <div class="mode-tabs" style="margin-bottom:20px">
      <ul class="tabs z-depth-1" ref="tabsEl" style="border-radius:8px">
        <li class="tab col s6"><a href="#tab-mes" class="active">
          <i class="material-icons">calendar_month</i>Por mes
        </a></li>
        <li class="tab col s6"><a href="#tab-rango">
          <i class="material-icons">date_range</i>Por rango de fechas
        </a></li>
      </ul>
    </div>

    <!-- ── Tab: Por mes ── -->
    <div id="tab-mes">
      <div class="card controls-card z-depth-1" style="margin-bottom:20px">
        <div class="card-content">
          <div class="month-chips">
            <span
              v-for="r in reports" :key="r.month"
              class="chip" :class="{ active: selectedMonth === r.month, disabled: !r.in_db }"
              @click="r.in_db && loadMonth(r.month)"
            >
              <i class="material-icons tiny" style="margin-right:4px;vertical-align:middle">{{ r.in_db ? 'storage' : 'cloud_off' }}</i>
              {{ r.label }}
              <span v-if="!r.in_db" class="badge">sin importar</span>
            </span>
          </div>
        </div>
      </div>

      <!-- Import banner -->
      <div v-if="selectedReport && !selectedReport.in_db" class="import-banner z-depth-1">
        <i class="material-icons">warning</i>
        <p><strong>{{ selectedReport.label }}</strong> no está en la base de datos.</p>
        <a class="btn btn-danger waves-effect waves-light btn-small" :class="{ disabled: importing }" @click="importReport">
          <i class="material-icons left">upload</i>{{ importing ? 'Importando…' : 'Importar' }}
        </a>
      </div>
    </div>

    <!-- ── Tab: Por rango ── -->
    <div id="tab-rango">
      <div class="card controls-card z-depth-1" style="margin-bottom:20px">
        <div class="card-content">
          <div class="range-form">
            <div class="range-field">
              <label>Desde</label>
              <input type="date" v-model="dateFrom" />
            </div>
            <div class="range-field">
              <label>Hasta</label>
              <input type="date" v-model="dateTo" />
            </div>
            <div class="range-actions">
              <a class="btn btn-primary waves-effect waves-light" :class="{ disabled: !dateFrom || !dateTo || loading }" @click="loadRange">
                <i class="material-icons left">search</i>Aplicar
              </a>
              <a v-if="data && activeMode==='rango'" class="btn btn-danger waves-effect waves-light" @click="openEmailModal">
                <i class="material-icons left">email</i>Enviar por correo
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Loading ── -->
    <div v-if="loading" class="loading-wrap">
      <div class="preloader-wrapper active">
        <div class="spinner-layer spinner-blue-only">
          <div class="circle-clipper left"><div class="circle"></div></div>
          <div class="gap-patch"><div class="circle"></div></div>
          <div class="circle-clipper right"><div class="circle"></div></div>
        </div>
      </div>
      <span>Cargando reporte…</span>
    </div>

    <!-- ── Data ── -->
    <template v-else-if="data">

      <!-- KPI row -->
      <div class="row" style="margin-top:20px">
        <div class="col s6 m4 l2" v-for="kpi in kpis" :key="kpi.label">
          <div class="card kpi-card z-depth-1">
            <div class="card-content">
              <div class="kpi-icon"><i class="material-icons">{{ kpi.icon }}</i></div>
              <div class="kpi-val">{{ kpi.value }}</div>
              <div class="kpi-label">{{ kpi.label }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Charts row 1 -->
      <div class="row">
        <div class="col s12 m6">
          <div class="card chart-card z-depth-1">
            <div class="card-content">
              <div class="chart-title"><i class="material-icons">bar_chart</i> Horas por semana</div>
              <canvas ref="weekChart"></canvas>
            </div>
          </div>
        </div>
        <div class="col s12 m6">
          <div class="card chart-card z-depth-1">
            <div class="card-content">
              <div class="chart-title"><i class="material-icons">donut_large</i> Distribución por tipo</div>
              <canvas ref="typeChart"></canvas>
            </div>
          </div>
        </div>
      </div>

      <!-- Charts row 2 -->
      <div class="row">
        <div class="col s12 m6">
          <div class="card chart-card wide z-depth-1">
            <div class="card-content">
              <div class="chart-title"><i class="material-icons">horizontal_rule</i> Top Work Items</div>
              <canvas ref="itemChart"></canvas>
            </div>
          </div>
        </div>
        <div class="col s12 m6">
          <div class="card chart-card wide z-depth-1">
            <div class="card-content">
              <div class="chart-title"><i class="material-icons">today</i> Horas por día</div>
              <canvas ref="dayChart"></canvas>
            </div>
          </div>
        </div>
      </div>

      <!-- Breakdown tables -->
      <div class="row">
        <div class="col s12 m6">
          <div class="card z-depth-1" style="border-radius:10px">
            <div class="card-content" style="padding:16px 20px">
              <div class="chart-title"><i class="material-icons">label</i> Por tipo</div>
              <table class="summary-table">
                <thead><tr><th>Tipo</th><th>Tiempo</th><th style="width:160px">Dist.</th></tr></thead>
                <tbody>
                  <tr v-for="t in data.summary.by_type" :key="t.type">
                    <td>{{ t.type }}</td>
                    <td class="hours-val">{{ toHHMM(t.minutes) }}</td>
                    <td><div class="bar-wrap"><div class="bar-fill" :style="{width: pct(t.minutes, data.summary.total_minutes)+'%'}"></div></div></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
        <div class="col s12 m6">
          <div class="card z-depth-1" style="border-radius:10px">
            <div class="card-content" style="padding:16px 20px">
              <div class="chart-title"><i class="material-icons">view_week</i> Por semana</div>
              <table class="summary-table">
                <thead><tr><th>Semana</th><th>Tiempo</th><th style="width:160px">Dist.</th></tr></thead>
                <tbody>
                  <tr v-for="w in data.summary.by_week" :key="w.week">
                    <td>{{ w.week }}</td>
                    <td class="hours-val">{{ toHHMM(w.minutes) }}</td>
                    <td><div class="bar-wrap"><div class="bar-fill" :style="{width: pct(w.minutes, data.summary.total_minutes)+'%'}"></div></div></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <!-- Detail table -->
      <div class="card table-card z-depth-1">
        <div class="table-toolbar">
          <h6><i class="material-icons" style="vertical-align:middle;margin-right:6px;font-size:18px">list_alt</i> Detalle de registros</h6>
          <div class="table-search">
            <i class="material-icons">search</i>
            <input v-model="search" type="text" placeholder="Buscar…" />
          </div>
        </div>
        <div style="overflow-x:auto">
          <table class="summary-table" style="margin:0">
            <thead>
              <tr>
                <th>Fecha</th><th>Semana</th><th>Work Item</th>
                <th>Tipo</th><th>Comentario</th><th>Tiempo</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in filteredRows" :key="i">
                <td style="white-space:nowrap">{{ row.date }}</td>
                <td style="white-space:nowrap">{{ row.week }}</td>
                <td>{{ row.work_item_title }}</td>
                <td><span class="tag-chip" :class="typeClass(row.type)">{{ row.type }}</span></td>
                <td>{{ row.comment }}</td>
                <td class="hours-val" style="white-space:nowrap">{{ toHHMM(row.minutes) }}</td>
              </tr>
              <tr v-if="!filteredRows.length">
                <td colspan="6" style="text-align:center;color:#b0bec5;padding:24px">Sin resultados</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </template>

    <!-- Empty state -->
    <div v-else-if="!loading" class="empty-state">
      <i class="material-icons">insert_chart_outlined</i>
      <p>Selecciona un mes o aplica un rango de fechas</p>
    </div>

    <!-- ── Email modal ── -->
    <div id="emailModal" class="modal email-modal" ref="modalEl">
      <div class="modal-content">
        <div class="modal-head">
          <h5><i class="material-icons left" style="font-size:20px;vertical-align:middle">email</i> Enviar reporte por correo</h5>
          <a class="btn-flat waves-effect modal-close"><i class="material-icons">close</i></a>
        </div>
        <div class="modal-body-inner">
          <p class="modal-period">Período: <strong>{{ dateFrom }}</strong> al <strong>{{ dateTo }}</strong></p>

          <div class="modal-field">
            <label>Asunto</label>
            <input type="text" v-model="emailSubject" placeholder="Asunto del correo" />
          </div>

          <div class="modal-field">
            <label>Mensaje para el jefe</label>
            <textarea v-model="emailMessage" rows="4" placeholder="Escribe aquí tu mensaje personal…"></textarea>
          </div>

          <div class="modal-field">
            <label>Destinatarios</label>
            <div class="recipient-chips">
              <div
                v-for="(r, i) in allRecipients" :key="r"
                class="chip" @click="allRecipients.splice(i,1)"
                title="Click para eliminar"
              >{{ r }}<i class="material-icons tiny" style="margin-left:4px">close</i></div>
              <span v-if="!allRecipients.length" style="color:#b0bec5;font-size:.82rem">Sin destinatarios</span>
            </div>
            <div class="modal-add-row">
              <input type="email" v-model="extraEmail" placeholder="correo@ejemplo.com" @keyup.enter="addRecipient" />
              <a class="btn btn-primary btn-small waves-effect waves-light" @click="addRecipient">
                <i class="material-icons">add</i>
              </a>
            </div>
            <p v-if="!allRecipients.length" class="modal-hint">Agrega al menos un destinatario</p>
          </div>

          <div v-if="emailError" class="modal-error">{{ emailError }}</div>
          <div v-if="emailSuccess" class="modal-success">{{ emailSuccess }}</div>
        </div>
      </div>
      <div class="modal-foot">
        <a class="btn btn-outline waves-effect modal-close">Cancelar</a>
        <a class="btn btn-primary waves-effect waves-light" :class="{ disabled: sending }" @click="sendEmail">
          <i class="material-icons left">send</i>{{ sending ? 'Enviando…' : 'Enviar correo' }}
        </a>
      </div>
    </div>
    <div v-if="emailModal" class="modal-overlay" style="display:block;opacity:.5;z-index:999"></div>

  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import M from 'materialize-css'
import {
  Chart, BarController, BarElement, DoughnutController, ArcElement,
  CategoryScale, LinearScale, Tooltip, Legend,
} from 'chart.js'

Chart.register(BarController, BarElement, DoughnutController, ArcElement, CategoryScale, LinearScale, Tooltip, Legend)

const props = defineProps({ reports: Array, token: String })

// ── Refs ──
const tabsEl   = ref(null)
const modalEl  = ref(null)
const weekChart = ref(null)
const typeChart = ref(null)
const itemChart = ref(null)
const dayChart  = ref(null)
let   charts    = []
let   mModal    = null
let   mTabs     = null

// ── State ──
const activeMode     = ref('mes')
const selectedMonth  = ref(null)
const selectedReport = ref(null)
const dateFrom       = ref('')
const dateTo         = ref('')
const data           = ref(null)
const loading        = ref(false)
const importing      = ref(false)
const search         = ref('')

// ── Email ──
const emailModal    = ref(false)
const allRecipients = ref([])
const extraEmail    = ref('')
const emailSubject  = ref('')
const emailMessage  = ref('')
const sending       = ref(false)
const emailError    = ref('')
const emailSuccess  = ref('')

onMounted(() => {
  mTabs  = M.Tabs.init(tabsEl.value, {
    onShow: (el) => { activeMode.value = el.id === 'tab-mes' ? 'mes' : 'rango' }
  })
  mModal = M.Modal.init(modalEl.value, { dismissible: true })
})

// ── Auto-load first month ──
watch(() => props.reports, (val) => {
  if (val?.length && activeMode.value === 'mes') {
    const first = val.find(r => r.in_db)
    if (first) loadMonth(first.month)
  }
}, { immediate: true })

function authHeaders() { return { Authorization: `Bearer ${props.token}` } }

async function loadMonth(month) {
  selectedMonth.value = month
  selectedReport.value = props.reports.find(r => r.month === month) || null
  if (!selectedReport.value?.in_db) { data.value = null; return }
  loading.value = true; data.value = null; destroyCharts()
  const res = await fetch(`/api/reports/${month}/data`, { headers: authHeaders() })
  data.value = await res.json()
  loading.value = false
  await nextTick(); renderCharts()
}

async function loadRange() {
  if (!dateFrom.value || !dateTo.value) return
  loading.value = true; data.value = null; destroyCharts()
  const res = await fetch(`/api/entries?date_from=${dateFrom.value}&date_to=${dateTo.value}`, { headers: authHeaders() })
  data.value = await res.json()
  loading.value = false
  await nextTick(); renderCharts()
}

async function importReport() {
  if (!selectedReport.value?.filename) return
  importing.value = true
  await fetch(`/api/reports/${selectedReport.value.filename}/import`, { method: 'POST', headers: authHeaders() })
  importing.value = false
  // Refresh
  const res = await fetch('/api/reports', { headers: authHeaders() })
  const updated = await res.json()
  props.reports.splice(0, props.reports.length, ...updated)
  await loadMonth(selectedMonth.value)
}

// ── KPIs ──
const uniqueDays = computed(() => data.value ? new Set(data.value.rows.map(r => r.date)).size : 0)
const kpis = computed(() => {
  if (!data.value) return []
  const s = data.value.summary
  return [
    { icon: 'schedule',      label: 'Total horas',     value: toHHMM(s.total_minutes) },
    { icon: 'receipt_long',  label: 'Registros',       value: data.value.rows.length },
    { icon: 'view_week',     label: 'Semanas',          value: s.by_week.length },
    { icon: 'task',          label: 'Work Items',       value: s.by_work_item.length },
    { icon: 'today',         label: 'Días trabajados',  value: uniqueDays.value },
    { icon: 'avg_pace',      label: 'Promedio/día',     value: uniqueDays.value ? toHHMM(Math.round(s.total_minutes / uniqueDays.value)) : '0:00' },
  ]
})

const filteredRows = computed(() => {
  if (!data.value) return []
  const q = search.value.toLowerCase()
  return q ? data.value.rows.filter(r =>
    r.work_item_title.toLowerCase().includes(q) ||
    r.comment.toLowerCase().includes(q) ||
    r.type.toLowerCase().includes(q)
  ) : data.value.rows
})

// ── Charts ──
const PALETTE = ['#E8752A','#6D6E71','#D4631A','#9E9E9E','#F0A060','#4A4A4A','#F5C49A','#8A8A8A','#C85E1A','#B0B0B0']

function destroyCharts() { charts.forEach(c => c.destroy()); charts = [] }

function renderCharts() {
  if (!data.value) return
  const s = data.value.summary

  charts.push(new Chart(weekChart.value, {
    type: 'bar',
    data: { labels: s.by_week.map(w => w.week), datasets: [{ data: s.by_week.map(w => +(w.minutes/60).toFixed(2)), backgroundColor: '#0d47a1', borderRadius: 5 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => toHHMM(s.by_week[ctx.dataIndex].minutes) } } }, scales: { y: { beginAtZero: true, ticks: { callback: v => `${v}h` } } } },
  }))

  charts.push(new Chart(typeChart.value, {
    type: 'doughnut',
    data: { labels: s.by_type.map(t => t.type), datasets: [{ data: s.by_type.map(t => +(t.minutes/60).toFixed(2)), backgroundColor: PALETTE, borderWidth: 2 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { font: { size: 10 }, boxWidth: 12 } }, tooltip: { callbacks: { label: ctx => ` ${toHHMM(s.by_type[ctx.dataIndex].minutes)}` } } }, cutout: '60%' },
  }))

  const topItems = s.by_work_item.slice(0, 10)
  charts.push(new Chart(itemChart.value, {
    type: 'bar',
    data: { labels: topItems.map(w => w.title.length > 45 ? w.title.slice(0,45)+'…' : w.title), datasets: [{ data: topItems.map(w => +(w.minutes/60).toFixed(2)), backgroundColor: topItems.map((_,i) => PALETTE[i%PALETTE.length]), borderRadius: 4 }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => toHHMM(topItems[ctx.dataIndex].minutes) } } }, scales: { x: { beginAtZero: true, ticks: { callback: v => `${v}h` } } } },
  }))

  const byDay = {}
  data.value.rows.forEach(r => { byDay[r.date] = (byDay[r.date]||0) + r.minutes })
  const days = Object.keys(byDay).sort()
  charts.push(new Chart(dayChart.value, {
    type: 'bar',
    data: { labels: days, datasets: [{ data: days.map(d => +(byDay[d]/60).toFixed(2)), backgroundColor: days.map(d => byDay[d]>=480?'#2e7d32':byDay[d]>=240?'#0d47a1':'#e53935'), borderRadius: 4 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => toHHMM(byDay[days[ctx.dataIndex]]) } } }, scales: { y: { beginAtZero: true, ticks: { callback: v => `${v}h` } } } },
  }))
}

// ── Email ──
function openEmailModal() {
  emailError.value = ''; emailSuccess.value = ''; extraEmail.value = ''
  allRecipients.value = []
  emailSubject.value = `Reporte de horas Complemento 360 · ${dateFrom.value} al ${dateTo.value}`
  emailMessage.value = ''
  mModal.open()
}

function addRecipient() {
  const e = extraEmail.value.trim()
  if (e && !allRecipients.value.includes(e)) allRecipients.value.push(e)
  extraEmail.value = ''
}

async function sendEmail() {
  if (!allRecipients.value.length) { emailError.value = 'Agrega al menos un destinatario'; return }
  emailError.value = ''; emailSuccess.value = ''; sending.value = true
  try {
    const res = await fetch('/api/email/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ date_from: dateFrom.value, date_to: dateTo.value, extra_recipients: allRecipients.value, subject: emailSubject.value, message: emailMessage.value }),
    })
    const d = await res.json()
    if (!res.ok) { emailError.value = d.detail; return }
    emailSuccess.value = `✓ Correo enviado a ${d.sent_to.join(', ')}`
  } catch { emailError.value = 'Error al conectar' }
  finally { sending.value = false }
}

// ── Helpers ──
function toHHMM(min) { const h=Math.floor(min/60),m=min%60; return `${h}:${String(m).padStart(2,'0')}` }
function pct(v, t) { return t ? Math.round(v/t*100) : 0 }
function typeClass(type) {
  const t = (type||'').toLowerCase()
  if (t.includes('admin')) return 'admin'
  if (t.includes('dev')||t.includes('conc')) return 'dev'
  if (t.includes('est')) return 'est'
  return 'default'
}
</script>
