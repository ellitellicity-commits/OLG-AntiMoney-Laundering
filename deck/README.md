# Pitch deck

A 5-slide, ~2-minute pitch deck built with [Slidev](https://sli.dev). Everything runs offline: fonts come
from `node_modules/@fontsource`, images from `public/img/`, and no CDN is used.

| File | What it is |
|---|---|
| `slides.md` | The 5 slides and their speaker notes (with timings) |
| `components/ProjectName.vue` | **The project name, in one place.** Edit it to rename the deck |
| `components/Pipeline.vue`, `components/Results.vue` | Static diagram and results panels |
| `styles/` | Theme tokens from `../DESIGN.md` and the bundled fonts |
| `public/img/` | Real dashboard screenshots (synthetic data) |
| `export/pitch-deck.pdf`, `export/pitch-deck.pptx` | Exported deck (committed) |
| `screenshots/` | Every slide at 1920x1080 and 1280x720, from the last check |
| `SOURCES.md` | Where every number comes from |
| `scripts/` | Dashboard screenshots and slide checks (Playwright with Microsoft Edge) |

All data shown is synthetic. The slides are static: no animations, clicks or transitions, so the PDF and
PPTX match what you see in the browser.

## Setup (once)

Tested with Node.js 26.8.1 and Microsoft Edge (used instead of a downloaded browser). In Windows PowerShell:

```powershell
cd deck
$env:PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD = "1"   # use Edge; don't download Chromium
npm ci
```

## Run and present

```powershell
npm run dev            # opens http://localhost:3030 ; press F for fullscreen, arrow keys to move
```

Presenter view with speaker notes and a timer: http://localhost:3030/presenter/

## Export

```powershell
npm run export:pdf     # export/pitch-deck.pdf
npm run export:pptx    # export/pitch-deck.pptx (slides as images, speaker notes included)
```

Both use Edge at `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`. If Edge is elsewhere, change
the `--executable-path` in `package.json`. A console line "Failed to patch FloatingVue" during export is a
harmless Slidev warning.

## Static offline build

```powershell
npm run build          # writes dist/ (git-ignored)
```

Serve `dist/` with any static server, for example from the repo root with the project's Python venv:
`python -m http.server 4173 --directory deck\dist`, then open http://127.0.0.1:4173/. The deck uses hash routing
(`/#/3`), so any static server works.

## Google Slides

Upload `export/pitch-deck.pptx` to Google Drive, then right-click it and choose **Open with > Google Slides**
(or in Google Slides: **File > Import slides**). **Each slide arrives as a single image**, so the text cannot be
edited in Google Slides. Change `slides.md` and export again instead. Speaker notes are in the PPTX as text.

## Checks

```powershell
npm run build
python -m http.server 4173 --directory dist      # in a second terminal (any static server)
npm run check
```

`npm run check` screenshots every slide at 1920x1080 and 1280x720 into `screenshots/` and fails on text outside
the slide, clipped text, contrast below 4.5:1, text under 13px on the 980px canvas, or any request leaving the
local server.

To refresh the dashboard screenshots, run the API (see the main README), then:
`node scripts/shoot-dashboard.mjs http://127.0.0.1:8765`.
