import type { HydroObject, HydroState } from '../types'

export type RenderKind = 'river' | 'structure' | 'station' | 'control'
export interface RenderSpec { id: string; label: string; kind: RenderKind; highlighted: boolean; status: 'normal' | 'warning' | 'flood' }

export function classifyObject(object: HydroObject, highlightedIds: Set<string>, states: HydroState[] = []): RenderSpec {
  const state = states.find((item) => item.object_id === object.id && item.variable === 'flow')
  let status: RenderSpec['status'] = 'normal'
  if (state && state.value > 2800) status = 'flood'
  else if (state && state.value > 1800) status = 'warning'
  const kind: RenderKind = object.object_type === 'river_reach' ? 'river' : object.object_type === 'gauge' ? 'station' : object.object_type === 'control_point' ? 'control' : 'structure'
  return { id: object.id, label: object.name, kind, highlighted: highlightedIds.has(object.id), status }
}
