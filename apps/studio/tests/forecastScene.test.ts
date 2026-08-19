import { describe, expect, it } from 'vitest'
import { flowSceneVisual, forecastTimestamps, stateValueAt, storageSceneVisual } from '../src/cesium/forecastScene'
import type { HydroState } from '../src/types'

const states: HydroState[] = [
  { scenario_id: 'forecast', object_id: 'reach-001', timestamp_minutes: 60, variable: 'flow', value: 1700, unit: 'm3/s' },
  { scenario_id: 'forecast', object_id: 'reservoir-shasta', timestamp_minutes: 0, variable: 'storage', value: 4_100_000_000, unit: 'm3' },
  { scenario_id: 'forecast', object_id: 'reach-001', timestamp_minutes: 30, variable: 'flow', value: 1200, unit: 'm3/s' },
]

describe('forecast scene helpers', () => {
  it('extracts exact state values and sorted timestamps', () => {
    expect(stateValueAt(states, 'reach-001', 'flow', 30)).toBe(1200)
    expect(stateValueAt(states, 'reach-001', 'flow', 90)).toBeNull()
    expect(forecastTimestamps(states)).toEqual([0, 30, 60])
  })

  it('increases 3D flow emphasis as discharge rises', () => {
    const normal = flowSceneVisual(500)
    const high = flowSceneVisual(1800)
    const extreme = flowSceneVisual(2800)

    expect(high.wallHeightM).toBeGreaterThan(normal.wallHeightM)
    expect(extreme.width).toBeGreaterThan(high.width)
    expect(extreme.severity).toBe('extreme')
  })

  it('maps storage ratio into reservoir footprint and column height', () => {
    const half = storageSceneVisual(50, 100)
    const full = storageSceneVisual(100, 100)

    expect(half.ratio).toBe(0.5)
    expect(full.columnHeightM).toBeGreaterThan(half.columnHeightM)
    expect(full.radiusScale).toBeGreaterThan(half.radiusScale)
  })
})
