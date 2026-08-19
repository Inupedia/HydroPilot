import { invoke } from '@tauri-apps/api/core'
import { fetch as tauriFetch } from '@tauri-apps/plugin-http'
import type { HydroObject, HydroState, NetworkPathItem } from '../types'

const DEFAULT_API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000'
let apiBase = DEFAULT_API_BASE
let apiBaseConfigured = false

declare global {
  interface Window { __TAURI_INTERNALS__?: unknown }
}

export interface LlmProviderSummary {
  id: string
  name: string
  adapter_family: string
  default_base_url: string | null
  api_key_env: string | null
  auth_required: boolean
  model_examples: string[]
}
export interface LlmChatMessage { role: 'system' | 'user' | 'assistant'; content: string }
export interface LlmChatRequest {
  provider: string
  model: string
  messages: LlmChatMessage[]
  api_key?: string
  base_url?: string
  temperature?: number
  max_tokens?: number
}
export interface LlmChatResponse {
  provider: string
  model: string
  text: string
  usage?: Record<string, unknown> | null
}
export interface AgentChatMessage { role: 'user' | 'assistant'; content: string }
export interface AgentChatRequest {
  provider: string
  model: string
  messages: AgentChatMessage[]
  api_key?: string
  base_url?: string
  temperature?: number
  max_tokens?: number
  max_tool_rounds?: number
}
export interface AgentToolExecution {
  call_id: string
  name: string
  arguments: Record<string, unknown>
  result: unknown
}
export interface AgentChatResponse {
  provider: string
  model: string
  text: string
  tool_executions: AgentToolExecution[]
  provider_rounds: number
}
export interface ScenarioHydrographPoint {
  timestamp_minutes: number
  flow_cms: number
}
export interface FlowObservation {
  timestamp_minutes: number
  flow_cms: number
}
export interface FlowForecastPoint {
  timestamp_minutes: number
  flow_cms: number
}
export interface FlowForecastSummary {
  current_flow_cms: number
  peak_flow_cms: number
  peak_timestamp_minutes: number
  peak_change_pct: number | null
  trend: 'rising' | 'falling' | 'steady'
}
export interface FlowForecastRequest {
  object_id: string
  history: FlowObservation[]
  horizon_minutes?: number
  dt_minutes?: number
  model?: 'persistence' | 'damped_trend'
  trend_window_points?: number
  damping?: number
}
export interface FlowForecastResponse {
  object_id: string
  model: 'persistence' | 'damped_trend'
  horizon_minutes: number
  dt_minutes: number
  forecast: FlowForecastPoint[]
  summary: FlowForecastSummary
}
export interface RainfallForecastPoint {
  timestamp_minutes: number
  precipitation_mm: number
}
export interface RunoffForecastRequest {
  object_id: string
  rainfall: RainfallForecastPoint[]
  dt_minutes?: number
  initial_flow_cms: number
  catchment_area_km2: number
  runoff_coefficient?: number
  response_time_hours?: number
  baseflow_cms?: number
}
export interface RunoffForecastPoint {
  timestamp_minutes: number
  rainfall_mm: number
  flow_cms: number
}
export interface RunoffForecastSummary {
  current_flow_cms: number
  peak_flow_cms: number
  peak_timestamp_minutes: number
  peak_change_pct: number | null
  total_rainfall_mm: number
}
export interface RunoffForecastResponse {
  object_id: string
  model: string
  dt_minutes: number
  horizon_minutes: number
  runoff: RunoffForecastPoint[]
  summary: RunoffForecastSummary
}
export interface ReservoirRainfallForecastRequest {
  reservoir_id: string
  rainfall: RainfallForecastPoint[]
  dt_minutes?: number
  initial_inflow_cms: number
  release_cms: number
  release_response_fraction?: number
  max_release_cms?: number
  catchment_area_km2: number
  runoff_coefficient?: number
  response_time_hours?: number
  baseflow_cms?: number
  max_hops?: number
}
export interface ReservoirForecastSummary {
  current_storage_m3: number
  final_storage_m3: number
  min_storage_m3: number
  max_storage_m3: number
  storage_change_m3: number
  storage_change_pct: number | null
  peak_inflow_cms: number
  peak_inflow_timestamp_minutes: number
  release_cms: number
  peak_release_cms: number
  release_response_fraction: number
  final_level_m: number | null
}
export interface ReservoirRainfallForecastResponse {
  reservoir_id: string
  model: string
  runoff: RunoffForecastResponse
  scenario: {
    scenario_id: string
    states: HydroState[]
    violations: unknown[]
    unevaluated_constraints: unknown[]
  }
  summary: ReservoirForecastSummary
}

function inTauri(): boolean {
  return Boolean(window.__TAURI_INTERNALS__)
}

export async function configureApiBase(): Promise<string> {
  if (!apiBaseConfigured && inTauri()) {
    apiBase = await invoke<string>('api_base_url')
  }
  apiBaseConfigured = true
  return apiBase
}

export function currentApiBase(): string {
  return apiBase
}

function runtimeFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  if (inTauri()) return tauriFetch(input, init)
  return window.fetch(input, init)
}

async function getJson<T>(path: string): Promise<T> {
  const response = await runtimeFetch(`${apiBase}${path}`)
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
  return response.json() as Promise<T>
}
async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await runtimeFetch(`${apiBase}${path}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null
    throw new Error(payload?.detail || `${response.status} ${response.statusText}`)
  }
  return response.json() as Promise<T>
}

export async function waitForApi(timeoutMs = 20_000): Promise<void> {
  await configureApiBase()
  const started = Date.now()
  let lastError: unknown
  while (Date.now() - started < timeoutMs) {
    try {
      const response = await runtimeFetch(`${apiBase}/health`)
      if (response.ok) return
      lastError = new Error(`${response.status} ${response.statusText}`)
    } catch (error) { lastError = error }
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  throw new Error(`HydroPilot API did not become ready at ${apiBase}: ${lastError instanceof Error ? lastError.message : String(lastError ?? 'unknown error')}`)
}

export const hydroApi = {
  objects: () => getJson<HydroObject[]>('/api/objects'),
  downstream: (id: string, maxHops = 8) => getJson<NetworkPathItem[]>(`/api/network/${id}/downstream?max_hops=${maxHops}`),
  async releaseScenario(
    inflow_hydrograph: ScenarioHydrographPoint[],
    release_hydrograph: ScenarioHydrographPoint[],
  ): Promise<HydroState[]> {
    const result = await postJson<{ states: HydroState[] }>('/api/scenarios/release', {
      duration_minutes: 180,
      dt_minutes: 30,
      max_hops: 6,
      inflow_hydrograph,
      release_hydrograph,
    })
    return result.states
  },
  flowForecast: (request: FlowForecastRequest) => postJson<FlowForecastResponse>('/api/forecasts/flow', request),
  runoffForecast: (request: RunoffForecastRequest) => postJson<RunoffForecastResponse>('/api/forecasts/runoff', request),
  reservoirForecast: (request: ReservoirRainfallForecastRequest) => postJson<ReservoirRainfallForecastResponse>('/api/forecasts/reservoir', request),
  llmProviders: () => getJson<LlmProviderSummary[]>('/api/llm/providers'),
  llmChat: (request: LlmChatRequest) => postJson<LlmChatResponse>('/api/llm/chat', request),
  agentChat: (request: AgentChatRequest) => postJson<AgentChatResponse>('/api/agent/chat', request),
}
