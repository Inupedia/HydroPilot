import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { Entity, Viewer } from 'cesium'
import Timeline from './components/Timeline'
import { hydroApi, waitForApi, type LlmChatMessage, type LlmProviderSummary } from './api/client'
import { createHydroViewer, renderHydroScene } from './cesium/hydroViewer'
import { parseCopilotCommand } from './copilot/commands'
import { secrets } from './platform/secrets'
import type { HydroObject, HydroState } from './types'

const examples = [
  '高亮这条水网的下游链路',
  '按 2200 m³/s 运行下泄调度场景',
  '解释当前水网里有哪些工程对象',
]

type Tone = 'idle' | 'working' | 'success' | 'error'

export default function App() {
  const mapHost = useRef<HTMLDivElement | null>(null)
  const viewerRef = useRef<Viewer | null>(null)
  const [objects, setObjects] = useState<HydroObject[]>([])
  const [highlightedIds, setHighlightedIds] = useState<Set<string>>(new Set())
  const [states, setStates] = useState<HydroState[]>([])
  const [timestamp, setTimestamp] = useState(0)
  const [releaseCms, setReleaseCms] = useState(2200)
  const [inflowCms, setInflowCms] = useState(1000)
  const [busyAction, setBusyAction] = useState('')
  const [actionStatus, setActionStatus] = useState('Ready — try one of the guided actions below.')
  const [actionTone, setActionTone] = useState<Tone>('idle')
  const [providers, setProviders] = useState<LlmProviderSummary[]>([])
  const [selectedProvider, setSelectedProvider] = useState(() => localStorage.getItem('hydropilot.llm.provider') || 'openai')
  const [selectedModel, setSelectedModel] = useState(() => localStorage.getItem('hydropilot.llm.model') || '')
  const [apiKey, setApiKey] = useState('')
  const [customBaseUrl, setCustomBaseUrl] = useState(() => localStorage.getItem('hydropilot.llm.baseUrl') || '')
  const [providerSettingsOpen, setProviderSettingsOpen] = useState(true)
  const [secretState, setSecretState] = useState('')
  const [copilotPrompt, setCopilotPrompt] = useState('')
  const [copilotBusy, setCopilotBusy] = useState(false)
  const [copilotMessages, setCopilotMessages] = useState<LlmChatMessage[]>([
    { role: 'assistant', content: 'Start with a suggested command. Map-control commands work before you configure an LLM.' },
  ])

  const riverCount = useMemo(() => objects.filter((item) => item.object_type === 'river_reach').length, [objects])
  const assetCount = objects.length - riverCount
  const timestamps = useMemo(() => [...new Set(states.map((item) => item.timestamp_minutes))].sort((a, b) => a - b), [states])
  const currentFlow = useMemo(() => {
    const visible = states.filter((item) => item.timestamp_minutes === timestamp && item.variable === 'flow')
    return visible.length ? Math.max(...visible.map((item) => item.value)) : null
  }, [states, timestamp])
  const storageState = states.find((item) => item.timestamp_minutes === timestamp && item.variable === 'storage')
  const activeProvider = providers.find((item) => item.id === selectedProvider)
  const providerNeedsKey = activeProvider?.auth_required ?? true
  const providerReady = Boolean(selectedModel.trim()) && (selectedProvider !== 'custom-openai' || Boolean(customBaseUrl.trim())) && (!providerNeedsKey || Boolean(apiKey.trim()))

  const status = useCallback((message: string, tone: Tone = 'idle') => { setActionStatus(message); setActionTone(tone) }, [])
  const loadApiKey = useCallback(async (providerId: string) => {
    setSecretState('')
    const value = await secrets.get(`llm:${providerId}`)
    setApiKey(value || '')
    setSecretState(value ? 'Saved securely or for this session' : 'No saved key')
  }, [])

  useEffect(() => {
    if (!mapHost.current) return
    const viewer = createHydroViewer(mapHost.current)
    viewerRef.current = viewer
    let cancelled = false
    ;(async () => {
      try {
        await waitForApi()
        const [nextObjects, nextProviders] = await Promise.all([hydroApi.objects(), hydroApi.llmProviders()])
        if (cancelled) return
        setObjects(nextObjects)
        setProviders(nextProviders)
        const valid = nextProviders.some((item) => item.id === selectedProvider)
        const providerId = valid ? selectedProvider : (nextProviders[0]?.id ?? selectedProvider)
        if (!valid) setSelectedProvider(providerId)
        const provider = nextProviders.find((item) => item.id === providerId)
        if (!selectedModel && provider?.model_examples.length) setSelectedModel(provider.model_examples[0])
        await loadApiKey(providerId)
      } catch (error) {
        status(`Startup error: ${error instanceof Error ? error.message : String(error)}`, 'error')
      }
    })()
    return () => { cancelled = true; if (!viewer.isDestroyed()) viewer.destroy(); viewerRef.current = null }
  }, [])

  useEffect(() => {
    if (viewerRef.current && objects.length) renderHydroScene(viewerRef.current, objects, highlightedIds, states, timestamp)
  }, [objects, highlightedIds, states, timestamp])

  useEffect(() => { localStorage.setItem('hydropilot.llm.provider', selectedProvider) }, [selectedProvider])
  useEffect(() => { localStorage.setItem('hydropilot.llm.model', selectedModel) }, [selectedModel])
  useEffect(() => { localStorage.setItem('hydropilot.llm.baseUrl', customBaseUrl) }, [customBaseUrl])

  const focusHighlighted = useCallback(async (ids: Set<string>) => {
    const viewer = viewerRef.current
    if (!viewer) return
    const entities = Array.from(ids).map((id) => viewer.entities.getById(id)).filter((entity): entity is Entity => Boolean(entity))
    if (entities.length) await viewer.flyTo(entities, { duration: 1.1 })
  }, [])

  const highlightDownstream = useCallback(async () => {
    setBusyAction('highlight'); status('Tracing the directed FLOWS_TO network…', 'working')
    try {
      const path = await hydroApi.downstream('reach-001')
      const ids = new Set(['reach-001', ...path.map((item) => item.object_id)])
      setHighlightedIds(ids)
      setTimeout(() => { void focusHighlighted(ids) }, 0)
      status(`Highlighted ${ids.size} connected objects and moved the camera to them.`, 'success')
      return ids.size
    } catch (error) { status(`Could not highlight network: ${error instanceof Error ? error.message : String(error)}`, 'error'); throw error }
    finally { setBusyAction('') }
  }, [focusHighlighted, status])

  const runScenario = useCallback(async (flow = releaseCms) => {
    const inflowHydrograph = [
      { timestamp_minutes: 0, flow_cms: inflowCms },
      { timestamp_minutes: 180, flow_cms: inflowCms },
    ]
    setBusyAction('scenario'); status(`Running 0D + 1D scenario: inflow ${inflowCms.toLocaleString()} m³/s, release ${flow.toLocaleString()} m³/s…`, 'working')
    try {
      const next = await hydroApi.releaseScenario(flow, inflowHydrograph)
      setStates(next)
      const nextTimes = [...new Set(next.map((item) => item.timestamp_minutes))].sort((a, b) => a - b)
      setTimestamp(nextTimes[0] ?? 0)
      status(`Scenario ready: ${nextTimes.length} time steps with an explicit ${inflowCms.toLocaleString()} m³/s inflow boundary.`, 'success')
      return nextTimes.length
    } catch (error) { status(`Scenario failed: ${error instanceof Error ? error.message : String(error)}`, 'error'); throw error }
    finally { setBusyAction('') }
  }, [inflowCms, releaseCms, status])

  async function selectProvider(providerId: string) {
    setSelectedProvider(providerId)
    const provider = providers.find((item) => item.id === providerId)
    setSelectedModel(provider?.model_examples[0] ?? '')
    await loadApiKey(providerId)
  }
  async function saveApiKey() {
    try {
      if (apiKey.trim()) {
        const mode = await secrets.set(`llm:${selectedProvider}`, apiKey.trim())
        setSecretState(mode === 'secure' ? 'Saved in the OS credential store' : 'Saved for this session')
      } else {
        await secrets.remove(`llm:${selectedProvider}`); setSecretState('Saved key removed')
      }
    } catch (error) { setSecretState(`Could not save key: ${error instanceof Error ? error.message : String(error)}`) }
  }
  function addMessage(role: 'user' | 'assistant', content: string) {
    setCopilotMessages((current) => [...current, { role, content }].slice(-8))
  }
  async function submitCopilot(text = copilotPrompt) {
    const prompt = text.trim()
    if (!prompt || copilotBusy) return
    setCopilotPrompt(''); addMessage('user', prompt); setCopilotBusy(true)
    try {
      const command = parseCopilotCommand(prompt)
      if (command.type === 'highlight-downstream') {
        const count = await highlightDownstream(); addMessage('assistant', `Done. I highlighted ${count} objects in the downstream chain.`); return
      }
      if (command.type === 'run-release') {
        setReleaseCms(command.releaseCms); await runScenario(command.releaseCms); addMessage('assistant', `Done. I ran the ${command.releaseCms.toLocaleString()} m³/s release against the current ${inflowCms.toLocaleString()} m³/s inflow boundary. Drag the timeline to inspect propagation.`); return
      }
      if (!providerReady) {
        setProviderSettingsOpen(true); addMessage('assistant', 'This question needs an LLM. Choose a provider, model, and API key first. Map-control commands work without an LLM.'); return
      }
      const system = `You are HydroPilot, a concise water-network GIS copilot. This is a public-data demonstrator, not operational flood-control decision support. Current scene: ${objects.length} objects, ${riverCount} river reaches, ${assetCount} engineering assets. Current scenario time: ${timestamp} minutes. Manual reservoir inflow boundary: ${inflowCms} m3/s. ${currentFlow == null ? 'No routing scenario is active.' : `Peak visible flow is ${currentFlow.toFixed(0)} m3/s.`}`
      const response = await hydroApi.llmChat({ provider: selectedProvider, model: selectedModel.trim(), api_key: apiKey.trim() || undefined, base_url: customBaseUrl.trim() || undefined, messages: [{ role: 'system', content: system }, ...copilotMessages.slice(-5).filter((message) => message.role !== 'system'), { role: 'user', content: prompt }], temperature: 0.2, max_tokens: 1200 })
      addMessage('assistant', response.text)
    } catch (error) { addMessage('assistant', `Request failed: ${error instanceof Error ? error.message : String(error)}`) }
    finally { setCopilotBusy(false) }
  }

  return (
    <main className="app-shell">
      <aside className="control-panel">
        <div className="brand-row"><div className="brand-mark">HP</div><div><p className="eyebrow">HydroPilot v0.3.0 · Tauri</p><h1>Sacramento<br/>Water Network</h1></div></div>
        <p className="note">React + Tauri water-network digital twin. Start with a guided command; every action reports what changed.</p>
        <div className="metric-grid">
          <article><span>River reaches</span><strong>{riverCount}</strong></article><article><span>Engineering assets</span><strong>{assetCount}</strong></article>
          <article><span>Scenario time</span><strong>{timestamp} min</strong></article><article><span>Peak visible flow</span><strong>{currentFlow == null ? '—' : `${currentFlow.toFixed(0)} m³/s`}</strong></article>
        </div>
        <section className="copilot-card" data-testid="copilot-panel">
          <div className="section-heading-row"><div><span className="section-kicker">AI COPILOT</span><h2>Tell the map what to do</h2></div><span className={`provider-badge ${providerReady ? 'ready' : ''}`}>{providerReady ? activeProvider?.name || 'Ready' : 'Model setup'}</span></div>
          <div className="quick-prompts">{examples.map((example) => <button key={example} type="button" onClick={() => void submitCopilot(example)}>{example}</button>)}</div>
          <div className="copilot-thread" aria-live="polite">{copilotMessages.slice(-4).map((message, index) => <div key={index} className={`copilot-message ${message.role}`}><span>{message.role === 'assistant' ? 'HP' : 'YOU'}</span><p>{message.content}</p></div>)}</div>
          <form className="copilot-compose" onSubmit={(event) => { event.preventDefault(); void submitCopilot() }}><textarea rows={2} value={copilotPrompt} onChange={(event) => setCopilotPrompt(event.target.value)} placeholder="例如：按 2600 m³/s 跑一次调度，或者问当前水网有什么对象"/><button className="send-button" type="submit" disabled={copilotBusy || !copilotPrompt.trim()}>{copilotBusy ? 'Working…' : 'Send'}</button></form>
          <button className="settings-toggle" type="button" onClick={() => setProviderSettingsOpen((value) => !value)}>{providerSettingsOpen ? 'Hide model settings' : 'Model settings'}</button>
          {providerSettingsOpen && <div className="provider-settings">
            <label>Provider<select value={selectedProvider} onChange={(event) => void selectProvider(event.target.value)}>{providers.map((provider) => <option key={provider.id} value={provider.id}>{provider.name}</option>)}</select></label>
            <label>Model<input value={selectedModel} onChange={(event) => setSelectedModel(event.target.value)} placeholder="Model ID"/></label>
            {selectedProvider === 'custom-openai' && <label>Base URL<input value={customBaseUrl} onChange={(event) => setCustomBaseUrl(event.target.value)} placeholder="https://example.com/v1"/></label>}
            {providerNeedsKey && <label>API key<input value={apiKey} onChange={(event) => setApiKey(event.target.value)} type="password" autoComplete="off" placeholder="Stored in the OS credential store"/></label>}
            <div className="secret-row"><span>{providerNeedsKey ? secretState : 'No saved key'}</span>{providerNeedsKey && <button type="button" onClick={() => void saveApiKey()}>Save key</button>}</div>
            <p className="helper">Map commands work locally. General questions use the selected LLM provider.</p>
          </div>}
        </section>
        <div className={`action-feedback ${actionTone}`} data-testid="action-feedback"><span className="feedback-dot"/><p>{actionStatus}</p></div>
        <section className="panel-section"><h2>1 · Network topology</h2><button data-testid="highlight-downstream" className="action primary" disabled={busyAction === 'highlight'} onClick={() => void highlightDownstream()}>{busyAction === 'highlight' ? 'Tracing network…' : 'Highlight downstream chain'}</button><p className="helper">Expected result: the chain turns yellow and the camera flies to it.</p></section>
        <section className="panel-section"><h2>2 · Release scenario</h2><label className="field-label" htmlFor="inflow">Reservoir inflow boundary</label><div className="release-field"><input id="inflow" value={inflowCms} onChange={(event) => setInflowCms(Number(event.target.value))} type="number" min="0" step="100"/><span>m³/s</span></div><label className="field-label" htmlFor="release">Reservoir release</label><div className="release-field"><input id="release" value={releaseCms} onChange={(event) => setReleaseCms(Number(event.target.value))} type="number" min="1" step="100"/><span>m³/s</span></div><button data-testid="run-scenario" className="action warning" disabled={busyAction === 'scenario'} onClick={() => void runScenario()}>{busyAction === 'scenario' ? 'Running scenario…' : 'Run 0D + 1D scenario'}</button><p className="helper">The 180-minute demo uses the visible inflow as an explicit constant boundary; release is the control input.</p></section>
        <div className="status-card" data-testid="scenario-status"><span>Reservoir storage</span><strong>{storageState ? `${(storageState.value / 1e9).toFixed(2)} B m³` : 'Run scenario'}</strong></div>
        <div className="legend"><span><i className="legend-line river"/>River</span><span><i className="legend-dot reservoir"/>Reservoir</span><span><i className="legend-dot dam"/>Dam</span><span><i className="legend-dot gauge"/>Gauge</span><span><i className="legend-dot control"/>Control point</span></div>
      </aside>
      <section className="map-stage"><div ref={mapHost} className="cesium-host" data-testid="cesium-host"/><div className="map-header"><div><span className="live-dot"/> CESIUM 3D / EPSG:4326</div><div>{objects.length} OBJECTS · PUBLIC DEMO DATA</div></div><div className="map-title-card"><span>Water-network digital twin</span><strong>Shasta → Sacramento control section</strong></div>{states.length > 0 && <Timeline timestamps={timestamps} timestamp={timestamp} onChange={(value) => setTimestamp(value)}/>}</section>
    </main>
  )
}