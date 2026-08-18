import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { viteStaticCopy } from 'vite-plugin-static-copy'

const projectRoot = dirname(fileURLToPath(import.meta.url))
const cesiumSource = resolve(projectRoot, 'node_modules/cesium/Build/Cesium')
const cesiumBaseUrl = 'cesium'

export default defineConfig({
  plugins: [
    vue(),
    viteStaticCopy({
      targets: [
        { src: resolve(cesiumSource, 'ThirdParty'), dest: cesiumBaseUrl },
        { src: resolve(cesiumSource, 'Workers'), dest: cesiumBaseUrl },
        { src: resolve(cesiumSource, 'Assets'), dest: cesiumBaseUrl },
        { src: resolve(cesiumSource, 'Widgets'), dest: cesiumBaseUrl },
      ],
    }),
  ],
  test: { environment: 'jsdom' },
  define: { CESIUM_BASE_URL: JSON.stringify(`/${cesiumBaseUrl}/`) },
})
