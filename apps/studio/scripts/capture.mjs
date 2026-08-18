import { mkdir } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { chromium } from 'playwright'

const url = process.env.HYDROPILOT_WEB_URL ?? 'http://127.0.0.1:4173'
const output = resolve(process.env.SCREENSHOT_PATH ?? 'artifacts/hydropilot-cesium.png')
const debugOutput = resolve(process.env.DEBUG_SCREENSHOT_PATH ?? 'artifacts/hydropilot-cesium-debug.png')
await mkdir(dirname(output), { recursive: true })

const browser = await chromium.launch({
  headless: true,
  args: [
    '--use-gl=swiftshader',
    '--enable-webgl',
    '--ignore-gpu-blocklist',
    '--enable-unsafe-swiftshader',
  ],
})
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 })
const pageErrors = []
const consoleErrors = []
page.on('pageerror', (error) => pageErrors.push(error.message))
page.on('console', (message) => {
  if (message.type() === 'error' || message.type() === 'warning') {
    consoleErrors.push(`[${message.type()}] ${message.text()}`)
  }
})

try {
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60_000 })

  const webgl = await page.evaluate(() => {
    const canvas = document.createElement('canvas')
    return Boolean(canvas.getContext('webgl2') || canvas.getContext('webgl'))
  })
  console.log(`WebGL available: ${webgl}`)
  if (!webgl) throw new Error('WebGL is unavailable in the acceptance browser')

  try {
    await page.waitForSelector('.cesium-viewer canvas', { state: 'visible', timeout: 20_000 })
  } catch (error) {
    await page.screenshot({ path: debugOutput, fullPage: true })
    console.error(`Cesium viewer did not mount. Debug screenshot: ${debugOutput}`)
    console.error(`Page errors: ${pageErrors.join(' | ') || '(none)'}`)
    console.error(`Console messages: ${consoleErrors.join(' | ') || '(none)'}`)
    throw error
  }

  await page.waitForFunction(() => {
    const canvas = document.querySelector('.cesium-viewer canvas')
    const host = document.querySelector('[data-testid="cesium-host"]')
    return canvas instanceof HTMLCanvasElement && host instanceof HTMLElement && canvas.width > 500 && host.clientHeight > 500
  })
  await page.waitForFunction(() => document.body.textContent?.includes('24 OBJECTS'))

  await page.getByTestId('highlight-downstream').click()
  await page.getByTestId('run-scenario').click()
  await page.waitForFunction(() => {
    const status = document.querySelector('[data-testid="scenario-status"]')?.textContent ?? ''
    return status.includes('B m³')
  }, undefined, { timeout: 30_000 })

  await page.waitForTimeout(1_500)
  await page.screenshot({ path: output, fullPage: true })

  const diagnostics = await page.evaluate(() => ({
    cesiumViewers: document.querySelectorAll('.cesium-viewer').length,
    canvases: document.querySelectorAll('.cesium-viewer canvas').length,
    entityText: document.body.textContent?.includes('24 OBJECTS') ?? false,
    scenarioText: document.querySelector('[data-testid="scenario-status"]')?.textContent?.trim() ?? '',
  }))

  if (diagnostics.cesiumViewers !== 1 || diagnostics.canvases < 1 || !diagnostics.entityText) {
    throw new Error(`Cesium visual acceptance failed: ${JSON.stringify(diagnostics)}`)
  }
  if (pageErrors.length) {
    throw new Error(`Browser page errors: ${pageErrors.join(' | ')}`)
  }

  console.log(JSON.stringify({ ok: true, screenshot: output, webgl, ...diagnostics }, null, 2))
} finally {
  await browser.close()
}
