import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: { environment: 'jsdom' },
  define: { CESIUM_BASE_URL: JSON.stringify('/cesium') },
})
