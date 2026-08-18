import { invoke } from '@tauri-apps/api/core'

declare global { interface Window { __TAURI_INTERNALS__?: unknown } }

function sessionKey(name: string) { return `hydropilot.secret.${name}` }
function inTauri() { return Boolean(window.__TAURI_INTERNALS__) }

export const secrets = {
  async get(name: string): Promise<string | null> {
    if (inTauri()) {
      try { return await invoke<string | null>('secret_get', { name }) } catch { /* fall through */ }
    }
    return sessionStorage.getItem(sessionKey(name))
  },
  async set(name: string, value: string): Promise<'secure' | 'session'> {
    if (inTauri()) {
      try { await invoke('secret_set', { name, value }); return 'secure' } catch { /* fall through */ }
    }
    sessionStorage.setItem(sessionKey(name), value)
    return 'session'
  },
  async remove(name: string): Promise<void> {
    if (inTauri()) {
      try { await invoke('secret_remove', { name }); return } catch { /* fall through */ }
    }
    sessionStorage.removeItem(sessionKey(name))
  },
}
