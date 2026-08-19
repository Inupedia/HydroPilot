import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  hydroApi,
  type AgentChatRequest,
  type LlmProviderSummary,
} from '../src/api/client'
import {
  agentCompatibleProviders,
  buildReadOnlyAgentMessages,
  type StudioAgentContext,
} from '../src/copilot/agent'

const providers: LlmProviderSummary[] = [
  {
    id: 'openai',
    name: 'OpenAI',
    adapter_family: 'openai-compatible',
    default_base_url: 'https://api.openai.com/v1',
    api_key_env: 'OPENAI_API_KEY',
    auth_required: true,
    model_examples: ['gpt-test'],
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    adapter_family: 'anthropic',
    default_base_url: 'https://api.anthropic.com/v1',
    api_key_env: 'ANTHROPIC_API_KEY',
    auth_required: true,
    model_examples: ['claude-test'],
  },
  {
    id: 'custom-openai',
    name: 'Custom',
    adapter_family: 'openai-compatible',
    default_base_url: null,
    api_key_env: 'HYDROPILOT_LLM_API_KEY',
    auth_required: true,
    model_examples: [],
  },
]

const context: StudioAgentContext = {
  objectCount: 18,
  riverCount: 13,
  assetCount: 5,
  timestampMinutes: 30,
  inflowCms: 1000,
  releaseCms: 2200,
  peakVisibleFlowCms: 1875,
}

afterEach(() => {
  vi.restoreAllMocks()
  delete window.__TAURI_INTERNALS__
})

describe('read-only Studio Agent', () => {
  it('offers only OpenAI-compatible providers', () => {
    expect(agentCompatibleProviders(providers).map((item) => item.id)).toEqual([
      'openai',
      'custom-openai',
    ])
  })

  it('builds user/assistant-only history with descriptive non-executable Studio context', () => {
    const messages = buildReadOnlyAgentMessages(
      [
        { role: 'assistant', content: 'How can I help?' },
        { role: 'user', content: 'What is this project?' },
        { role: 'assistant', content: 'A water-network demonstrator.' },
      ],
      'What constraints are configured?',
      context,
    )

    expect(messages.every((message) => message.role === 'user' || message.role === 'assistant')).toBe(true)
    expect(messages.at(-1)?.role).toBe('user')
    expect(messages.at(-1)?.content).toContain('18 objects')
    expect(messages.at(-1)?.content).toContain('13 river reaches')
    expect(messages.at(-1)?.content).toContain('30 minutes')
    expect(messages.at(-1)?.content).toContain('1000 m3/s')
    expect(messages.at(-1)?.content).toContain('2200 m3/s')
    expect(messages.at(-1)?.content).toContain('1875 m3/s')
    expect(messages.at(-1)?.content).toContain('Scenario controls are UI-only and are not available as Agent tools.')
    expect(messages.at(-1)?.content).toContain('User question: What constraints are configured?')
  })

  it('posts Copilot questions to the Agent endpoint without caller-supplied tools', async () => {
    const fetchMock = vi.spyOn(window, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          provider: 'openai',
          model: 'gpt-test',
          text: 'No constraints are configured.',
          tool_executions: [],
          provider_rounds: 1,
        }),
        { status: 200, headers: { 'content-type': 'application/json' } },
      ),
    )

    const request: AgentChatRequest = {
      provider: 'openai',
      model: 'gpt-test',
      api_key: 'secret',
      messages: [{ role: 'user', content: 'What constraints are configured?' }],
      temperature: 0.2,
      max_tokens: 1200,
      max_tool_rounds: 4,
    }

    const response = await hydroApi.agentChat(request)

    expect(response.text).toBe('No constraints are configured.')
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(String(url)).toMatch(/\/api\/agent\/chat$/)
    const body = JSON.parse(String(init?.body)) as Record<string, unknown>
    expect(body.tools).toBeUndefined()
    expect(body.messages).toEqual(request.messages)
  })
})
