"""Turns docs/DESIGN.md into a print-ready HTML page: white A4 pages in DM Sans with the playground's violet, pink and cyan accents.

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
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&family=JetBrains+Mono:wght@400;500&display=swap');
:root { --soft: #F7F7FB; --lav: #F5F3FF; --lav-line: #E9E3FD; --band: #FAF9FE; --border: #E6E4F0; --ink: #14122B; --body: #3F4459; --muted: #6B7085;
        --violet: #7C3AED; --pink: #DB2777; --cyan: #0891B2; --grad: linear-gradient(90deg, #7C3AED, #DB2777 55%, #0891B2); }
@page { size: A4; margin: 0; }  /* pages are laid out here as fixed A4 boxes; the renderer flows the content into them */
* { box-sizing: border-box; }
html, body { background: #FFFFFF; color: var(--body); font-family: 'DM Sans', ui-sans-serif, system-ui, sans-serif; font-optical-sizing: auto;
             font-size: 10.5pt; line-height: 1.55; margin: 0; -webkit-font-smoothing: antialiased; }
.page { width: 210mm; height: 297mm; padding: 20mm 18mm 13mm; background: #FFFFFF; page-break-after: always; display: flex; flex-direction: column; position: relative; }
.page::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 2.2mm; background: var(--grad); }
.page-content { flex: 1 1 auto; overflow: hidden; }
.page-footer { height: 9mm; margin-top: 4mm; padding-top: 3mm; border-top: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; font-size: 8pt; color: var(--muted); }
.page-footer span:first-child { font-weight: 500; }
.cover .page-content { display: flex; flex-direction: column; justify-content: space-between; }
.cover .mark svg { width: 20mm; height: 20mm; display: block; }
.cover .bar { height: 2mm; width: 48mm; border-radius: 2mm; background: var(--grad); margin: 8mm 0 7mm; }
.cover h1 { font-size: 34pt; line-height: 1.05; letter-spacing: -0.03em; margin: 0; font-weight: 700; color: var(--ink); }
.cover .grad { color: var(--violet); }
.cover .sub { font-size: 15pt; color: var(--muted); margin-top: 3mm; font-weight: 500; }
.cover .intro { font-size: 11.5pt; color: var(--body); border-left: 3px solid var(--violet); padding-left: 4mm; max-width: 150mm; margin-top: 8mm; }
.cover .layers { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4mm; margin-top: 8mm; }
.cover .layers div { border: 1px solid var(--lav-line); background: var(--lav); border-radius: 3.5mm; padding: 4mm 4.5mm; font-size: 9.5pt; color: var(--body); line-height: 1.45; }
.cover .layers b { display: block; color: var(--ink); margin-bottom: 1mm; font-weight: 700; font-size: 10.5pt; }
.cover .hero { display: block; width: 92mm; margin: 6mm auto 0; border-radius: 4mm; border: 1px solid var(--border); }
.cover .meta { color: var(--muted); font-size: 9.5pt; display: flex; gap: 10mm; }
.cover .meta b { color: var(--ink); font-weight: 600; display: block; margin-bottom: 0.6mm; }
.doc h1 { display: none; }
h2 { font-size: 18pt; letter-spacing: -0.02em; font-weight: 700; color: var(--ink); margin: 9mm 0 3.5mm; line-height: 1.2; }
.page-content > h2:first-child { margin-top: 0; }
h2::before { content: ""; display: block; width: 12mm; height: 1.2mm; border-radius: 1mm; background: var(--grad); margin-bottom: 3mm; }
h3 { font-size: 12.5pt; font-weight: 600; color: var(--ink); margin: 6mm 0 2mm; break-after: avoid; }
p { margin: 2mm 0 3.5mm; break-inside: avoid; }
strong { color: var(--ink); font-weight: 600; }
table { width: 100%; border-collapse: collapse; margin: 3mm 0 5mm; font-size: 9.5pt; border: 1px solid var(--border); }
thead { display: table-row-group; break-inside: avoid; break-after: avoid; }  /* shown once per page by the renderer */
thead th { background: var(--lav); color: var(--ink); text-align: left; font-weight: 600; padding: 2.4mm 3mm; font-size: 8.5pt; letter-spacing: 0.04em; text-transform: uppercase; border-bottom: 1px solid var(--lav-line); }
thead.empty { display: none; }
td { padding: 2.2mm 3mm; vertical-align: top; border-top: 1px solid var(--border); color: var(--body); page-break-inside: avoid; }
tbody tr:nth-child(even) td { background: var(--band); }
tr { break-inside: avoid; }
td:first-child { color: var(--ink); font-weight: 600; }
ol, ul { padding-left: 6mm; margin: 2mm 0 3.5mm; }
li { margin: 1.4mm 0; break-inside: avoid; }
li::marker { color: var(--violet); font-weight: 700; }
code { font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 9pt; background: var(--lav); color: var(--ink); padding: 0.3mm 1.4mm; border-radius: 1mm; }
figure { margin: 4mm 0 6mm; break-inside: avoid; }
figure img { width: 100%; display: block; border-radius: 3.5mm; border: 1px solid var(--border); background: var(--soft); }
figcaption { color: var(--muted); font-size: 8.5pt; margin-top: 2mm; }
"""


def build() -> str:
    text = DOC.read_text(encoding="utf-8")
    title = re.match(r"#\s+(.+)", text).group(1)

    prints = {"architecture-flow": "print-layers", "workflow-flow": "print-run", "agent-flow": "print-agent"}
    in_product = {"architecture-flow", "workflow-flow"}

    def still(m: re.Match) -> str:  # animated diagrams become light print stills, with a pointer to the animated version
        alt, stem = m.group(1), Path(m.group(2)).stem
        path = (IMAGES / "deck" / f"{prints.get(stem, stem)}.png").as_posix()
        note = " The animated version plays in the product under Documentation, Design overview." if stem in in_product else ""
        return f'<figure><img src="file://{path}" alt="{alt}"><figcaption>{alt}.{note}</figcaption></figure>'

    # The print edition shows what happens inside one agent next to the agents table.
    text = text.replace("\n\n| Agent | What it is for |", "\n\n![Inside an agent: code steps, a rule, a person on exceptions and one model call](images/agent-flow.gif)\n\n| Agent | What it is for |", 1)
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
  <img class="hero" src="file://{(IMAGES / "deck" / "print-hub.png").as_posix()}" alt="The governed gateway at the centre of models, agents, knowledge, notebooks, connectors and clouds">
  <div class="meta"><span><b>Document</b>{title}</span><span><b>Date</b>{today}</span><span><b>Audience</b>IT and business decision makers</span></div>
  </div>
</section>
"""
    return f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title><style>{CSS}</style></head><body>{cover}<article class='doc'>{body}</article></body></html>"


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "images" / "DESIGN.html"
    out.write_text(build(), encoding="utf-8")
    print(f"wrote {out}")
