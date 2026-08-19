import type { AgentChatMessage, LlmProviderSummary } from '../api/client'

export interface StudioAgentContext {
  objectCount: number
  riverCount: number
  assetCount: number
  timestampMinutes: number
  inflowCms: number
  releaseCms: number
  peakVisibleFlowCms: number | null
}

export function agentCompatibleProviders(providers: LlmProviderSummary[]): LlmProviderSummary[] {
  return providers.filter((provider) => provider.adapter_family === 'openai-compatible')
}

export function buildReadOnlyAgentMessages(
  history: AgentChatMessage[],
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

  return [
    ...history.slice(-5),
    { role: 'user', content: contextMessage },
  ]
}
