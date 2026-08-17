import { app, BrowserWindow, dialog } from 'electron'
import { spawn } from 'node:child_process'
import { createReadStream, existsSync } from 'node:fs'
import { createServer, get as httpGet, request as httpRequest } from 'node:http'
import { dirname, extname, join, normalize, resolve, sep, delimiter } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const smokeMode = process.env.HYDROPILOT_DESKTOP_SMOKE === '1'
let mainWindow
let apiProcess
let rendererServer
let apiPort
let rendererPort

const mimeTypes = new Map([
  ['.html', 'text/html; charset=utf-8'],
  ['.js', 'text/javascript; charset=utf-8'],
  ['.mjs', 'text/javascript; charset=utf-8'],
  ['.css', 'text/css; charset=utf-8'],
  ['.json', 'application/json; charset=utf-8'],
  ['.wasm', 'application/wasm'],
  ['.png', 'image/png'],
  ['.jpg', 'image/jpeg'],
  ['.jpeg', 'image/jpeg'],
  ['.svg', 'image/svg+xml'],
  ['.gif', 'image/gif'],
  ['.ico', 'image/x-icon'],
  ['.woff', 'font/woff'],
  ['.woff2', 'font/woff2'],
])

const sleep = (ms) => new Promise((resolveSleep) => setTimeout(resolveSleep, ms))

function repoRoot() {
  return resolve(__dirname, '../../..')
}

function resourcePath(...parts) {
  return app.isPackaged ? join(process.resourcesPath, ...parts) : join(repoRoot(), ...parts)
}

function getFreePort() {
  return new Promise((resolvePort, reject) => {
    const server = createServer()
    server.unref()
    server.on('error', reject)
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      const port = typeof address === 'object' && address ? address.port : undefined
      server.close(() => port ? resolvePort(port) : reject(new Error('Unable to allocate a local port')))
    })
  })
}

function startApi(port) {
  const fixture = resourcePath('data', 'demo', 'sacramento_v0_1.json')
  const env = {
    ...process.env,
    HYDROPILOT_API_HOST: '127.0.0.1',
    HYDROPILOT_API_PORT: String(port),
    HYDROPILOT_DEMO_FIXTURE_PATH: fixture,
  }

  let command
  let args
  if (app.isPackaged) {
    command = resourcePath('api', process.platform === 'win32' ? 'hydropilot-api.exe' : 'hydropilot-api')
    args = []
    if (!existsSync(command)) throw new Error(`HydroPilot API sidecar is missing: ${command}`)
  } else {
    command = process.env.PYTHON ?? (process.platform === 'win32' ? 'python' : 'python3')
    args = [resourcePath('apps', 'api', 'desktop_entry.py')]
    env.PYTHONPATH = [
      resourcePath('apps', 'api', 'src'),
      resourcePath('packages', 'hydropilot-core', 'src'),
      process.env.PYTHONPATH,
    ].filter(Boolean).join(delimiter)
  }

  apiProcess = spawn(command, args, {
    cwd: app.isPackaged ? process.resourcesPath : repoRoot(),
    env,
    stdio: smokeMode || !app.isPackaged ? 'inherit' : 'ignore',
    windowsHide: true,
  })

  apiProcess.on('exit', (code, signal) => {
    if (!app.isQuitting && code !== 0) {
      console.error(`HydroPilot API exited unexpectedly (code=${code}, signal=${signal})`)
    }
  })
}

function waitForApi(port, timeoutMs = 20_000) {
  const started = Date.now()
  return new Promise((resolveHealth, reject) => {
    const attempt = () => {
      const req = httpGet(`http://127.0.0.1:${port}/health`, (res) => {
        res.resume()
        if (res.statusCode === 200) return resolveHealth()
        retry()
      })
      req.on('error', retry)
      req.setTimeout(1_000, () => req.destroy())
    }
    const retry = () => {
      if (Date.now() - started >= timeoutMs) return reject(new Error('Local HydroPilot API did not become ready'))
      setTimeout(attempt, 250)
    }
    attempt()
  })
}

function proxyToApi(req, res) {
  const upstream = httpRequest({
    hostname: '127.0.0.1',
    port: apiPort,
    path: req.url,
    method: req.method,
    headers: { ...req.headers, host: `127.0.0.1:${apiPort}` },
  }, (upstreamRes) => {
    res.writeHead(upstreamRes.statusCode ?? 502, upstreamRes.headers)
    upstreamRes.pipe(res)
  })
  upstream.on('error', (error) => {
    res.writeHead(502, { 'content-type': 'application/json; charset=utf-8' })
    res.end(JSON.stringify({ detail: 'HydroPilot API unavailable', error: error.message }))
  })
  req.pipe(upstream)
}

function safeStaticPath(root, pathname) {
  const decoded = decodeURIComponent(pathname)
  const relative = normalize(decoded).replace(/^([/\\])+/, '')
  const candidate = join(root, relative)
  const normalizedRoot = root.endsWith(sep) ? root : `${root}${sep}`
  return candidate === root || candidate.startsWith(normalizedRoot) ? candidate : null
}

async function startRendererServer() {
  if (rendererServer && rendererPort) return
  const webRoot = app.isPackaged ? resourcePath('web') : resourcePath('apps', 'web', 'dist')
  if (!existsSync(join(webRoot, 'index.html'))) throw new Error(`Desktop renderer build is missing: ${webRoot}`)

  rendererServer = createServer((req, res) => {
    const url = new URL(req.url ?? '/', 'http://127.0.0.1')
    if (url.pathname === '/health' || url.pathname.startsWith('/api/')) {
      proxyToApi(req, res)
      return
    }

    let filePath = safeStaticPath(webRoot, url.pathname === '/' ? '/index.html' : url.pathname)
    if (!filePath || !existsSync(filePath)) filePath = join(webRoot, 'index.html')

    res.writeHead(200, {
      'content-type': mimeTypes.get(extname(filePath).toLowerCase()) ?? 'application/octet-stream',
      'cache-control': url.pathname.startsWith('/cesium/') || url.pathname.startsWith('/assets/')
        ? 'public, max-age=31536000, immutable'
        : 'no-cache',
      'x-content-type-options': 'nosniff',
    })
    createReadStream(filePath).pipe(res)
  })

  rendererPort = await new Promise((resolvePort, reject) => {
    rendererServer.on('error', reject)
    rendererServer.listen(0, '127.0.0.1', () => {
      const address = rendererServer.address()
      const port = typeof address === 'object' && address ? address.port : undefined
      port ? resolvePort(port) : reject(new Error('Unable to start desktop renderer server'))
    })
  })
}

async function verifyDesktopRuntime(timeoutMs = 30_000) {
  const started = Date.now()
  while (Date.now() - started < timeoutMs) {
    const state = await mainWindow.webContents.executeJavaScript(`(() => ({
      viewer: Boolean(document.querySelector('.cesium-viewer canvas')),
      objects: document.body.textContent?.includes('24 OBJECTS') ?? false,
      hostHeight: document.querySelector('[data-testid="cesium-host"]')?.clientHeight ?? 0
    }))()`)
    if (state.viewer && state.objects && state.hostHeight > 500) {
      console.log(`HYDROPILOT_DESKTOP_SMOKE_OK ${JSON.stringify(state)}`)
      return
    }
    await sleep(500)
  }
  throw new Error('Packaged Electron runtime did not render the Cesium scene and 24 demo objects')
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1520,
    height: 980,
    minWidth: 1180,
    minHeight: 720,
    show: false,
    backgroundColor: '#06111f',
    title: 'HydroPilot',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      devTools: !app.isPackaged,
    },
  })

  if (!smokeMode) mainWindow.once('ready-to-show', () => mainWindow.show())
  mainWindow.on('closed', () => { mainWindow = undefined })

  const devRenderer = process.env.HYDROPILOT_RENDERER_URL
  if (devRenderer) {
    await mainWindow.loadURL(devRenderer)
  } else {
    await startRendererServer()
    await mainWindow.loadURL(`http://127.0.0.1:${rendererPort}`)
  }

  if (smokeMode) {
    await verifyDesktopRuntime()
    app.quit()
  }
}

async function boot() {
  apiPort = await getFreePort()
  startApi(apiPort)
  await waitForApi(apiPort)
  await createWindow()
}

function shutdown() {
  if (rendererServer) rendererServer.close()
  rendererServer = undefined
  rendererPort = undefined
  if (apiProcess && !apiProcess.killed) apiProcess.kill()
  apiProcess = undefined
}

app.whenReady().then(async () => {
  try {
    await boot()
  } catch (error) {
    console.error(error)
    if (smokeMode) {
      shutdown()
      app.exit(2)
      return
    }
    dialog.showErrorBox('HydroPilot failed to start', error instanceof Error ? error.message : String(error))
    app.quit()
  }
})

app.on('activate', async () => {
  if (BrowserWindow.getAllWindows().length === 0) await createWindow()
})

app.on('before-quit', () => {
  app.isQuitting = true
  shutdown()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
