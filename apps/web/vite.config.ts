import { cpSync, mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const projectRoot = dirname(fileURLToPath(import.meta.url))

function copyCesiumAssets() {
  return {
    name: 'copy-cesium-runtime-assets',
    closeBundle() {
      const sourceRoot = resolve(projectRoot, 'node_modules/cesium/Build/Cesium')
      const targetRoot = resolve(projectRoot, 'dist/cesium')
      mkdirSync(targetRoot, { recursive: true })
      for (const directory of ['Assets', 'ThirdParty', 'Workers', 'Widgets']) {
        cpSync(resolve(sourceRoot, directory), resolve(targetRoot, directory), { recursive: true })
      }
    },
  }
}

export default defineConfig({
  plugins: [vue(), copyCesiumAssets()],
  test: { environment: 'jsdom' },
  define: { CESIUM_BASE_URL: JSON.stringify('/cesium/') },
})
