<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch, watchEffect } from 'vue'
import type { Viewer } from 'cesium'
import Timeline from './components/Timeline.vue'
import { createHydroViewer, renderHydroScene } from './cesium/hydroViewer'
import { useNetworkStore } from './stores/network'
import { useScenarioStore } from './stores/scenario'

const mapHost = ref<HTMLElement | null>(null)
const releaseCms = ref(2200)
const network = useNetworkStore()
const scenario = useScenarioStore()
let viewer: Viewer | undefined

const riverCount = computed(() => network.objects.filter((item) => item.object_type === 'river_reach').length)
const assetCount = computed(() => network.objects.filter((item) => item.object_type !== 'river_reach').length)
const currentFlow = computed(() => {
  const states = network.states.filter((item) => item.timestamp_minutes === scenario.timestamp && item.variable === 'flow')
  if (!states.length) return null
  return Math.max(...states.map((item) => item.value))
})
const storageState = computed(() => network.states.find((item) => (
  item.timestamp_minutes === scenario.timestamp && item.variable === 'storage'
)))

watch(() => network.states, (states) => scenario.setStates(states), { deep: true })

onMounted(async () => {
  if (!mapHost.value) throw new Error('Cesium map host is unavailable')
  viewer = createHydroViewer(mapHost.value)
  await network.load()
})

watchEffect(() => {
  const objects = network.objects
  const highlighted = new Set(Array.from(network.highlightedIds))
  const states = network.states
  const timestamp = scenario.timestamp
  if (viewer && objects.length > 0) {
    renderHydroScene(viewer, objects, highlighted, states, timestamp)
  }
})

onBeforeUnmount(() => {
  if (viewer && !viewer.isDestroyed()) viewer.destroy()
})

async function runScenario() {
  await network.runScenario(releaseCms.value)
}
</script>

<template>
  <main class="app-shell">
    <aside class="control-panel">
      <div class="brand-row">
        <div class="brand-mark">HP</div>
        <div>
          <p class="eyebrow">HydroPilot v0.1</p>
          <h1>Sacramento<br>Water Network</h1>
        </div>
      </div>

      <p class="note">Real CesiumJS digital-twin viewer for a directed public water-network fixture. This demonstrator is not for operational flood-control decisions.</p>

      <div class="metric-grid">
        <article><span>River reaches</span><strong>{{ riverCount }}</strong></article>
        <article><span>Engineering assets</span><strong>{{ assetCount }}</strong></article>
        <article><span>Scenario time</span><strong>{{ scenario.timestamp }} min</strong></article>
        <article><span>Peak visible flow</span><strong>{{ currentFlow == null ? '—' : currentFlow.toFixed(0) + ' m³/s' }}</strong></article>
      </div>

      <section class="panel-section">
        <h2>Network topology</h2>
        <button data-testid="highlight-downstream" class="action primary" @click="network.highlightDownstream('reach-001')">Highlight downstream chain</button>
        <p class="helper">Highlights the directed <code>FLOWS_TO</code> path from the upper demo reach.</p>
      </section>

      <section class="panel-section">
        <h2>Release scenario</h2>
        <label class="field-label" for="release">Reservoir release</label>
        <div class="release-field">
          <input id="release" v-model.number="releaseCms" type="number" min="0" step="100">
          <span>m³/s</span>
        </div>
        <button data-testid="run-scenario" class="action warning" @click="runScenario">Run 0D + 1D scenario</button>
        <p class="helper">Mass-balance reservoir step followed by Muskingum routing along the directed network.</p>
      </section>

      <div class="status-card" data-testid="scenario-status">
        <span>Reservoir storage</span>
        <strong>{{ storageState ? (storageState.value / 1e9).toFixed(2) + ' B m³' : 'Run scenario' }}</strong>
      </div>

      <div class="legend">
        <span><i class="legend-line river" />River</span>
        <span><i class="legend-dot reservoir" />Reservoir</span>
        <span><i class="legend-dot dam" />Dam</span>
        <span><i class="legend-dot gauge" />Gauge</span>
        <span><i class="legend-dot control" />Control point</span>
      </div>
    </aside>

    <section class="map-stage">
      <div ref="mapHost" class="cesium-host" data-testid="cesium-host" />
      <div class="map-header">
        <div><span class="live-dot" /> CESIUM 3D / EPSG:4326</div>
        <div>{{ network.objects.length }} OBJECTS · PUBLIC DEMO DATA</div>
      </div>
      <div class="map-title-card">
        <span>Water-network digital twin</span>
        <strong>Shasta → Sacramento control section</strong>
      </div>
      <Timeline v-if="network.states.length" />
    </section>
  </main>
</template>
