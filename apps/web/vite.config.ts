import { cpSync, createReadStream, existsSync, mkdirSync, statSync } from 'node:fs'
import { dirname, extname, normalize, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const projectRoot = dirname(fileURLToPath(import.meta.url))
const cesiumSource = resolve(projectRoot, 'node_modules/cesium/Build/Cesium')
const cesiumBaseUrl = '/cesium/'

const mimeTypes = new Map([
  ['.css', 'text/css; charset=utf-8'],
  ['.gif', 'image/gif'],
  ['.ico', 'image/x-icon'],
  ['.jpeg', 'image/jpeg'],
  ['.jpg', 'image/jpeg'],
  ['.js', 'text/javascript; charset=utf-8'],
  ['.json', 'application/json; charset=utf-8'],
  ['.mjs', 'text/javascript; charset=utf-8'],
  ['.png', 'image/png'],
  ['.svg', 'image/svg+xml'],
  ['.wasm', 'application/wasm'],
  ['.woff', 'font/woff'],
  ['.woff2', 'font/woff2'],
  ['.xml', 'application/xml; charset=utf-8'],
])

function cesiumRuntimeAssets() {
  return {
    name: 'cesium-runtime-assets',
    configureServer(server: { middlewares: { use: (handler: (req: { url?: string }, res: any, next: () => void) => void) => void } }) {
      server.middlewares.use((req, res, next) => {
        const requestUrl = new URL(req.url ?? '/', 'http://127.0.0.1')
        if (!requestUrl.pathname.startsWith(cesiumBaseUrl)) {
          next()
          return
        }

        const rawRelative = decodeURIComponent(requestUrl.pathname.slice(cesiumBaseUrl.length))
        const relative = normalize(rawRelative).replace(/^([/\\])+/, '')
        const filePath = resolve(cesiumSource, relative)
        const sourceRoot = cesiumSource.endsWith(sep) ? cesiumSource : `${cesiumSource}${sep}`

        if (!filePath.startsWith(sourceRoot) || !existsSync(filePath) || !statSync(filePath).isFile()) {
          next()
          return
        }

        res.statusCode = 200
        res.setHeader('Content-Type', mimeTypes.get(extname(filePath).toLowerCase()) ?? 'application/octet-stream')
        res.setHeader('Cache-Control', 'no-cache')
        res.setHeader('X-Content-Type-Options', 'nosniff')
        createReadStream(filePath).pipe(res)
      })
    },
    closeBundle() {
      const targetRoot = resolve(projectRoot, 'dist/cesium')
      mkdirSync(targetRoot, { recursive: true })
      for (const directory of ['Assets', 'ThirdParty', 'Workers', 'Widgets']) {
        cpSync(resolve(cesiumSource, directory), resolve(targetRoot, directory), { recursive: true })
      }
    },
  }
}

export default defineConfig({
  plugins: [vue(), cesiumRuntimeAssets()],
  test: { environment: 'jsdom' },
  define: { CESIUM_BASE_URL: JSON.stringify(cesiumBaseUrl) },
})
