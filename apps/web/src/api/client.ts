import type { HydroObject, NetworkPathItem } from '../types'

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
  return response.json() as Promise<T>
}

export const hydroApi = {
  objects: () => getJson<HydroObject[]>('/api/objects'),
  downstream: (id: string, maxHops = 8) => getJson<NetworkPathItem[]>(`/api/network/${id}/downstream?max_hops=${maxHops}`),
}
