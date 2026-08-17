import { describe, expect, it } from 'vitest'
import { parseCopilotCommand } from '../src/copilot/commands'

describe('parseCopilotCommand', () => {
  it('recognizes downstream map commands', () => {
    expect(parseCopilotCommand('高亮这条水网的下游链路')).toEqual({ type: 'highlight-downstream' })
    expect(parseCopilotCommand('show downstream chain')).toEqual({ type: 'highlight-downstream' })
  })

  it('extracts release flow values', () => {
    expect(parseCopilotCommand('按 2200 m³/s 运行下泄调度场景')).toEqual({ type: 'run-release', releaseCms: 2200 })
    expect(parseCopilotCommand('release 2600 cms')).toEqual({ type: 'run-release', releaseCms: 2600 })
  })

  it('falls back to LLM chat for explanation questions', () => {
    expect(parseCopilotCommand('解释当前水网里有哪些工程对象')).toEqual({ type: 'chat' })
  })
})
