import { describe, expect, it } from 'vitest'
import { classifyObject } from '../src/rendering/renderSpec'

const object = { id: 'reach-001', name: 'Reach', object_type: 'river_reach' as const, geometry: { type: 'LineString' as const, coordinates: [] }, properties: {} }

describe('classifyObject', () => {
  it('marks highlighted river reaches and flood status', () => {
    const spec = classifyObject(object, new Set(['reach-001']), [{ scenario_id: 's', object_id: 'reach-001', timestamp_minutes: 0, variable: 'flow', value: 3000, unit: 'm3/s' }])
    expect(spec.kind).toBe('river')
    expect(spec.highlighted).toBe(true)
    expect(spec.status).toBe('flood')
  })
})
