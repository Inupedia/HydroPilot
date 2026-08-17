import { defineStore } from 'pinia'
import type { HydroState } from '../types'

export const useScenarioStore = defineStore('scenario', {
  state: () => ({ timestamp: 0, timestamps: [0] as number[] }),
  actions: {
    setStates(states: HydroState[]) { this.timestamps = [...new Set(states.map((item) => item.timestamp_minutes))].sort((a, b) => a - b); this.timestamp = this.timestamps[0] ?? 0 },
    setTimestamp(value: number) { const min = this.timestamps[0] ?? 0; const max = this.timestamps[this.timestamps.length - 1] ?? 0; this.timestamp = Math.min(Math.max(value, min), max) },
  },
})
