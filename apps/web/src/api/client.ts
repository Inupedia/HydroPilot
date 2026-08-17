import type { HydroObject, HydroState, NetworkPathItem } from '../types'

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

export interface LlmProviderSummary {
  id: string
  name: string
  adapter_family: string
  default_base_url: string | null
  api_key_env: string | null
  auth_required: boolean
  model_examples: string[]
}

export interface LlmChatMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

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

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
  return response.json() as Promise<T>
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
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

export const hydroApi = {
  objects: () => getJson<HydroObject[]>('/api/objects'),
  downstream: (id: string, maxHops = 8) => getJson<NetworkPathItem[]>(`/api/network/${id}/downstream?max_hops=${maxHops}`),
  async releaseScenario(release_cms: number): Promise<HydroState[]> {
    const result = await postJson<{ states: HydroState[] }>('/api/scenarios/release', {
      release_cms,
      duration_minutes: 180,
      dt_minutes: 30,
      max_hops: 6,
    })
    return result.states
  },
  llmProviders: () => getJson<LlmProviderSummary[]>('/api/llm/providers'),
  llmChat: (request: LlmChatRequest) => postJson<LlmChatResponse>('/api/llm/chat', request),
}
