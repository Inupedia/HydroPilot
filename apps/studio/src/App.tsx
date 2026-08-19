import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { Entity, Viewer } from 'cesium'
import Timeline from './components/Timeline'
import { hydroApi, waitForApi, type LlmProviderSummary } from './api/client'
import { createHydroViewer, renderHydroScene } from './cesium/hydroViewer'
import {
  agentCompatibleProviders,
  buildReadOnlyAgentMessages,
  formatToolExecutionLabel,
  type StudioCopilotMessage,
} from './copilot/agent'
import './copilot/grounding.css'
import { secrets } from './platform/secrets'
import type { HydroObject, HydroState } from './types'

const examples = [
  '这条水网从 reach-001 往下游连接了哪些对象？',
  '当前水网里有哪些工程对象？',
  'reservoir-shasta 有哪些工程曲线和运行约束？',
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
  const [copilotMessages, setCopilotMessages] = useState<StudioCopilotMessage[]>([
    { role: 'assistant', content: 'Ask about objects, downstream topology, curves, or constraints. Highlighting and scenario execution remain explicit controls below.' },
  ])

  const riverCount = useMemo(() => objects.filter((item) => item.object_type === 'river_reach').length, [objects])
  const assetCount = objects.length - riverCount
  const timestamps = useMemo(() => [...new Set(states.map((item) => item.timestamp_minutes))].sort((a, b) => a - b), [states])
  const currentFlow = useMemo(() => {
    const visible = states.filter((item) => item.timestamp_minutes === timestamp && item.variable === 'flow')
    return visible.length ? Math.max(...visible.map((item) => item.value)) : null
  }, [states, timestamp])
  const storageState = states.find((item) => item.timestamp_minutes === timestamp && item.variable === 'storage')
  const agentProviders = useMemo(() => agentCompatibleProviders(providers), [providers])
  const activeProvider = agentProviders.find((item) => item.id === selectedProvider)
  const providerNeedsKey = activeProvider?.auth_required ?? true
  const providerReady = Boolean(activeProvider) && Boolean(selectedModel.trim()) && (selectedProvider !== 'custom-openai' || Boolean(customBaseUrl.trim())) && (!providerNeedsKey || Boolean(apiKey.trim()))

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
        const nextAgentProviders = agentCompatibleProviders(nextProviders)
        const valid = nextAgentProviders.some((item) => item.id === selectedProvider)
        const providerId = valid ? selectedProvider : (nextAgentProviders[0]?.id ?? '')
        if (!providerId) {
          setSelectedProvider('')
          setSelectedModel('')
          setSecretState('No Agent-compatible provider available')
          return
        }
        if (!valid) setSelectedProvider(providerId)
        const provider = nextAgentProviders.find((item) => item.id === providerId)
        if (!valid || !selectedModel.trim()) setSelectedModel(provider?.model_examples[0] ?? '')
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
    const releaseHydrograph = [
      { timestamp_minutes: 0, flow_cms: flow },
      { timestamp_minutes: 180, flow_cms: flow },
    ]
    setBusyAction('scenario'); status(`Running 0D + 1D scenario: inflow ${inflowCms.toLocaleString()} m³/s, release ${flow.toLocaleString()} m³/s…`, 'working')
    try {
      const next = await hydroApi.releaseScenario(inflowHydrograph, releaseHydrograph)
      setStates(next)
      const nextTimes = [...new Set(next.map((item) => item.timestamp_minutes))].sort((a, b) => a - b)
      setTimestamp(nextTimes[0] ?? 0)
      status(`Scenario ready: ${nextTimes.length} time steps with explicit inflow and release schedules.`, 'success')
      return nextTimes.length
    } catch (error) { status(`Scenario failed: ${error instanceof Error ? error.message : String(error)}`, 'error'); throw error }
    finally { setBusyAction('') }
  }, [inflowCms, releaseCms, status])

  async function selectProvider(providerId: string) {
    setSelectedProvider(providerId)
    const provider = agentProviders.find((item) => item.id === providerId)
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
  function addMessage(
    role: 'user' | 'assistant',
    content: string,
    metadata: Partial<Pick<StudioCopilotMessage, 'toolExecutions' | 'providerRounds'>> = {},
  ) {
    setCopilotMessages((current) => [...current, { role, content, ...metadata }].slice(-8))
  }
  async function submitCopilot(text = copilotPrompt) {
    const prompt = text.trim()
    if (!prompt || copilotBusy) return
    setCopilotPrompt(''); addMessage('user', prompt); setCopilotBusy(true)
    try {
      if (!providerReady) {
        setProviderSettingsOpen(true)
        addMessage('assistant', 'The read-only Agent needs an OpenAI-compatible provider, model, and any required credentials. Scenario actions remain available through the explicit controls below.')
        return
      }
      const response = await hydroApi.agentChat({
        provider: selectedProvider,
        model: selectedModel.trim(),
        api_key: apiKey.trim() || undefined,
        base_url: customBaseUrl.trim() || undefined,
        messages: buildReadOnlyAgentMessages(copilotMessages, prompt, {
          objectCount: objects.length,
          riverCount,
          assetCount,
          timestampMinutes: timestamp,
          inflowCms,
          releaseCms,
          peakVisibleFlowCms: currentFlow,
        }),
        temperature: 0.2,
        max_tokens: 1200,
        max_tool_rounds: 4,
      })
      addMessage('assistant', response.text, {
        toolExecutions: response.tool_executions,
        providerRounds: response.provider_rounds,
      })
    } catch (error) { addMessage('assistant', `Request failed: ${error instanceof Error ? error.message : String(error)}`) }
    finally { setCopilotBusy(false) }
  }

  return (
    <main className="app-shell">
      <aside className="control-panel">
        <div className="brand-row"><div className="brand-mark">HP</div><div><p className="eyebrow">HydroPilot v0.3.0 · Tauri</p><h1>Sacramento<br/>Water Network</h1></div></div>
        <p className="note">React + Tauri water-network digital twin. Ask read-only questions above or use the explicit topology and scenario controls below.</p>
        <div className="metric-grid">
          <article><span>River reaches</span><strong>{riverCount}</strong></article><article><span>Engineering assets</span><strong>{assetCount}</strong></article>
          <article><span>Scenario time</span><strong>{timestamp} min</strong></article><article><span>Peak visible flow</span><strong>{currentFlow == null ? '—' : `${currentFlow.toFixed(0)} m³/s`}</strong></article>
        </div>
        <section className="copilot-card" data-testid="copilot-panel">
          <div className="section-heading-row"><div><span className="section-kicker">AI COPILOT</span><h2>Ask the water network</h2></div><span className={`provider-badge ${providerReady ? 'ready' : ''}`}>{providerReady ? activeProvider?.name || 'Ready' : 'Model setup'}</span></div>
          <div className="quick-prompts">{examples.map((example) => <button key={example} type="button" onClick={() => void submitCopilot(example)}>{example}</button>)}</div>
          <div className="copilot-thread" aria-live="polite">{copilotMessages.slice(-4).map((message, index) => <div key={index} className={`copilot-message ${message.role}`}><span>{message.role === 'assistant' ? 'HP' : 'YOU'}</span><div className="copilot-message-content"><p>{message.content}</p>{message.role === 'assistant' && message.toolExecutions?.length ? <div className="agent-grounding"><div className="agent-grounding-header"><span>Grounded by</span>{message.providerRounds ? <small>{message.providerRounds} model rounds</small> : null}</div><div className="agent-grounding-tools">{message.toolExecutions.map((execution) => <code key={execution.call_id} title={formatToolExecutionLabel(execution)}>{formatToolExecutionLabel(execution)}</code>)}</div></div> : null}</div></div>)}</div>
          <form className="copilot-compose" onSubmit={(event) => { event.preventDefault(); void submitCopilot() }}><textarea rows={2} value={copilotPrompt} onChange={(event) => setCopilotPrompt(event.target.value)} placeholder="例如：reach-001 下游有哪些对象？或 reservoir-shasta 有哪些运行约束？"/><button className="send-button" type="submit" disabled={copilotBusy || !copilotPrompt.trim()}>{copilotBusy ? 'Working…' : 'Send'}</button></form>
          <button className="settings-toggle" type="button" onClick={() => setProviderSettingsOpen((value) => !value)}>{providerSettingsOpen ? 'Hide model settings' : 'Model settings'}</button>
          {providerSettingsOpen && <div className="provider-settings">
            <label>Provider<select value={selectedProvider} onChange={(event) => void selectProvider(event.target.value)}>{agentProviders.map((provider) => <option key={provider.id} value={provider.id}>{provider.name}</option>)}</select></label>
            <label>Model<input value={selectedModel} onChange={(event) => setSelectedModel(event.target.value)} placeholder="Model ID"/></label>
            {selectedProvider === 'custom-openai' && <label>Base URL<input value={customBaseUrl} onChange={(event) => setCustomBaseUrl(event.target.value)} placeholder="https://example.com/v1"/></label>}
            {providerNeedsKey && <label>API key<input value={apiKey} onChange={(event) => setApiKey(event.target.value)} type="password" autoComplete="off" placeholder="Stored in the OS credential store"/></label>}
            <div className="secret-row"><span>{providerNeedsKey ? secretState : 'No API key required'}</span>{providerNeedsKey && <button type="button" onClick={() => void saveApiKey()}>Save key</button>}</div>
            <p className="helper">Copilot questions use the read-only Agent. Network highlighting and scenario execution remain explicit controls below.</p>
          </div>}
        </section>
        <div className={`action-feedback ${actionTone}`} data-testid="action-feedback"><span className="feedback-dot"/><p>{actionStatus}</p></div>
        <section className="panel-section"><h2>1 · Network topology</h2><button data-testid="highlight-downstream" className="action primary" disabled={busyAction === 'highlight'} onClick={() => void highlightDownstream()}>{busyAction === 'highlight' ? 'Tracing network…' : 'Highlight downstream chain'}</button><p className="helper">Expected result: the chain turns yellow and the camera flies to it.</p></section>
        <section className="panel-section"><h2>2 · Release scenario</h2><label className="field-label" htmlFor="inflow">Reservoir inflow boundary</label><div className="release-field"><input id="inflow" value={inflowCms} onChange={(event) => setInflowCms(Number(event.target.value))} type="number" min="0" step="100"/><span>m³/s</span></div><label className="field-label" htmlFor="release">Reservoir release</label><div className="release-field"><input id="release" value={releaseCms} onChange={(event) => setReleaseCms(Number(event.target.value))} type="number" min="1" step="100"/><span>m³/s</span></div><button data-testid="run-scenario" className="action warning" disabled={busyAction === 'scenario'} onClick={() => void runScenario()}>{busyAction === 'scenario' ? 'Running scenario…' : 'Run 0D + 1D scenario'}</button><p className="helper">The visible inflow and release values are converted into explicit 180-minute constant hydrographs before simulation.</p></section>
        <div className="status-card" data-testid="scenario-status"><span>Reservoir storage</span><strong>{storageState ? `${(storageState.value / 1e9).toFixed(2)} B m³` : 'Run scenario'}</strong></div>
        <div className="legend"><span><i className="legend-line river"/>River</span><span><i className="legend-dot reservoir"/>Reservoir</span><span><i className="legend-dot dam"/>Dam</span><span><i className="legend-dot gauge"/>Gauge</span><span><i className="legend-dot control"/>Control point</span></div>
      </aside>
      <section className="map-stage"><div ref={mapHost} className="cesium-host" data-testid="cesium-host"/><div className="map-header"><div><span className="live-dot"/> CESIUM 3D / EPSG:4326</div><div>{objects.length} OBJECTS · PUBLIC DEMO DATA</div></div><div className="map-title-card"><span>Water-network digital twin</span><strong>Shasta → Sacramento control section</strong></div><Timeline timestamps={timestamps} timestamp={timestamp} onChange={(value) => setTimestamp(value)}/></section>
    </main>
  )
}