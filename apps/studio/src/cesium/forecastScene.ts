import type { HydroState } from '../types'

export type FlowSeverity = 'normal' | 'elevated' | 'high' | 'extreme'
export type ControlRisk = 'normal' | 'warning' | 'flood'

export interface FlowSceneVisual {
  width: number
  wallHeightM: number
  glow: number
  severity: FlowSeverity
}

export interface StorageSceneVisual {
  ratio: number
  radiusScale: number
  columnHeightM: number
}

export interface ControlRiskVisual {
  risk: ControlRisk
  beaconHeightM: number
  pulseRadiusM: number
  scale: number
}

export function stateValueAt(
  states: HydroState[],
  objectId: string,
  variable: string,
  timestampMinutes: number,
): number | null {
  const state = states.find((item) => (
    item.object_id === objectId
    && item.variable === variable
    && item.timestamp_minutes === timestampMinutes
  ))
  return state?.value ?? null
}

export function forecastTimestamps(states: HydroState[]): number[] {
  return [...new Set(states.map((state) => state.timestamp_minutes))].sort((a, b) => a - b)
}

export function flowSceneVisual(flowCms: number | null): FlowSceneVisual {
  const flow = Math.max(0, flowCms ?? 0)
  if (flow >= 2500) return { width: 9, wallHeightM: 2400, glow: 0.55, severity: 'extreme' }
  if (flow >= 1600) return { width: 7.5, wallHeightM: 1800, glow: 0.42, severity: 'high' }
  if (flow >= 800) return { width: 6, wallHeightM: 1200, glow: 0.32, severity: 'elevated' }
  return { width: 4.5, wallHeightM: Math.max(280, 420 + flow * 0.45), glow: 0.22, severity: 'normal' }
}

export function storageSceneVisual(storageM3: number | null, maxStorageM3: number | null): StorageSceneVisual {
  if (storageM3 == null || maxStorageM3 == null || maxStorageM3 <= 0) {
    return { ratio: 0, radiusScale: 0.82, columnHeightM: 500 }
  }
  const ratio = Math.min(1, Math.max(0, storageM3 / maxStorageM3))
  return {
    ratio,
    radiusScale: 0.82 + ratio * 0.34,
    columnHeightM: 500 + ratio * 2200,
  }
}

export function controlRiskVisual(
  flowCms: number | null,
  warningFlowCms: number | null,
  floodFlowCms: number | null,
): ControlRiskVisual {
  const flow = Math.max(0, flowCms ?? 0)
  if (floodFlowCms != null && floodFlowCms > 0 && flow >= floodFlowCms) {
    return { risk: 'flood', beaconHeightM: 5200, pulseRadiusM: 22_000, scale: 1.45 }
  }
  if (warningFlowCms != null && warningFlowCms > 0 && flow >= warningFlowCms) {
    return { risk: 'warning', beaconHeightM: 3600, pulseRadiusM: 16_000, scale: 1.22 }
  }
  return { risk: 'normal', beaconHeightM: 1900, pulseRadiusM: 10_000, scale: 1 }
}
