export {}

declare global {
  interface Window {
    hydropilotDesktop?: {
      secrets: {
        get(name: string): Promise<string | null>
        set(name: string, value: string): Promise<void>
        remove(name: string): Promise<void>
      }
    }
  }
}
