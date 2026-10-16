// Screenshot every slide at 1920x1080 and 1280x720 with Microsoft Edge, and report
// overflow, cut-off or low-contrast text and any request that leaves the local server.
//
//   node scripts/check-slides.mjs http://127.0.0.1:3030 [slideCount]
//
// Screenshots go to screenshots/<width>x<height>/slide-N.png. Exit code 1 if anything failed.
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'

const base = (process.argv[2] || 'http://127.0.0.1:3030').replace(/\/$/, '')
const count = Number(process.argv[3] || 5)
const sizes = [[1920, 1080], [1280, 720]]
const origin = new URL(base).origin

const browser = await chromium.launch({ channel: 'msedge' })
const external = new Set()
const problems = []

for (const [width, height] of sizes) {
  const dir = `screenshots/${width}x${height}`
  mkdirSync(dir, { recursive: true })
  const page = await browser.newPage({ viewport: { width, height } })
  page.on('request', (r) => {
    const u = r.url()
    if (!u.startsWith(origin) && !u.startsWith('data:') && !u.startsWith('blob:')) external.add(u)
  })
  for (let n = 1; n <= count; n++) {
    // hash routing works for both the dev server and the static build
    await page.goto(`${base}/#/${n}`, { waitUntil: 'networkidle' })
    await page.evaluate(() => document.fonts.ready)
    await page.waitForTimeout(400)
    await page.screenshot({ path: `${dir}/slide-${n}.png` })

    const found = await page.evaluate(() => {
      const out = []
      const root = [...document.querySelectorAll('.slidev-layout')].find((el) => el.offsetParent !== null)
      if (!root) return ['no visible .slidev-layout']
      const box = root.getBoundingClientRect()
      if (root.scrollHeight > root.clientHeight + 1) out.push(`layout scrolls: ${root.scrollHeight} > ${root.clientHeight}`)

      const parse = (c) => (c.match(/[\d.]+/g) || []).map(Number)
      const lum = ([r, g, b]) => {
        const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4 }
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
      }
      const bgOf = (el) => {
        for (let e = el; e; e = e.parentElement) {
          const c = parse(getComputedStyle(e).backgroundColor)
          if (c.length >= 3 && (c.length < 4 || c[3] > 0.5)) return c.slice(0, 3)
        }
        return [255, 255, 255]
      }

      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
      while (walker.nextNode()) {
        const t = walker.currentNode
        if (!t.textContent.trim()) continue
        const el = t.parentElement
        const cs = getComputedStyle(el)
        if (cs.visibility === 'hidden' || cs.display === 'none') continue
        const range = document.createRange()
        range.selectNodeContents(t)
        const r = range.getBoundingClientRect()
        const label = t.textContent.trim().slice(0, 40)
        if (r.left < box.left - 1 || r.right > box.right + 1 || r.top < box.top - 1 || r.bottom > box.bottom + 1)
          out.push(`outside slide: "${label}"`)
        if (el.scrollWidth > el.clientWidth + 1 && cs.overflow !== 'visible') out.push(`clipped: "${label}"`)
        const fg = lum(parse(cs.color)), bg = lum(bgOf(el))
        const ratio = (Math.max(fg, bg) + 0.05) / (Math.min(fg, bg) + 0.05)
        if (ratio < 4.5) out.push(`contrast ${ratio.toFixed(2)}: "${label}"`)
        // projector floor: 13px on the 980px canvas (about 17px on a 1280x720 screen)
        if (parseFloat(cs.fontSize) < 13) out.push(`tiny text ${cs.fontSize}: "${label}"`)
      }
      return out
    })
    for (const f of found) problems.push(`${width}x${height} slide ${n}: ${f}`)
  }
  await page.close()
}
await browser.close()

console.log(`Screenshots: screenshots/{1920x1080,1280x720}/slide-1..${count}.png`)
console.log(external.size ? `External requests (${external.size}):\n  ${[...external].join('\n  ')}` : 'External requests: none')
console.log(problems.length ? `Problems (${problems.length}):\n  ${problems.join('\n  ')}` : 'Problems: none')
process.exit(external.size || problems.length ? 1 : 0)
