import { defineStore } from 'pinia'
import { hydroApi } from '../api/client'
import type { HydroObject } from '../types'

export const useNetworkStore = defineStore('network', {
  state: () => ({ objects: [] as HydroObject[], highlightedIds: new Set<string>(), selectedId: '' }),
  actions: {
    async load() { this.objects = await hydroApi.objects() },
    async highlightDownstream(id: string) { this.selectedId = id; const path = await hydroApi.downstream(id); this.highlightedIds = new Set([id, ...path.map((item) => item.object_id)]) },
  },
})
