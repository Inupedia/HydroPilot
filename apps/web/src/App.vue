<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch, watchEffect } from 'vue'
import type { Entity, Viewer } from 'cesium'
import Timeline from './components/Timeline.vue'
import { hydroApi, type LlmChatMessage, type LlmProviderSummary } from './api/client'
import { createHydroViewer, renderHydroScene } from './cesium/hydroViewer'
import { parseCopilotCommand } from './copilot/commands'
import { useNetworkStore } from './stores/network'
import { useScenarioStore } from './stores/scenario'

const mapHost = ref<HTMLElement | null>(null)
const releaseCms = ref(2200)
const network = useNetworkStore()
const scenario = useScenarioStore()
let viewer: Viewer | undefined

const busyAction = ref('')
const actionStatus = ref('Ready — try one of the guided actions below.')
const actionTone = ref<'idle' | 'working' | 'success' | 'error'>('idle')

const providers = ref<LlmProviderSummary[]>([])
const selectedProvider = ref(localStorage.getItem('hydropilot.llm.provider') || 'openai')
const selectedModel = ref(localStorage.getItem('hydropilot.llm.model') || '')
const apiKey = ref('')
const customBaseUrl = ref(localStorage.getItem('hydropilot.llm.baseUrl') || '')
const providerSettingsOpen = ref(true)
const secretState = ref('')
const copilotPrompt = ref('')
const copilotBusy = ref(false)
const copilotMessages = ref<LlmChatMessage[]>([
  { role: 'assistant', content: 'Start with a suggested command. Map-control commands work even before you configure an LLM.' },
])

const examples = [
  '高亮这条水网的下游链路',
  '按 2200 m³/s 运行下泄调度场景',
  '解释当前水网里有哪些工程对象',
]

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
const activeProvider = computed(() => providers.value.find((item) => item.id === selectedProvider.value))
const providerNeedsKey = computed(() => activeProvider.value?.auth_required ?? true)
const providerReady = computed(() => {
  if (!selectedModel.value.trim()) return false
  if (selectedProvider.value === 'custom-openai' && !customBaseUrl.value.trim()) return false
  return !providerNeedsKey.value || Boolean(apiKey.value.trim())
})

watch(() => network.states, (states) => scenario.setStates(states), { deep: true })
watch(selectedProvider, async (providerId) => {
  localStorage.setItem('hydropilot.llm.provider', providerId)
  const provider = providers.value.find((item) => item.id === providerId)
  if (provider?.model_examples.length) {
    selectedModel.value = provider.model_examples[0]
  } else if (providerId === 'custom-openai') {
    selectedModel.value = ''
  }
  await loadApiKey(providerId)
})
watch(selectedModel, (model) => localStorage.setItem('hydropilot.llm.model', model))
watch(customBaseUrl, (url) => localStorage.setItem('hydropilot.llm.baseUrl', url))

onMounted(async () => {
  if (!mapHost.value) throw new Error('Cesium map host is unavailable')
  viewer = createHydroViewer(mapHost.value)
  try {
    await network.load()
    providers.value = await hydroApi.llmProviders()
    const validProvider = providers.value.some((item) => item.id === selectedProvider.value)
    if (!validProvider && providers.value.length) selectedProvider.value = providers.value[0].id
    const active = providers.value.find((item) => item.id === selectedProvider.value)
    if (!selectedModel.value && active?.model_examples.length) selectedModel.value = active.model_examples[0]
    await loadApiKey(selectedProvider.value)
  } catch (error) {
    setActionStatus(`Startup error: ${error instanceof Error ? error.message : String(error)}`, 'error')
  }
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

function setActionStatus(message: string, tone: 'idle' | 'working' | 'success' | 'error' = 'idle') {
  actionStatus.value = message
  actionTone.value = tone
}

async function focusHighlighted() {
  await nextTick()
  if (!viewer) return
  const entities = Array.from(network.highlightedIds)
    .map((id) => viewer?.entities.getById(id))
    .filter((entity): entity is Entity => Boolean(entity))
  if (entities.length) await viewer.flyTo(entities, { duration: 1.1 })
}

async function highlightDownstream() {
  busyAction.value = 'highlight'
  setActionStatus('Tracing the directed FLOWS_TO network…', 'working')
  try {
    await network.highlightDownstream('reach-001')
    await focusHighlighted()
    setActionStatus(`Highlighted ${network.highlightedIds.size} connected objects and moved the camera to them.`, 'success')
  } catch (error) {
    setActionStatus(`Could not highlight network: ${error instanceof Error ? error.message : String(error)}`, 'error')
  } finally {
    busyAction.value = ''
  }
}

async function runScenario() {
  busyAction.value = 'scenario'
  setActionStatus(`Running reservoir + Muskingum routing at ${releaseCms.value.toLocaleString()} m³/s…`, 'working')
  try {
    await network.runScenario(releaseCms.value)
    setActionStatus(`Scenario ready: ${scenario.timestamps.length} time steps. Use the timeline at the bottom of the map.`, 'success')
  } catch (error) {
    setActionStatus(`Scenario failed: ${error instanceof Error ? error.message : String(error)}`, 'error')
  } finally {
    busyAction.value = ''
  }
}

async function loadApiKey(providerId: string) {
  secretState.value = ''
  try {
    if (window.hydropilotDesktop?.secrets) {
      apiKey.value = await window.hydropilotDesktop.secrets.get(`llm:${providerId}`) || ''
      secretState.value = apiKey.value ? 'Saved securely on this device' : 'No saved key'
      return
    }
    apiKey.value = sessionStorage.getItem(`hydropilot.llm.key.${providerId}`) || ''
    secretState.value = apiKey.value ? 'Saved for this browser session' : 'No saved key'
  } catch {
    apiKey.value = ''
    secretState.value = 'Key storage unavailable'
  }
}

async function saveApiKey() {
  try {
    if (window.hydropilotDesktop?.secrets) {
      if (apiKey.value.trim()) await window.hydropilotDesktop.secrets.set(`llm:${selectedProvider.value}`, apiKey.value.trim())
      else await window.hydropilotDesktop.secrets.remove(`llm:${selectedProvider.value}`)
      secretState.value = apiKey.value.trim() ? 'Saved securely on this device' : 'Saved key removed'
    } else {
      if (apiKey.value.trim()) sessionStorage.setItem(`hydropilot.llm.key.${selectedProvider.value}`, apiKey.value.trim())
      else sessionStorage.removeItem(`hydropilot.llm.key.${selectedProvider.value}`)
      secretState.value = apiKey.value.trim() ? 'Saved for this browser session' : 'Saved key removed'
    }
  } catch (error) {
    secretState.value = `Could not save key: ${error instanceof Error ? error.message : String(error)}`
  }
}

function addCopilotMessage(role: 'user' | 'assistant', content: string) {
  copilotMessages.value.push({ role, content })
  if (copilotMessages.value.length > 8) copilotMessages.value = copilotMessages.value.slice(-8)
}

async function submitCopilot(text = copilotPrompt.value) {
  const prompt = text.trim()
  if (!prompt || copilotBusy.value) return
  copilotPrompt.value = ''
  addCopilotMessage('user', prompt)
  copilotBusy.value = true

  try {
    const command = parseCopilotCommand(prompt)
    if (command.type === 'highlight-downstream') {
      await highlightDownstream()
      addCopilotMessage('assistant', `Done. I highlighted ${network.highlightedIds.size} objects in the downstream chain and focused the map.`)
      return
    }
    if (command.type === 'run-release') {
      releaseCms.value = command.releaseCms
      await runScenario()
      addCopilotMessage('assistant', `Done. The ${command.releaseCms.toLocaleString()} m³/s release scenario is on the map. Drag the bottom timeline to inspect propagation.`)
      return
    }

    if (!providerReady.value) {
      providerSettingsOpen.value = true
      addCopilotMessage('assistant', 'This question needs an LLM. Choose a provider, model, and API key in Model settings first. The two map-control commands above work without an LLM.')
      return
    }

    const system = `You are HydroPilot, a concise water-network GIS copilot. This is a public-data demonstrator, not operational flood-control decision support. Current scene: ${network.objects.length} objects, ${riverCount.value} river reaches, ${assetCount.value} engineering assets. Current scenario time: ${scenario.timestamp} minutes. ${currentFlow.value == null ? 'No routing scenario is active.' : `Peak visible flow is ${currentFlow.value.toFixed(0)} m3/s.`} Explain what is visible and be explicit that you cannot change the map unless HydroPilot executes a supported local command.`
    const response = await hydroApi.llmChat({
      provider: selectedProvider.value,
      model: selectedModel.value.trim(),
      api_key: apiKey.value.trim() || undefined,
      base_url: customBaseUrl.value.trim() || undefined,
      messages: [
        { role: 'system', content: system },
        ...copilotMessages.value.slice(-5).filter((message) => message.role !== 'system'),
      ],
      temperature: 0.2,
      max_tokens: 1200,
    })
    addCopilotMessage('assistant', response.text)
  } catch (error) {
    addCopilotMessage('assistant', `Request failed: ${error instanceof Error ? error.message : String(error)}`)
  } finally {
    copilotBusy.value = false
  }
}
</script>

<template>
  <main class="app-shell">
    <aside class="control-panel">
      <div class="brand-row">
        <div class="brand-mark">HP</div>
        <div>
          <p class="eyebrow">HydroPilot v0.2.1</p>
          <h1>Sacramento<br>Water Network</h1>
        </div>
      </div>

      <p class="note">AI-assisted Cesium water-network demonstrator. Start with a guided command below; every action now reports what changed.</p>

      <div class="metric-grid">
        <article><span>River reaches</span><strong>{{ riverCount }}</strong></article>
        <article><span>Engineering assets</span><strong>{{ assetCount }}</strong></article>
        <article><span>Scenario time</span><strong>{{ scenario.timestamp }} min</strong></article>
        <article><span>Peak visible flow</span><strong>{{ currentFlow == null ? '—' : currentFlow.toFixed(0) + ' m³/s' }}</strong></article>
      </div>

      <section class="copilot-card" data-testid="copilot-panel">
        <div class="section-heading-row">
          <div>
            <span class="section-kicker">AI COPILOT</span>
            <h2>Tell the map what to do</h2>
          </div>
          <span class="provider-badge" :class="{ ready: providerReady }">{{ providerReady ? activeProvider?.name || 'Ready' : 'Model setup' }}</span>
        </div>

        <div class="quick-prompts">
          <button v-for="example in examples" :key="example" type="button" @click="submitCopilot(example)">{{ example }}</button>
        </div>

        <div class="copilot-thread" aria-live="polite">
          <div v-for="(message, index) in copilotMessages.slice(-4)" :key="index" class="copilot-message" :class="message.role">
            <span>{{ message.role === 'assistant' ? 'HP' : 'YOU' }}</span>
            <p>{{ message.content }}</p>
          </div>
        </div>

        <form class="copilot-compose" @submit.prevent="submitCopilot()">
          <textarea v-model="copilotPrompt" rows="2" placeholder="例如：按 2600 m³/s 跑一次调度，或者问当前水网有什么对象" />
          <button class="send-button" type="submit" :disabled="copilotBusy || !copilotPrompt.trim()">{{ copilotBusy ? 'Working…' : 'Send' }}</button>
        </form>

        <button class="settings-toggle" type="button" @click="providerSettingsOpen = !providerSettingsOpen">
          {{ providerSettingsOpen ? 'Hide model settings' : 'Model settings' }}
        </button>

        <div v-if="providerSettingsOpen" class="provider-settings">
          <label>Provider
            <select v-model="selectedProvider">
              <option v-for="provider in providers" :key="provider.id" :value="provider.id">{{ provider.name }}</option>
            </select>
          </label>
          <label>Model
            <input v-model="selectedModel" placeholder="Model ID">
          </label>
          <label v-if="selectedProvider === 'custom-openai'">Base URL
            <input v-model="customBaseUrl" placeholder="https://example.com/v1">
          </label>
          <label v-if="providerNeedsKey">API key
            <input v-model="apiKey" type="password" autocomplete="off" placeholder="Stored with Electron safeStorage">
          </label>
          <div class="secret-row">
            <span>{{ providerNeedsKey ? secretState : 'No API key required' }}</span>
            <button v-if="providerNeedsKey" type="button" @click="saveApiKey">Save key</button>
          </div>
          <p class="helper">Map commands work locally. General questions use the selected LLM provider.</p>
        </div>
      </section>

      <div class="action-feedback" :class="actionTone" data-testid="action-feedback">
        <span class="feedback-dot" />
        <p>{{ actionStatus }}</p>
      </div>

      <section class="panel-section">
        <h2>1 · Network topology</h2>
        <button data-testid="highlight-downstream" class="action primary" :disabled="busyAction === 'highlight'" @click="highlightDownstream">
          {{ busyAction === 'highlight' ? 'Tracing network…' : 'Highlight downstream chain' }}
        </button>
        <p class="helper">Expected result: the chain turns yellow and the camera flies to the selected network.</p>
      </section>

      <section class="panel-section">
        <h2>2 · Release scenario</h2>
        <label class="field-label" for="release">Reservoir release</label>
        <div class="release-field">
          <input id="release" v-model.number="releaseCms" type="number" min="0" step="100">
          <span>m³/s</span>
        </div>
        <button data-testid="run-scenario" class="action warning" :disabled="busyAction === 'scenario'" @click="runScenario">
          {{ busyAction === 'scenario' ? 'Running scenario…' : 'Run 0D + 1D scenario' }}
        </button>
        <p class="helper">Expected result: river colors/widths update and a draggable timeline appears at the bottom of the map.</p>
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
