import { describe, expect, it } from 'vitest'
import { parseCopilotCommand } from '../src/copilot/commands'

describe('parseCopilotCommand', () => {
  it('recognizes downstream highlighting', () => { expect(parseCopilotCommand('高亮这条水网的下游链路')).toEqual({ type: 'highlight-downstream' }) })
  it('recognizes Chinese release commands with the number before the verb', () => { expect(parseCopilotCommand('按 2200 m³/s 运行下泄调度场景')).toEqual({ type: 'run-release', releaseCms: 2200 }) })
  it('leaves general questions for the LLM', () => { expect(parseCopilotCommand('解释当前水网里有哪些工程对象')).toEqual({ type: 'chat' }) })
})
