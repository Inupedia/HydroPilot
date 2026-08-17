import { describe, expect, it } from 'vitest'
import { classifyObject } from '../src/rendering/renderSpec'

const object = { id: 'reach-001', name: 'Reach', object_type: 'river_reach' as const, geometry: { type: 'LineString' as const, coordinates: [] }, properties: {} }

describe('classifyObject', () => {
  it('marks highlighted river reaches', () => {
    const spec = classifyObject(object, new Set(['reach-001']))
    expect(spec.kind).toBe('river')
    expect(spec.highlighted).toBe(true)
  })
})
