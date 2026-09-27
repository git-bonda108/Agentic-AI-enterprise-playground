// Prints the design overview to docs/DESIGN.pdf in the playground's palette.
// Step 1 captures a still frame of each animated diagram (docs/images/<name>-still.png) at a moment where the beam is
// mid-journey; step 2 prints the HTML that scripts/design_html.py produced.
//   npm run design:pdf
import { chromium } from "playwright";
import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";

const HTML = process.argv[2];
if (!HTML || !existsSync(HTML)) { console.error("usage: node scripts/render-design-pdf.mjs <design.html>"); process.exit(1); }

const STILLS = [
  { name: "architecture-flow", width: 1290, height: 720, at: 4.6 },
  { name: "workflow-flow", width: 1200, height: 420, at: 5.2 },
];

const browser = await chromium.launch();
for (const s of STILLS) {
  const svg = readFileSync(resolve("docs/images", `${s.name}.svg`), "utf8");
  const page = await browser.newPage({ viewport: { width: s.width, height: s.height }, deviceScaleFactor: 2 });
  await page.setContent(`<!doctype html><html><body style="margin:0;background:#0a0a14">${svg}</body></html>`);
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate((t) => { const el = document.querySelector("svg"); el.pauseAnimations(); el.setCurrentTime(t); }, s.at);
  await page.locator("svg").screenshot({ path: resolve("docs/images", `${s.name}-still.png`) });
  await page.close();
}

const page = await browser.newPage();
await page.goto(`file://${resolve(HTML)}`, { waitUntil: "networkidle" });
await page.evaluate(() => document.fonts.ready);
await page.emulateMedia({ media: "print" });
// Flow the article into fixed A4 page boxes: block by block, table row by row (each page repeats the table header),
// list item by list item (numbering continues). Headings never end a page alone.
const pageCount = await page.evaluate(() => {
  const article = document.querySelector("article.doc");
  const units = [];
  for (const el of [...article.children]) {
    if (el.tagName === "H1") continue;  // the cover carries the title
    if (el.tagName === "TABLE") {
      const thead = el.querySelector("thead");
      [...el.querySelectorAll("tbody tr")].forEach((tr) => units.push({ kind: "row", table: el, thead, node: tr }));
    } else if (el.tagName === "OL" || el.tagName === "UL") {
      [...el.children].forEach((li, i) => units.push({ kind: "li", list: el, node: li, index: i }));
    } else {
      units.push({ kind: "block", node: el });
    }
  }
  const pages = document.createElement("div");
  article.after(pages);  // measurements below need the pages in the document
  let n = 1, content = null, wrapper = null;  // wrapper: the table or list currently being filled on this page
  const mm = (v) => v * 96 / 25.4;
  const newPage = () => {
    n += 1;
    const section = document.createElement("section"); section.className = "page";
    content = document.createElement("div"); content.className = "page-content"; section.appendChild(content);
    const footer = document.createElement("div"); footer.className = "page-footer";
    footer.innerHTML = `<span>Enterprise AI Playground · Design overview</span><span>${n}</span>`;
    section.appendChild(footer); pages.appendChild(section); wrapper = null;
  };
  const place = (u) => {
    if (u.kind === "block") { content.appendChild(u.node); wrapper = null; return; }
    if (u.kind === "row") {
      if (!wrapper || wrapper.source !== u.table) {
        const t = u.table.cloneNode(false); if (u.thead) t.appendChild(u.thead.cloneNode(true)); t.appendChild(document.createElement("tbody"));
        content.appendChild(t); wrapper = { source: u.table, el: t, body: t.querySelector("tbody") };
      }
      wrapper.body.appendChild(u.node); return;
    }
    if (!wrapper || wrapper.source !== u.list) {
      const l = u.list.cloneNode(false); if (l.tagName === "OL") l.setAttribute("start", String(u.index + 1));
      content.appendChild(l); wrapper = { source: u.list, el: l, body: l };
    }
    wrapper.body.appendChild(u.node);
  };
  const overflows = () => content.scrollHeight > content.clientHeight + 1;
  const remaining = () => {  // space below the last placed element (scrollHeight never exceeds the clipped box)
    const last = content.lastElementChild; const box = content.getBoundingClientRect();
    return box.bottom - (last ? last.getBoundingClientRect().bottom : box.top);
  };
  newPage();
  for (const u of units) {
    place(u);
    const heading = u.kind === "block" && /^H[23]$/.test(u.node.tagName);
    if (overflows() || (heading && remaining() < mm(30))) {
      u.node.remove();
      if (wrapper && wrapper.body.children.length === 0) { wrapper.el.remove(); wrapper = null; }
      newPage();
      place(u);
    }
  }
  const coverFooter = document.querySelector(".cover .page-footer");
  if (!coverFooter) { const f = document.createElement("div"); f.className = "page-footer"; f.innerHTML = "<span>Enterprise AI Playground · Design overview</span><span>1</span>"; document.querySelector(".cover").appendChild(f); }
  article.remove();
  return n;
});
await page.pdf({ path: resolve("docs/DESIGN.pdf"), format: "A4", printBackground: true, preferCSSPageSize: true, margin: { top: "0", right: "0", bottom: "0", left: "0" } });
await browser.close();
console.log(`wrote docs/DESIGN.pdf (${pageCount} pages)`);
