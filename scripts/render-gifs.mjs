// Captures frames of the animated SVG diagrams in docs/images with the Playwright Chromium already installed for the
// end-to-end tests, into docs/images/frames/<name>/NNN.png. scripts/frames_to_gif.py then encodes each folder as a GIF.
//   npm run diagrams:gif
import { chromium } from "playwright";
import { mkdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const DIAGRAMS = [
  { name: "architecture-flow", width: 1290, height: 720, seconds: 10 },
  { name: "workflow-flow", width: 1200, height: 420, seconds: 12 },
];
const FPS = 6;

const browser = await chromium.launch();
for (const d of DIAGRAMS) {
  const dir = resolve("docs/images/frames", d.name);
  mkdirSync(dir, { recursive: true });
  const svg = readFileSync(resolve("docs/images", `${d.name}.svg`), "utf8");
  const page = await browser.newPage({ viewport: { width: d.width, height: d.height }, deviceScaleFactor: 1 });
  await page.setContent(`<!doctype html><html><body style="margin:0;background:#0a0a14">${svg}</body></html>`);
  await page.evaluate(() => document.fonts.ready);
  const svgEl = page.locator("svg");
  const frames = d.seconds * FPS;
  for (let i = 0; i < frames; i++) {
    // Drive the SMIL clock explicitly so every frame lands on a deterministic timestamp.
    await page.evaluate((t) => { const s = document.querySelector("svg"); s.pauseAnimations(); s.setCurrentTime(t); }, i / FPS);
    await svgEl.screenshot({ path: resolve(dir, `${String(i).padStart(3, "0")}.png`) });
  }
  await page.close();
  console.log(`${d.name}: ${frames} frames`);
}
await browser.close();
