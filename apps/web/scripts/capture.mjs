import { mkdir } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { chromium } from 'playwright'

const url = process.env.HYDROPILOT_WEB_URL ?? 'http://127.0.0.1:4173'
const output = resolve(process.env.SCREENSHOT_PATH ?? 'artifacts/hydropilot-cesium.png')
await mkdir(dirname(output), { recursive: true })

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 })
const pageErrors = []
page.on('pageerror', (error) => pageErrors.push(error.message))

try {
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60_000 })
  await page.waitForSelector('.cesium-viewer canvas', { state: 'visible', timeout: 30_000 })
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
  }, { timeout: 30_000 })

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

  console.log(JSON.stringify({ ok: true, screenshot: output, ...diagnostics }, null, 2))
} finally {
  await browser.close()
}
