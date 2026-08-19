import type {
  AgentChatMessage,
  AgentToolExecution,
  LlmProviderSummary,
} from '../api/client'

export interface StudioAgentContext {
  objectCount: number
  riverCount: number
  assetCount: number
  timestampMinutes: number
  inflowCms: number
  releaseCms: number
  peakVisibleFlowCms: number | null
}

export interface StudioCopilotMessage extends AgentChatMessage {
  toolExecutions?: AgentToolExecution[]
  providerRounds?: number
}

export function agentCompatibleProviders(providers: LlmProviderSummary[]): LlmProviderSummary[] {
  return providers.filter((provider) => provider.adapter_family === 'openai-compatible')
}

function compactArgumentValue(value: unknown): string {
  let rendered: string
  if (typeof value === 'string') rendered = value
  else if (value === null || typeof value === 'number' || typeof value === 'boolean') rendered = String(value)
  else rendered = JSON.stringify(value) ?? String(value)

  const limit = 56
  return rendered.length <= limit ? rendered : `${rendered.slice(0, limit - 1)}…`
}

export function formatToolExecutionLabel(execution: AgentToolExecution): string {
  const argumentsLabel = Object.keys(execution.arguments)
    .sort()
    .map((key) => `${key}=${compactArgumentValue(execution.arguments[key])}`)
    .join(', ')

  return argumentsLabel ? `${execution.name} · ${argumentsLabel}` : execution.name
}

export function buildReadOnlyAgentMessages(
  history: StudioCopilotMessage[],
  prompt: string,
  context: StudioAgentContext,
): AgentChatMessage[] {
  const visibleFlow = context.peakVisibleFlowCms == null
    ? 'No routed scenario flow is currently visible.'
    : `Peak visible routed flow is ${context.peakVisibleFlowCms} m3/s.`
  const contextMessage = [
    'Studio context (read-only UI state):',
    `${context.objectCount} objects; ${context.riverCount} river reaches; ${context.assetCount} engineering assets.`,
    `Scenario time is ${context.timestampMinutes} minutes.`,
    `Manual inflow control is ${context.inflowCms} m3/s.`,
    `Manual release control is ${context.releaseCms} m3/s.`,
    visibleFlow,
    'Scenario controls are UI-only and are not available as Agent tools.',
    `User question: ${prompt}`,
  ].join('\n')

  const normalizedHistory = history
    .slice(-5)
    .map((message): AgentChatMessage => ({ role: message.role, content: message.content }))

  return [
    ...normalizedHistory,
    { role: 'user', content: contextMessage },
  ]
}
