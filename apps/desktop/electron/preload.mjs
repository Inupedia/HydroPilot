import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('hydropilotDesktop', {
  secrets: {
    get: (name) => ipcRenderer.invoke('hydropilot:secret:get', name),
    set: (name, value) => ipcRenderer.invoke('hydropilot:secret:set', name, value),
    remove: (name) => ipcRenderer.invoke('hydropilot:secret:remove', name),
  },
})
