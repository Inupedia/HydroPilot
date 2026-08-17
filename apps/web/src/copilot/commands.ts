export type CopilotCommand =
  | { type: 'highlight-downstream' }
  | { type: 'run-release'; releaseCms: number }
  | { type: 'chat' }

const RELEASE_INTENT_PATTERN = /release|flow|discharge|下泄|泄量|流量|调度/i
const NUMBER_PATTERN = /([0-9]{2,6}(?:\.[0-9]+)?)/

export function parseCopilotCommand(input: string): CopilotCommand {
  const text = input.trim()
  const lower = text.toLowerCase()

  if (
    lower.includes('downstream') ||
    text.includes('下游') ||
    text.includes('水网链路') ||
    text.includes('河网链路')
  ) {
    return { type: 'highlight-downstream' }
  }

  if (RELEASE_INTENT_PATTERN.test(text)) {
    const numberMatch = text.match(NUMBER_PATTERN)
    if (numberMatch) {
      const releaseCms = Number(numberMatch[1])
      if (Number.isFinite(releaseCms) && releaseCms >= 0) {
        return { type: 'run-release', releaseCms }
      }
    }
  }

  return { type: 'chat' }
}
