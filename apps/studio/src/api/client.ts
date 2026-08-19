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
export interface ScenarioHydrographPoint {
  timestamp_minutes: number
  flow_cms: number
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
  async releaseScenario(release_cms: number, inflow_hydrograph: ScenarioHydrographPoint[]): Promise<HydroState[]> {
    const result = await postJson<{ states: HydroState[] }>('/api/scenarios/release', {
      release_cms,
      duration_minutes: 180,
      dt_minutes: 30,
      max_hops: 6,
      inflow_hydrograph,
    })
    return result.states
  },
  llmProviders: () => getJson<LlmProviderSummary[]>('/api/llm/providers'),
  llmChat: (request: LlmChatRequest) => postJson<LlmChatResponse>('/api/llm/chat', request),
}
