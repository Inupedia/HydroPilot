import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  hydroApi,
  type ReleaseScenarioResponse,
} from '../src/api/client'
import {
  constraintResultSummary,
  formatConstraintViolation,
  formatUnevaluatedConstraint,
} from '../src/scenario/results'

afterEach(() => {
  vi.restoreAllMocks()
  delete window.__TAURI_INTERNALS__
})

const response: ReleaseScenarioResponse = {
  scenario_id: 'scenario-test',
  states: [
    {
      scenario_id: 'scenario-test',
      object_id: 'reservoir-shasta',
      timestamp_minutes: 0,
      variable: 'storage',
      value: 4_100_000_000,
      unit: 'm3',
    },
  ],
  violations: [
    {
      constraint_id: 'constraint-release-max',
      object_id: 'reservoir-shasta',
      variable: 'release',
      timestamp_minutes: 30,
      value: 2600,
      unit: 'm3/s',
      constraint_type: 'maximum',
      min_value: null,
      max_value: 2500,
      source: 'demo rulebook',
    },
  ],
  unevaluated_constraints: [
    {
      constraint_id: 'constraint-seasonal',
      object_id: 'reservoir-shasta',
      variable: 'level',
      reason: 'conditional constraint active_when is not evaluated',
    },
  ],
}

describe('Studio scenario constraint results', () => {
  it('preserves the complete release scenario response instead of dropping constraint results', async () => {
    const fetchMock = vi.spyOn(window, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(response), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    )

    const result = await hydroApi.releaseScenario(
      [
        { timestamp_minutes: 0, flow_cms: 1000 },
        { timestamp_minutes: 180, flow_cms: 1000 },
      ],
      [
        { timestamp_minutes: 0, flow_cms: 2600 },
        { timestamp_minutes: 180, flow_cms: 2600 },
      ],
    )

    expect(result).toEqual(response)
    expect(result.violations).toHaveLength(1)
    expect(result.unevaluated_constraints).toHaveLength(1)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('never describes zero detected violations as operational compliance', () => {
    const summary = constraintResultSummary({
      ...response,
      violations: [],
      unevaluated_constraints: [],
    })

    expect(summary.counts).toBe('0 violations · 0 unevaluated')
    expect(summary.message).toContain('No violations were found among configured constraints that could be evaluated.')
    expect(summary.message).toContain('not an operational compliance determination')
    expect(summary.message.toLowerCase()).not.toContain('fully compliant')
  })

  it('summarizes detected and unevaluated constraints separately', () => {
    const summary = constraintResultSummary(response)

    expect(summary.counts).toBe('1 violation · 1 unevaluated')
    expect(summary.message).toContain('1 configured constraint violation detected')
    expect(summary.message).toContain('1 constraint could not be evaluated')
  })

  it('formats violation and unevaluated details with source and reason', () => {
    expect(formatConstraintViolation(response.violations[0])).toContain(
      'constraint-release-max · reservoir-shasta.release · 2600 m3/s @ 30 min · maximum ≤ 2500 · demo rulebook',
    )
    expect(formatUnevaluatedConstraint(response.unevaluated_constraints[0])).toBe(
      'constraint-seasonal · reservoir-shasta.level · conditional constraint active_when is not evaluated',
    )
  })
})
