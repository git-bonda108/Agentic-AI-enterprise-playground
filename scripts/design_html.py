"""Turns docs/DESIGN.md into a print-ready HTML page in the playground's palette (dark surface, violet, pink and cyan accents).

Run through uvx so the markdown library needs no project dependency:
    uvx --with markdown python scripts/design_html.py <out.html>
scripts/render-design-pdf.mjs prints the result to docs/DESIGN.pdf. Animated diagrams are replaced by the still frames the
renderer captures next to them.
"""

from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "DESIGN.md"
IMAGES = ROOT / "docs" / "images"
ICON = (ROOT / "apps" / "web" / "src" / "app" / "icon.svg").read_text()

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
:root { --bg: #0a0a14; --card: #12121a; --card-2: #171628; --border: #2a2a3a; --fg: #ececf4; --muted: #a4a4b8; --violet: #8b5cf6; --pink: #ec4899; --cyan: #06b6d4; --emerald: #10b981; }
@page { size: A4; margin: 0; }  /* pages are laid out here as fixed A4 boxes; the renderer flows the content into them */
* { box-sizing: border-box; }
html, body { background: var(--bg); color: var(--fg); font-family: 'Instrument Sans', ui-sans-serif, system-ui, sans-serif; font-size: 10.5pt; line-height: 1.5; margin: 0; }
.page { width: 210mm; height: 297mm; padding: 18mm 14mm 14mm; box-sizing: border-box; background: var(--bg); page-break-after: always; display: flex; flex-direction: column; position: relative; }
.page-content { flex: 1 1 auto; overflow: hidden; }
.page-footer { height: 8mm; margin-top: 4mm; display: flex; justify-content: space-between; align-items: flex-end; font-size: 8pt; color: var(--muted); }
.cover .page-content { display: flex; flex-direction: column; justify-content: space-between; }
.cover .mark { width: 72px; height: 72px; }
.cover .mark svg { width: 72px; height: 72px; }
.cover .bar { height: 6px; width: 180px; border-radius: 4px; background: linear-gradient(90deg, var(--violet), var(--pink) 55%, var(--cyan)); margin: 28px 0 22px; }
.cover h1 { font-size: 36pt; line-height: 1.05; letter-spacing: -0.02em; margin: 0; font-weight: 700; }
.cover .sub { font-size: 16pt; color: var(--muted); margin-top: 10px; }
.cover .grad { color: #a78bfa; }
.cover .meta { color: var(--muted); font-size: 10pt; display: flex; gap: 28px; }
.cover .meta b { color: var(--fg); font-weight: 600; display: block; margin-bottom: 2px; }
.cover .layers { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 26px; }
.cover .layers div { border: 1px solid var(--border); background: var(--card); border-radius: 12px; padding: 12px 14px; font-size: 9.5pt; color: var(--muted); }
.cover .layers b { display: block; color: var(--fg); margin-bottom: 3px; font-weight: 600; }
.doc h1 { display: none; }
.cover .intro { font-size: 12pt; color: var(--muted); border-left: 3px solid var(--violet); padding-left: 12px; max-width: 150mm; margin-top: 22px; }
h2 { font-size: 17pt; letter-spacing: -0.02em; font-weight: 700; margin: 22px 0 10px; padding-top: 10px; border-top: 1px solid var(--border); }
.page-content > h2:first-child { margin-top: 0; border-top: 0; padding-top: 0; }
h2::before { content: ""; display: block; width: 46px; height: 4px; border-radius: 3px; background: linear-gradient(90deg, var(--violet), var(--pink) 55%, var(--cyan)); margin-bottom: 10px; }
h3 { font-size: 12.5pt; font-weight: 600; margin: 18px 0 6px; break-after: avoid; }
p { margin: 6px 0 10px; break-inside: avoid; }
thead { display: table-row-group; break-inside: avoid; break-after: avoid; }  /* shown once; repeated headers mis-place under pagination */
li { break-inside: avoid; }
strong { color: #fff; font-weight: 600; }
table { width: 100%; border-collapse: collapse; margin: 8px 0 14px; font-size: 9.5pt; border: 1px solid var(--border); }
thead th { background: var(--card-2); color: var(--fg); text-align: left; font-weight: 600; padding: 7px 9px; font-size: 9pt; letter-spacing: 0.02em; }
thead.empty { display: none; }
td { padding: 6px 9px; vertical-align: top; border-top: 1px solid var(--border); color: var(--fg); page-break-inside: avoid; }
tbody tr:nth-child(even) td { background: #0f0f1a; }
tr { break-inside: avoid; }
td:first-child { color: #fff; font-weight: 500; }
ol, ul { padding-left: 20px; margin: 6px 0 10px; }
li { margin: 3px 0; }
li::marker { color: var(--violet); font-weight: 600; }
code { font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 9pt; background: var(--card-2); padding: 1px 5px; border-radius: 4px; }
figure { margin: 10px 0 16px; break-inside: avoid; }
figure img { width: 100%; border-radius: 12px; border: 1px solid var(--border); display: block; }
figcaption { color: var(--muted); font-size: 9pt; margin-top: 6px; }
"""


def build() -> str:
    text = DOC.read_text(encoding="utf-8")
    title = re.match(r"#\s+(.+)", text).group(1)

    def still(m: re.Match) -> str:  # animated diagrams become still frames, with a pointer to the animated version
        alt, src = m.group(1), m.group(2)
        path = (IMAGES / f"{Path(src).stem}-still.png").as_posix()
        return f'<figure><img src="file://{path}" alt="{alt}"><figcaption>{alt}. The animated version plays in the product under Documentation, Design overview.</figcaption></figure>'

    text = re.sub(r"!\[([^\]]*)\]\(images/([^)]+)\)", still, text)
    # The first paragraph is the document's purpose statement: it belongs on the cover.
    intro_match = re.search(r"^#\s+.+?\n\n(.+?)\n\n", text, re.DOTALL)
    intro = intro_match.group(1).replace("\n", " ") if intro_match else ""
    if intro_match:
        text = text.replace(intro_match.group(1) + "\n\n", "", 1)
    body = markdown.markdown(text, extensions=["tables", "sane_lists", "smarty"])
    body = body.replace("<thead>\n<tr>\n<th></th>\n<th></th>\n</tr>\n</thead>", '<thead class="empty"></thead>')  # the key-value table has no header
    today = dt.datetime.now(tz=dt.UTC).strftime("%d %B %Y")
    cover = f"""
<section class="cover page">
  <div class="page-content">
  <div>
    <div class="mark">{ICON}</div>
    <div class="bar"></div>
    <h1>Enterprise AI <span class="grad">Playground</span></h1>
    <div class="sub">{title}</div>
    <p class="intro">{intro}</p>
    <div class="layers">
      <div><b>Governed</b>Identity, policy and budget before every call; one ledger row after it.</div>
      <div><b>Agentic</b>Blueprints as explicit steps, review gates for people, evaluation and canaries.</div>
      <div><b>Open</b>Thirty models, any SDK through one gateway, four cloud runtimes, no lock-in.</div>
    </div>
  </div>
  <div class="meta"><span><b>Document</b>{title}</span><span><b>Date</b>{today}</span><span><b>Audience</b>IT and business decision makers</span></div>
  </div>
</section>
"""
    return f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title><style>{CSS}</style></head><body>{cover}<article class='doc'>{body}</article></body></html>"


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "images" / "DESIGN.html"
    out.write_text(build(), encoding="utf-8")
    print(f"wrote {out}")
