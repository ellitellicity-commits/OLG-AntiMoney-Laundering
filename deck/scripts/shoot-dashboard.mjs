// Capture real dashboard screenshots for slide 3 with Microsoft Edge.
// Needs the API running (it serves the dashboard at /app/):
//   node scripts/shoot-dashboard.mjs http://127.0.0.1:8765 [outDir]
// Writes dashboard-queue.png (ranked queue) and dashboard-alert.png (top alert opened).
// The dashboard's top bar (which carries the app's own working name) is cropped off;
// nothing inside the images is edited.
import { chromium } from 'playwright'

const api = (process.argv[2] || 'http://127.0.0.1:8765').replace(/\/$/, '')
const outDir = process.argv[3] || 'public/img'
const width = 1440, height = 860

const browser = await chromium.launch({ channel: 'msedge' })
const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1.5 })
await page.goto(`${api}/app/`, { waitUntil: 'networkidle' })
await page.waitForTimeout(600)

// Collapse the assistant panel so the queue and the alert detail get the room.
await page.click('#chat-collapse')
await page.waitForTimeout(300)

const top = await page.evaluate(() => {
  const bar = document.querySelector('header, .topbar, [role="banner"]')
  return bar ? Math.ceil(bar.getBoundingClientRect().bottom) : 0
})
const clip = { x: 0, y: top, width, height: height - top }

await page.screenshot({ path: `${outDir}/dashboard-queue.png`, clip })

// Open the top-ranked alert.
const first = await page.locator('tbody tr').first().innerText()
await page.locator('tbody tr').first().click()
await page.waitForLoadState('networkidle')
await page.waitForTimeout(800)
await page.screenshot({ path: `${outDir}/dashboard-alert.png`, clip })

console.log(`saved queue + alert screenshots to ${outDir} (cropped ${top}px top bar); top row: ${first.split('\n').slice(0, 4).join(' | ')}`)
await browser.close()
