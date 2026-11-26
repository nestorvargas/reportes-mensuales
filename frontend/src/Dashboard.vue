<template>
  <div>
    <!-- ── Mode tabs ── -->
    <div class="mode-tabs" style="margin-bottom:20px">
      <ul class="tabs z-depth-1" ref="tabsEl" style="border-radius:8px">
        <li class="tab col s4"><a href="#tab-mes" class="active">
          <i class="material-icons">calendar_month</i>Por mes
        </a></li>
        <li class="tab col s4"><a href="#tab-cobro">
          <i class="material-icons">receipt_long</i>Por cuenta de cobro
        </a></li>
        <li class="tab col s4"><a href="#tab-rango">
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
              @click="r.in_db && navigate(`/mes/${r.month}`)"
            >
              <i class="material-icons tiny" style="margin-right:4px;vertical-align:middle">{{ r.in_db ? 'storage' : 'cloud_off' }}</i>
              {{ r.label }}
              <span v-if="!r.in_db" class="badge">sin importar</span>
            </span>
          </div>
          <div v-if="data && activeMode === 'mes'" class="mes-actions">
            <span class="muted period-label">
              <i class="material-icons tiny">event</i>
              Del {{ fmtDate(currentPeriod()[0]) }} al {{ fmtDate(currentPeriod()[1]) }}
            </span>
            <a class="btn btn-primary waves-effect waves-light" @click="downloadReporte">
              <i class="material-icons left">download</i>Descargar reporte
            </a>
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

    <!-- ── Tab: Por cuenta de cobro (ciclo del 25 al 24 por fecha) ── -->
    <div id="tab-cobro">
      <div class="card controls-card z-depth-1" style="margin-bottom:20px">
        <div class="card-content">
          <div class="month-chips">
            <span
              v-for="r in importedReports" :key="r.month"
              class="chip" :class="{ active: selectedCycle === r.month }"
              @click="navigate(`/cuenta-cobro/${r.month}`)"
            >
              <i class="material-icons tiny" style="margin-right:4px;vertical-align:middle">receipt_long</i>
              {{ r.label }}
              <span class="chip-sub">{{ fmtDate(cyclePeriod(r.month)[0]) }} – {{ fmtDate(cyclePeriod(r.month)[1]) }}</span>
            </span>
            <span v-if="!importedReports.length" class="muted">No hay meses importados.</span>
          </div>
          <div v-if="data && activeMode === 'cobro'" class="mes-actions">
            <span class="muted period-label">
              <i class="material-icons tiny">event</i>
              Ciclo del {{ fmtDate(currentPeriod()[0]) }} al {{ fmtDate(currentPeriod()[1]) }}
            </span>
            <a class="btn btn-outline waves-effect" @click="downloadCuentaCobro">
              <i class="material-icons left">download</i>Descargar cuenta de cobro
            </a>
            <a class="btn btn-outline waves-effect" @click="downloadDocumentoSoporte">
              <i class="material-icons left">description</i>Descargar documento soporte
            </a>
            <a class="btn btn-outline waves-effect" @click="openEmailModal('reporte')">
              <i class="material-icons left">email</i>Enviar reporte
            </a>
            <a class="btn btn-primary waves-effect waves-light" @click="openEmailModal('cobro')">
              <i class="material-icons left">send</i>Enviar cuenta de cobro
            </a>
          </div>
        </div>
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
              <a class="btn btn-primary waves-effect waves-light" :class="{ disabled: !dateFrom || !dateTo || loading }" @click="applyRange">
                <i class="material-icons left">search</i>Aplicar
              </a>
              <template v-if="data && activeMode==='rango'">
                <a class="btn btn-outline waves-effect" @click="downloadReporte">
                  <i class="material-icons left">download</i>Descargar reporte
                </a>
                <a class="btn btn-outline waves-effect" @click="openEmailModal('reporte')">
                  <i class="material-icons left">email</i>Enviar reporte
                </a>
              </template>
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
              <div class="type-dist">
                <div class="type-donut">
                  <canvas ref="typeChart"></canvas>
                  <div class="type-donut-center">
                    <strong>{{ toHHMM(data.summary.total_minutes) }}</strong>
                    <span>horas</span>
                  </div>
                </div>
                <ul class="type-legend">
                  <li v-for="(g, i) in typeGroups" :key="g.label" :title="g.label">
                    <span class="dot" :style="{ background: TYPE_COLORS[i] }"></span>
                    <span class="name">{{ g.label }}</span>
                    <span class="val">{{ toHHMM(g.minutes) }}</span>
                    <span class="pct">{{ pct(g.minutes, data.summary.total_minutes) }}%</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Charts row 2 -->
      <div class="row">
        <div class="col s12 m6">
          <div class="card chart-card wide z-depth-1">
            <div class="card-content">
              <div class="chart-title"><i class="material-icons">task</i> Tareas con más horas</div>
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
              <div class="table-scroll"><table class="summary-table">
                <thead><tr><th>Tipo</th><th>Horas</th><th style="width:150px">Porcentaje</th></tr></thead>
                <tbody>
                  <tr v-for="t in data.summary.by_type" :key="t.type">
                    <td>{{ t.type }}</td>
                    <td class="hours-val">{{ toHHMM(t.minutes) }}</td>
                    <td><span class="muted">{{ pct(t.minutes, data.summary.total_minutes) }}%</span><div class="bar-wrap"><div class="bar-fill" :style="{width: pct(t.minutes, data.summary.total_minutes)+'%'}"></div></div></td>
                  </tr>
                </tbody>
              </table></div>
            </div>
          </div>
        </div>
        <div class="col s12 m6">
          <div class="card z-depth-1" style="border-radius:10px">
            <div class="card-content" style="padding:16px 20px">
              <div class="chart-title"><i class="material-icons">view_week</i> Por semana</div>
              <div class="table-scroll"><table class="summary-table">
                <thead><tr><th>Semana</th><th>Horas</th><th style="width:150px">Porcentaje</th></tr></thead>
                <tbody>
                  <tr v-for="w in data.summary.by_week" :key="w.week">
                    <td>{{ weekLabel(w.week) }}</td>
                    <td class="hours-val">{{ toHHMM(w.minutes) }}</td>
                    <td><span class="muted">{{ pct(w.minutes, data.summary.total_minutes) }}%</span><div class="bar-wrap"><div class="bar-fill" :style="{width: pct(w.minutes, data.summary.total_minutes)+'%'}"></div></div></td>
                  </tr>
                </tbody>
              </table></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Detail table -->
      <div class="card table-card z-depth-1">
        <div class="table-toolbar">
          <h6><i class="material-icons" style="font-size:20px">list_alt</i> Detalle de registros <span class="row-count">· {{ filteredRows.length }}</span></h6>
          <div class="table-search">
            <i class="material-icons">search</i>
            <input v-model="search" type="text" placeholder="Buscar…" />
          </div>
        </div>
        <div class="table-scroll">
          <table class="summary-table" style="margin:0">
            <thead>
              <tr>
                <th>Fecha</th><th>Tarea</th>
                <th>Tipo</th><th>Comentario</th><th>Horas</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in visibleRows" :key="i">
                <td style="white-space:nowrap">{{ fmtDate(row.date, true) }}</td>
                <td>{{ row.work_item_title }}</td>
                <td><span class="tag-chip" :class="typeClass(row.type)">{{ row.type }}</span></td>
                <td>{{ row.comment }}</td>
                <td class="hours-val" style="white-space:nowrap">{{ toHHMM(row.minutes) }}</td>
              </tr>
              <tr v-if="!filteredRows.length">
                <td colspan="5" style="text-align:center;color:#b0bec5;padding:24px">Sin resultados</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="filteredRows.length > visibleRows.length" class="table-more">
          <a class="btn btn-outline btn-small waves-effect" @click="rowLimit += 25">
            Ver más ({{ filteredRows.length - visibleRows.length }} restantes)
          </a>
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
          <h5><i class="material-icons left" style="font-size:20px;vertical-align:middle">email</i> {{ emailKind === 'cobro' ? 'Enviar cuenta de cobro' : 'Enviar reporte por correo' }}</h5>
          <a class="btn-flat waves-effect modal-close"><i class="material-icons">close</i></a>
        </div>
        <div class="modal-body-inner">
          <p class="modal-period"><i class="material-icons">event</i>Período: <strong>{{ fmtDate(emailDateFrom) }}</strong> al <strong>{{ fmtDate(emailDateTo) }}</strong></p>

          <div class="modal-field">
            <label>Asunto</label>
            <input type="text" v-model="emailSubject" placeholder="Asunto del correo" />
          </div>

          <div class="modal-field">
            <label>Mensaje</label>
            <textarea v-model="emailMessage" rows="7" placeholder="Escribe aquí tu mensaje…"></textarea>
          </div>

          <div class="modal-field">
            <label>Destinatarios</label>
            <div v-if="availableContacts.length" class="contact-options">
              <div
                v-for="c in availableContacts" :key="c.email"
                class="chip contact-option" @click="addContact(c)"
                :title="c.email"
              ><i class="material-icons tiny" style="margin-right:4px">person_add</i>{{ c.name ? `${c.name} · ${c.email}` : c.email }}<i
                  class="material-icons tiny contact-remove" title="Quitar de sugerencias"
                  @click.stop="hideContact(c)"
                >close</i></div>
            </div>
            <div class="recipient-chips">
              <div
                v-for="(r, i) in allRecipients" :key="r"
                class="chip" @click="allRecipients.splice(i,1)"
                title="Click para eliminar"
              >{{ r }}<i class="material-icons tiny" style="margin-left:4px">close</i></div>
              <div
                v-for="c in emailCc" :key="'cc-' + c"
                class="chip cc-chip" title="Copia automática en todos los envíos"
              ><i class="material-icons tiny" style="margin-right:4px">content_copy</i>Copia: {{ c }}</div>
            </div>
            <div class="modal-add-row">
              <input type="email" v-model="extraEmail" placeholder="correo@ejemplo.com" @keyup.enter="addRecipient" />
              <a class="btn btn-primary btn-small waves-effect waves-light" @click="addRecipient">
                <i class="material-icons">add</i>
              </a>
            </div>
            <p v-if="!allRecipients.length" class="modal-hint">Agrega al menos un destinatario</p>
          </div>

          <div v-if="emailKind === 'cobro'" class="modal-field">
            <label>Adjuntos ({{ 3 + Math.max(planillaFiles.length, PLANILLAS_REQUERIDAS) }} archivos)</label>
            <ul class="attachment-list">
              <li class="ok">
                <i class="material-icons tiny">check_circle</i>
                Cuenta de cobro <span class="attachment-note">(se genera automáticamente)</span>
              </li>
              <li class="ok">
                <i class="material-icons tiny">check_circle</i>
                Reporte de horas en Excel <span class="attachment-note">(se genera automáticamente)</span>
              </li>
              <li class="ok">
                <i class="material-icons tiny">check_circle</i>
                Documento soporte GAF-FOR-015 <span class="attachment-note">(se genera automáticamente)</span>
              </li>
              <li :class="planillasOk ? 'ok' : 'missing'">
                <i class="material-icons tiny">{{ planillasOk ? 'check_circle' : 'error_outline' }}</i>
                Planilla de aportes en línea
                <span class="attachment-note">
                  {{ planillasOk ? `(${planillaFiles.length} archivos)` : `(${planillaFiles.length} de ${PLANILLAS_REQUERIDAS} archivos)` }}
                </span>
              </li>
            </ul>

            <!-- Zona para soltar o seleccionar los archivos de la planilla -->
            <label
              class="drop-zone" :class="{ dragging, full: planillaFiles.length >= PLANILLAS_MAX }"
              @dragenter.prevent="dragging = true" @dragover.prevent="dragging = true"
              @dragleave.prevent="dragging = false" @drop.prevent="onPlanillaDrop"
            >
              <input type="file" multiple accept=".pdf,.png,.jpg,.jpeg" ref="planillaInput" @change="onPlanillaChange" />
              <i class="material-icons">cloud_upload</i>
              <span class="drop-title">Arrastra aquí los {{ PLANILLAS_REQUERIDAS }} archivos de la planilla</span>
              <span class="drop-sub">o haz clic para seleccionarlos · PDF, PNG o JPG, máximo 10 MB cada uno</span>
            </label>
            <ul v-if="planillaFiles.length" class="drop-files">
              <li v-for="(f, i) in planillaFiles" :key="f.name + f.size">
                <i class="material-icons tiny">{{ f.type.startsWith('image/') ? 'image' : 'picture_as_pdf' }}</i>
                <span class="drop-file-name">{{ f.name }}</span>
                <span class="drop-file-size">{{ fmtSize(f.size) }}</span>
                <a class="drop-file-remove" title="Quitar" @click="planillaFiles.splice(i, 1)"><i class="material-icons tiny">close</i></a>
              </li>
            </ul>
            <p v-if="planillaError" class="modal-hint" style="color:#c62828">{{ planillaError }}</p>
          </div>

          <div v-if="emailError" class="modal-error">{{ emailError }}</div>
          <div v-if="emailSuccess" class="modal-success">{{ emailSuccess }}</div>
        </div>
      </div>
      <div class="modal-foot">
        <a class="btn btn-outline waves-effect modal-close">Cancelar</a>
        <a class="btn btn-primary waves-effect waves-light" :class="{ disabled: sending || (emailKind === 'cobro' && !planillasOk) }" @click="sendEmail">
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
import { route, segments, navigate } from './router.js'
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
const monthData      = ref(null)   // datos del tab "mes"
const cycleData      = ref(null)   // datos del tab "cobro"
const rangeData      = ref(null)   // datos del tab "rango"
const selectedCycle  = ref(null)
const data           = computed(() => ({ mes: monthData.value, cobro: cycleData.value, rango: rangeData.value })[activeMode.value])
const importedReports = computed(() => (props.reports || []).filter(r => r.in_db))
const loading        = ref(false)
const importing      = ref(false)
const search         = ref('')
const rowLimit       = ref(25)
let   monthFetchToken = 0
let   cycleFetchToken = 0
let   rangeFetchToken = 0

// ── Email ──
const emailModal    = ref(false)
const emailDateFrom = ref('')
const emailDateTo   = ref('')
const allRecipients = ref([])
const extraEmail    = ref('')
const emailSubject  = ref('')
const emailMessage  = ref('')
const sending       = ref(false)
const emailError    = ref('')
const emailSuccess  = ref('')
const contacts      = ref([])
const emailKind     = ref('reporte')   // 'reporte' | 'cobro'
const emailCc       = ref([])
// Planilla de aportes en línea: llega en 2 archivos
const PLANILLAS_REQUERIDAS = 2
const PLANILLAS_MAX        = 4
const PLANILLA_MAX_BYTES   = 10 * 1024 * 1024
const planillaFiles = ref([])
const planillaInput = ref(null)
const planillaError = ref('')
const dragging      = ref(false)
const planillasOk   = computed(() => planillaFiles.value.length >= PLANILLAS_REQUERIDAS)
const availableContacts = computed(() => contacts.value.filter(c => !allRecipients.value.includes(c.email)))

const MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
function monthLabel(date) {
  const [y, m] = date.split('-')
  return `${MESES[+m - 1]} de ${y}`
}
function buildMessage(name) {
  const mes = monthLabel(emailDateTo.value)
  if (emailKind.value === 'cobro') {
    return [
      `Hola ${name},`,
      'Espero que se encuentre muy bien.',
      `Envío la cuenta de cobro correspondiente al mes de ${mes}, junto con el reporte de horas en Excel, el documento soporte de prestación de servicios y la planilla de aportes en línea (seguridad social) del mismo período, como soporte para el pago.`,
      'Agradezco su ayuda gestionando el pago. Si necesita algún documento adicional o algún ajuste, quedo atento.',
      'Cordialmente,\nFabian Vargas',
    ].join('\n\n')
  }
  const rows  = data.value?.rows || []
  const total = data.value?.summary?.total_minutes || 0
  const dias  = new Set(rows.map(r => r.date)).size
  const totales = total
    ? ` En total registré ${toHHMM(total)} horas distribuidas en ${dias} días de trabajo.`
    : ''
  return [
    `Hola ${name},`,
    'Espero que se encuentre muy bien.',
    `Comparto el reporte de horas correspondiente al mes de ${mes}.${totales}`,
    'Adjunto el detalle en Excel y en PDF, con el resumen por tipo de actividad, por semana y el listado completo de registros.',
    'Quedo atento a cualquier comentario o ajuste.',
    'Cordialmente,\nFabian Vargas',
  ].join('\n\n')
}
let greetingName = 'Diego'
let emailMonth = null   // mes calendario del envío (pestaña 'mes')
let emailCycle = null   // ciclo de cuenta de cobro del envío (pestaña 'cobro')

onMounted(() => {
  mTabs  = M.Tabs.init(tabsEl.value, {
    onShow: (el) => {
      if (selectingTab) return   // cambio hecho desde applyRoute, no por un clic
      const mode = { 'tab-mes': 'mes', 'tab-cobro': 'cobro', 'tab-rango': 'rango' }[el.id]
      navigate(urlForMode(mode))
    }
  })
  mModal = M.Modal.init(modalEl.value, { dismissible: true })
  applyRoute()
})

// ── URL ↔ estado ──
// La URL es la fuente de verdad: chips, pestañas y "Aplicar" solo navegan, y applyRoute
// carga lo que la URL indique (también al recargar o con atrás/adelante del navegador).
const TAB_IDS  = { mes: 'tab-mes', cobro: 'tab-cobro', rango: 'tab-rango' }
const SECTIONS = { mes: 'mes', 'cuenta-cobro': 'cobro', rango: 'rango' }
let selectingTab = false

function urlForMode(mode) {
  if (mode === 'cobro') return selectedCycle.value ? `/cuenta-cobro/${selectedCycle.value}` : '/cuenta-cobro'
  if (mode === 'rango') return '/rango'
  return selectedMonth.value ? `/mes/${selectedMonth.value}` : '/mes'
}

async function applyRoute() {
  if (!mTabs || !props.reports?.length) return
  const [section, key] = segments()
  const mode = SECTIONS[section] || 'mes'

  if (mode !== activeMode.value) {
    destroyCharts(); loading.value = false
    activeMode.value = mode
    selectingTab = true; mTabs.select(TAB_IDS[mode]); selectingTab = false
    if (data.value) { await nextTick(); renderCharts() }   // datos que ya tenía la pestaña
  }

  const firstImported = importedReports.value[0]?.month
  if (mode === 'mes') {
    const month = key || selectedMonth.value || firstImported
    if (!month) return
    if (!key) { navigate(`/mes/${month}`, {}, true); return }
    if (month !== selectedMonth.value || (!monthData.value && !loading.value)) loadMonth(month)
  } else if (mode === 'cobro') {
    const month = key || selectedCycle.value || firstImported
    if (!month) return
    if (!key) { navigate(`/cuenta-cobro/${month}`, {}, true); return }
    if (month !== selectedCycle.value || (!cycleData.value && !loading.value)) loadCycle(month)
  } else {
    const { desde, hasta } = route.query
    if (desde && hasta && (desde !== dateFrom.value || hasta !== dateTo.value || !rangeData.value)) {
      dateFrom.value = desde; dateTo.value = hasta
      loadRange()
    }
  }
  updateTitle()
}

function applyRange() {
  if (!dateFrom.value || !dateTo.value) return
  // Si la URL ya tenía esas fechas, recargar igual
  if (!navigate('/rango', { desde: dateFrom.value, hasta: dateTo.value })) loadRange()
}

function updateTitle() {
  const label = m => props.reports.find(r => r.month === m)?.label || m
  const parts = {
    mes:   () => [label(selectedMonth.value), 'Por mes'],
    cobro: () => [label(selectedCycle.value), 'Cuenta de cobro'],
    rango: () => [dateFrom.value && dateTo.value ? `${fmtDate(dateFrom.value)} – ${fmtDate(dateTo.value)}` : null, 'Por rango'],
  }[activeMode.value]()
  document.title = [...parts.filter(Boolean), 'Complemento 360'].join(' · ')
}

watch(() => [route.path, route.query.desde, route.query.hasta], applyRoute)
watch(() => props.reports, applyRoute)
watch([selectedMonth, selectedCycle], updateTitle)

function authHeaders() { return { Authorization: `Bearer ${props.token}` } }

async function loadMonth(month) {
  selectedMonth.value = month
  selectedReport.value = props.reports.find(r => r.month === month) || null
  if (!selectedReport.value?.in_db) { monthData.value = null; return }
  const token = ++monthFetchToken
  loading.value = true; monthData.value = null; destroyCharts()
  const res = await fetch(`/api/reports/${month}/data`, { headers: authHeaders() })
  if (token !== monthFetchToken) return
  monthData.value = await res.json()
  loading.value = false
  await nextTick(); renderCharts()
}

async function loadCycle(month) {
  selectedCycle.value = month
  const token = ++cycleFetchToken
  loading.value = true; cycleData.value = null; destroyCharts()
  const res = await fetch(`/api/reports/${month}/data?cycle=true`, { headers: authHeaders() })
  if (token !== cycleFetchToken) return
  cycleData.value = res.ok ? await res.json() : null
  loading.value = false
  await nextTick(); renderCharts()
}

async function loadRange() {
  if (!dateFrom.value || !dateTo.value) return
  const token = ++rangeFetchToken
  loading.value = true; rangeData.value = null; destroyCharts()
  const res = await fetch(`/api/entries?date_from=${dateFrom.value}&date_to=${dateTo.value}`, { headers: authHeaders() })
  if (token !== rangeFetchToken) return
  rangeData.value = await res.json()
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
    { icon: 'task',          label: 'Tareas',       value: s.by_work_item.length },
    { icon: 'today',         label: 'Días trabajados',  value: uniqueDays.value },
    { icon: 'speed',         label: 'Promedio por día',     value: uniqueDays.value ? toHHMM(Math.round(s.total_minutes / uniqueDays.value)) : '0:00' },
  ]
})

const visibleRows = computed(() => filteredRows.value.slice(0, rowLimit.value))
watch([search, data], () => { rowLimit.value = 25 })

const filteredRows = computed(() => {
  if (!data.value) return []
  let rows = data.value.rows
  if (activeMode.value === 'rango' && dateFrom.value && dateTo.value) {
    rows = rows.filter(r => r.date >= dateFrom.value && r.date <= dateTo.value)
  }
  const q = search.value.toLowerCase()
  return q ? rows.filter(r =>
    r.work_item_title.toLowerCase().includes(q) ||
    r.comment.toLowerCase().includes(q) ||
    r.type.toLowerCase().includes(q)
  ) : rows
})

// ── Charts ──
// Distribución por tipo: 6 tipos principales + "Otros", con colores de la marca
const TYPE_COLORS = ['#E8752A', '#1A2744', '#F5B88A', '#6D6E71', '#C65D0A', '#8FA3BF', '#DDE3E8']
const typeGroups = computed(() => {
  const types = data.value?.summary?.by_type || []
  const top = types.slice(0, 6).map(t => ({ label: t.type, minutes: t.minutes }))
  const rest = types.slice(6).reduce((a, t) => a + t.minutes, 0)
  if (rest) top.push({ label: `Otros (${types.length - 6} tipos)`, minutes: rest })
  return top
})
const PALETTE = ['#E8752A','#6D6E71','#D4631A','#9E9E9E','#F0A060','#4A4A4A','#F5C49A','#8A8A8A','#C85E1A','#B0B0B0']

function destroyCharts() { charts.forEach(c => c.destroy()); charts = [] }

function renderCharts() {
  if (!data.value) return
  const s = data.value.summary

  charts.push(new Chart(weekChart.value, {
    type: 'bar',
    data: { labels: s.by_week.map(w => weekLabel(w.week, true)), datasets: [{ data: s.by_week.map(w => +(w.minutes/60).toFixed(2)), backgroundColor: '#E8752A', hoverBackgroundColor: '#C65D0A', borderRadius: 6, maxBarThickness: 48 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => toHHMM(s.by_week[ctx.dataIndex].minutes) } } }, scales: { y: { beginAtZero: true, ticks: { callback: v => `${v}h` } } } },
  }))

  const groups = typeGroups.value
  charts.push(new Chart(typeChart.value, {
    type: 'doughnut',
    data: { labels: groups.map(g => g.label), datasets: [{ data: groups.map(g => +(g.minutes/60).toFixed(2)), backgroundColor: TYPE_COLORS, borderColor: '#fff', borderWidth: 2, hoverOffset: 4 }] },
    options: { responsive: true, maintainAspectRatio: false, cutout: '68%', plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ` ${toHHMM(groups[ctx.dataIndex].minutes)} · ${pct(groups[ctx.dataIndex].minutes, s.total_minutes)}%` } } } },
  }))

  const topItems = s.by_work_item.slice(0, 10)
  charts.push(new Chart(itemChart.value, {
    type: 'bar',
    data: { labels: topItems.map(w => w.title.length > 28 ? w.title.slice(0,28)+'…' : w.title), datasets: [{ data: topItems.map(w => +(w.minutes/60).toFixed(2)), backgroundColor: '#E8752A', hoverBackgroundColor: '#C65D0A', borderRadius: 4, maxBarThickness: 18 }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { title: items => topItems[items[0].dataIndex].title, label: ctx => toHHMM(topItems[ctx.dataIndex].minutes) } } }, scales: { x: { beginAtZero: true, ticks: { callback: v => `${v}h` } } } },
  }))

  const byDay = {}
  data.value.rows.forEach(r => { byDay[r.date] = (byDay[r.date]||0) + r.minutes })
  const days = Object.keys(byDay).sort()
  charts.push(new Chart(dayChart.value, {
    type: 'bar',
    // Día completo (8 h o más) en naranja fuerte; medio día en naranja suave; menos en gris
    data: { labels: days.map(d => fmtDate(d)), datasets: [{ data: days.map(d => +(byDay[d]/60).toFixed(2)), backgroundColor: days.map(d => byDay[d]>=480?'#E8752A':byDay[d]>=240?'#F5B88A':'#CFD8DC'), borderRadius: 4, maxBarThickness: 22 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { title: items => fmtDate(days[items[0].dataIndex], true), label: ctx => toHHMM(byDay[days[ctx.dataIndex]]) } } }, scales: { y: { beginAtZero: true, ticks: { callback: v => `${v}h` } } } },
  }))
}

// ── Email ──
// Ciclo de cuenta de cobro de un mes: del 25 del mes anterior al 24 del mes (el backend filtra igual)
function cyclePeriod(month) {
  const [y, m] = month.split('-').map(Number)
  const prev = m === 1 ? [y - 1, 12] : [y, m - 1]
  const pad = n => String(n).padStart(2, '0')
  return [`${prev[0]}-${pad(prev[1])}-25`, `${y}-${pad(m)}-24`]
}

// Periodo visible: mes calendario en 'mes', ciclo 25–24 en 'cobro', rango elegido en 'rango'
function currentPeriod() {
  if (activeMode.value === 'cobro' && selectedCycle.value) return cyclePeriod(selectedCycle.value)
  if (activeMode.value === 'mes' && selectedMonth.value) {
    const [y, m] = selectedMonth.value.split('-').map(Number)
    const pad = n => String(n).padStart(2, '0')
    return [`${y}-${pad(m)}-01`, `${y}-${pad(m)}-${pad(new Date(y, m, 0).getDate())}`]
  }
  return [dateFrom.value, dateTo.value]
}
function currentMonthKey() {
  return activeMode.value === 'mes' ? selectedMonth.value : null
}
function currentCycleKey() {
  return activeMode.value === 'cobro' ? selectedCycle.value : null
}

function openEmailModal(kind = 'reporte') {
  emailKind.value = kind
  planillaFiles.value = []; planillaError.value = ''
  if (planillaInput.value) planillaInput.value.value = ''
  ;[emailDateFrom.value, emailDateTo.value] = currentPeriod()
  emailMonth = currentMonthKey()
  emailCycle = currentCycleKey()
  emailError.value = ''; emailSuccess.value = ''; extraEmail.value = ''
  allRecipients.value = []
  greetingName = 'Diego'
  emailSubject.value = emailKind.value === 'cobro'
    ? `Cuenta de cobro · ${monthLabel(emailDateTo.value)}`
    : `Reporte de horas · ${monthLabel(emailDateTo.value)}`
  emailMessage.value = buildMessage(greetingName)
  loadContacts()
  mModal.open()
}

async function loadContacts() {
  try {
    const [res, ccRes] = await Promise.all([
      fetch('/api/email/contacts', { headers: authHeaders() }),
      fetch('/api/email/cc', { headers: authHeaders() }),
    ])
    if (res.ok) contacts.value = await res.json()
    if (ccRes.ok) emailCc.value = await ccRes.json()
  } catch { /* sin sugerencias */ }
}

async function hideContact(c) {
  contacts.value = contacts.value.filter(x => x.email !== c.email)
  try {
    const res = await fetch(`/api/email/contacts/${encodeURIComponent(c.email)}`, { method: 'DELETE', headers: authHeaders() })
    if (!res.ok) throw new Error()
  } catch {
    emailError.value = `No se pudo quitar ${c.email} de las sugerencias`
    loadContacts()
  }
}

function addPlanillas(fileList) {
  planillaError.value = ''
  for (const f of fileList) {
    if (!/\.(pdf|png|jpe?g)$/i.test(f.name)) { planillaError.value = `${f.name}: solo PDF, PNG o JPG`; continue }
    if (f.size > PLANILLA_MAX_BYTES) { planillaError.value = `${f.name} supera 10 MB`; continue }
    if (planillaFiles.value.some(x => x.name === f.name && x.size === f.size)) continue   // repetido
    if (planillaFiles.value.length >= PLANILLAS_MAX) { planillaError.value = `Máximo ${PLANILLAS_MAX} archivos`; break }
    planillaFiles.value.push(f)
  }
}
function onPlanillaChange(e) {
  addPlanillas(e.target.files || [])
  e.target.value = ''   // permite volver a elegir el mismo archivo después de quitarlo
}
function onPlanillaDrop(e) {
  dragging.value = false
  addPlanillas(e.dataTransfer?.files || [])
}
function fmtSize(bytes) {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`
}

function addContact(c) {
  if (!allRecipients.value.includes(c.email)) allRecipients.value.push(c.email)
  // Ajusta el saludo al primer contacto con nombre, si el mensaje no se ha editado
  const firstName = c.name.split(' ')[0]
  if (firstName && emailMessage.value === buildMessage(greetingName) && allRecipients.value.length === 1) {
    greetingName = firstName
    emailMessage.value = buildMessage(greetingName)
  }
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
    let res
    if (emailKind.value === 'cobro') {
      if (!planillasOk.value) {
        emailError.value = `La planilla de aportes en línea son ${PLANILLAS_REQUERIDAS} archivos: adjuntaste ${planillaFiles.value.length}`
        return
      }
      const form = new FormData()
      form.append('date_from', emailDateFrom.value)
      form.append('date_to', emailDateTo.value)
      form.append('extra_recipients', JSON.stringify(allRecipients.value))
      form.append('subject', emailSubject.value)
      form.append('message', emailMessage.value)
      if (emailMonth) form.append('month', emailMonth)
      if (emailCycle) form.append('cycle', emailCycle)
      planillaFiles.value.forEach(f => form.append('planillas', f))
      res = await fetch('/api/email/send-cuenta-cobro', { method: 'POST', headers: authHeaders(), body: form })
    } else {
      res = await fetch('/api/email/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ date_from: emailDateFrom.value, date_to: emailDateTo.value, month: emailMonth, cycle: emailCycle, extra_recipients: allRecipients.value, subject: emailSubject.value, message: emailMessage.value }),
      })
    }
    const d = await res.json()
    if (!res.ok) { emailError.value = d.detail; return }
    emailSuccess.value = `✓ Correo enviado a ${d.sent_to.join(', ')}` + (d.attachments ? ` con ${d.attachments.length} adjuntos: ${d.attachments.join(', ')}` : '')
  } catch { emailError.value = 'Error al conectar' }
  finally { sending.value = false }
}

// ── Cuenta de cobro ──
// Descarga un archivo generado por el backend para el periodo visible
async function downloadFile(endpoint, filename, errorMsg) {
  const [from, to] = currentPeriod()
  if (!data.value || !from || !to) return
  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ date_from: from, date_to: to, month: currentMonthKey(), cycle: currentCycleKey() }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      alert(err.detail || errorMsg)
      return
    }
    const url = URL.createObjectURL(await res.blob())
    const a   = document.createElement('a')
    a.href     = url
    a.download = filename(from, to)
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    alert('Error al conectar con el servidor')
  }
}

function downloadCuentaCobro() {
  return downloadFile('/api/cuenta-cobro/download', (f, t) => `cuenta_cobro_${f}_${t}.pdf`, 'Error al generar la cuenta de cobro')
}

function downloadDocumentoSoporte() {
  return downloadFile('/api/documento-soporte/download', (f, t) => `documento_soporte_${t.slice(0, 7)}.xlsx`, 'Error al generar el documento soporte')
}

function downloadReporte() {
  return downloadFile('/api/reporte/download', (f, t) => `reporte_${f}_${t}.xlsx`, 'Error al generar el reporte')
}

// ── Helpers ──
function toHHMM(min) { const h=Math.floor(min/60),m=min%60; return `${h}:${String(m).padStart(2,'0')}` }
function pct(v, t) { return t ? Math.round(v/t*100) : 0 }

const MESES_CORTOS = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']
const DIAS_CORTOS  = ['dom','lun','mar','mié','jue','vie','sáb']
// '2026-10-26' → '26 oct' (withDay: 'lun 26 oct')
function fmtDate(d, withDay = false) {
  if (!d) return ''
  const [y, m, day] = d.slice(0, 10).split('-').map(Number)
  const base = `${day} ${MESES_CORTOS[m - 1]}`
  return withDay ? `${DIAS_CORTOS[new Date(y, m - 1, day).getDay()]} ${base}` : base
}
// '2026-W45' → 'Semana 45 · 2 al 8 nov' (short: 'Sem 45')
function weekLabel(week, short = false) {
  const match = /^(\d{4})-W(\d{1,2})$/.exec(week || '')
  if (!match) return week
  const [, y, w] = match.map(Number)
  if (short) return `Sem ${w}`
  const jan4 = new Date(y, 0, 4)
  const monday = new Date(jan4); monday.setDate(jan4.getDate() - ((jan4.getDay() + 6) % 7) + (w - 1) * 7)
  const sunday = new Date(monday); sunday.setDate(monday.getDate() + 6)
  const f = dt => `${dt.getDate()} ${MESES_CORTOS[dt.getMonth()]}`
  return `Semana ${w} · ${f(monday)} al ${f(sunday)}`
}
function typeClass(type) {
  const t = (type||'').toLowerCase()
  if (t.includes('admin')) return 'admin'
  if (t.includes('dev')||t.includes('conc')) return 'dev'
  if (t.includes('est')) return 'est'
  return 'default'
}
</script>
