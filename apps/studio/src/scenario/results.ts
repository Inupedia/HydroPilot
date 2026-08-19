import type {
  ConstraintViolation,
  ReleaseScenarioResponse,
  UnevaluatedConstraint,
} from '../api/client'

export interface ScenarioConstraintSummary {
  counts: string
  message: string
  tone: 'clear' | 'warning'
}

function plural(count: number, singular: string, pluralValue = `${singular}s`): string {
  return count === 1 ? singular : pluralValue
}

export function constraintResultSummary(result: ReleaseScenarioResponse): ScenarioConstraintSummary {
  const violationCount = result.violations.length
  const unevaluatedCount = result.unevaluated_constraints.length
  const counts = `${violationCount} ${plural(violationCount, 'violation')} · ${unevaluatedCount} unevaluated`

  if (violationCount === 0) {
    const unevaluatedSuffix = unevaluatedCount > 0
      ? ` ${unevaluatedCount} ${plural(unevaluatedCount, 'constraint')} could not be evaluated.`
      : ''
    return {
      counts,
      tone: unevaluatedCount > 0 ? 'warning' : 'clear',
      message: `No violations were found among configured constraints that could be evaluated.${unevaluatedSuffix} This is not an operational compliance determination.`,
    }
  }

  const unevaluatedSuffix = unevaluatedCount > 0
    ? ` ${unevaluatedCount} ${plural(unevaluatedCount, 'constraint')} could not be evaluated.`
    : ''
  return {
    counts,
    tone: 'warning',
    message: `${violationCount} configured ${plural(violationCount, 'constraint')} ${plural(violationCount, 'violation')} detected.${unevaluatedSuffix}`,
  }
}

function thresholdLabel(violation: ConstraintViolation): string {
  if (violation.constraint_type === 'minimum') return `≥ ${violation.min_value}`
  if (violation.constraint_type === 'maximum' || violation.constraint_type === 'ramp_rate') return `≤ ${violation.max_value}`
  if (violation.constraint_type === 'range') return `${violation.min_value}–${violation.max_value}`
  return ''
}

export function formatConstraintViolation(violation: ConstraintViolation): string {
  const threshold = thresholdLabel(violation)
  return [
    violation.constraint_id,
    `${violation.object_id}.${violation.variable}`,
    `${violation.value} ${violation.unit} @ ${violation.timestamp_minutes} min`,
    `${violation.constraint_type}${threshold ? ` ${threshold}` : ''}`,
    violation.source,
  ].join(' · ')
}

export function formatUnevaluatedConstraint(item: UnevaluatedConstraint): string {
  return `${item.constraint_id} · ${item.object_id}.${item.variable} · ${item.reason}`
}
