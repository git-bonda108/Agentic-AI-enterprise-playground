// Renders the deck's animated diagrams (docs/images/deck/<name>.svg, from scripts/deck_diagrams.py) to PNG frames with
// Instrument Sans loaded, stepping the SMIL clock per frame; scripts/deck_gifs.py encodes them. Frame 0 starts at `start`
// so exports that show only the first frame (PDF, PowerPoint) catch the beam mid-journey.
//   npm run deck:gifs
import { chromium } from "playwright";
import { mkdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const FPS = 8;
const DIAGRAMS = [
  { name: "hub", width: 820, height: 820, seconds: 9, start: 1.2 },
  { name: "layers", width: 1600, height: 720, seconds: 10, start: 4.4 },
  { name: "run", width: 1600, height: 600, seconds: 12, start: 5.6 },
  { name: "agent", width: 1600, height: 560, seconds: 15, start: 10.6 },
  { name: "journeys", width: 1600, height: 600, seconds: 12.5, start: 3.6 },
];
const only = process.argv.slice(2);
const browser = await chromium.launch();
for (const d of DIAGRAMS.filter((x) => !only.length || only.includes(x.name))) {
  const dir = resolve("docs/images/deck/frames", d.name);
  mkdirSync(dir, { recursive: true });
  const svg = readFileSync(resolve("docs/images/deck", `${d.name}.svg`), "utf8");
  const page = await browser.newPage({ viewport: { width: d.width, height: d.height }, deviceScaleFactor: 1 });
  await page.setContent(`<!doctype html><html><head><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&display=swap"></head><body style="margin:0;background:#F7F7FB">${svg}</body></html>`, { waitUntil: "networkidle" });
  await page.evaluate(async () => { await Promise.all(["400", "600", "700"].map((w) => document.fonts.load(`${w} 20px "Sora"`))); await document.fonts.ready; });
  const frames = Math.round(d.seconds * FPS);
  for (let i = 0; i < frames; i++) {
    const t = (d.start + i / FPS) % d.seconds;
    await page.evaluate((s) => { const el = document.querySelector("svg"); el.pauseAnimations(); el.setCurrentTime(s); }, t);
    await page.locator("svg").screenshot({ path: resolve(dir, `${String(i).padStart(3, "0")}.png`) });
  }
  await page.close();
  console.log(`${d.name}: ${frames} frames`);
}
await browser.close();
