<script setup lang="ts">
import { computed } from 'vue'
import { useScenarioStore } from '../stores/scenario'
const scenario = useScenarioStore()
const max = computed(() => scenario.timestamps[scenario.timestamps.length - 1] ?? 0)
</script>
<template>
  <div class="timeline"><span>{{ scenario.timestamp }} min</span><input type="range" :min="0" :max="max" :step="30" :value="scenario.timestamp" @input="scenario.setTimestamp(Number(($event.target as HTMLInputElement).value))" /><span>{{ max }} min</span></div>
</template>
