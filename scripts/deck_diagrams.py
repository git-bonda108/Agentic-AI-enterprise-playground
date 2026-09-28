"""Generates the light-theme animated diagrams used in the client deck (docs/images/deck/<name>.svg).

Each diagram is an SVG whose light beam is driven by SMIL on one repeating cycle, so scripts/render-deck-gifs.mjs can step
the clock frame by frame and encode a looping GIF. Run: python3 scripts/deck_diagrams.py
"""

from __future__ import annotations

import math
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs" / "images" / "deck"

BG, CARD, BORDER, WIRE = "#F7F7FB", "#FFFFFF", "#E4E2F0", "#D9D5EA"
INK, BODY, MUTED = "#14122B", "#454A63", "#6B7085"
VIOLET, PINK, CYAN, EMERALD, AMBER = "#7C3AED", "#DB2777", "#0891B2", "#059669", "#D97706"
FONT = "Sora, ui-sans-serif, system-ui, sans-serif"  # the closest open face to Styrene A


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def defs() -> str:
    return f"""<defs>
  <linearGradient id="brand" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{VIOLET}"/><stop offset="0.55" stop-color="{PINK}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>
  <linearGradient id="brandv" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{VIOLET}"/><stop offset="0.55" stop-color="{PINK}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>
  <radialGradient id="glow"><stop offset="0" stop-color="#FFFFFF"/><stop offset="0.3" stop-color="#F0ABFC"/><stop offset="0.65" stop-color="{VIOLET}" stop-opacity="0.35"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>
  <filter id="soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="10"/></filter>
  <filter id="shadow" x="-10%" y="-10%" width="120%" height="140%"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#1E1B4B" flood-opacity="0.06"/></filter>
</defs>"""


def window(T: float, b: float, d: float, fade: float = 0.25) -> tuple[str, str]:
    """keyTimes and values for an opacity that is 1 inside [b, b+d] and 0 elsewhere, with short fades."""
    pts = [(0, 0), (max(b - fade, 0), 0), (b, 1), (min(b + d, T), 1), (min(b + d + fade, T), 0), (T, 0)]
    clean: list[tuple[float, float]] = []
    for t, v in pts:
        if clean and t <= clean[-1][0]:
            t = clean[-1][0] + 0.0001
        clean.append((min(t, T), v))
    clean[-1] = (T, clean[-1][1])
    kt = ";".join(f"{t / T:.4f}" for t, _ in clean)
    vals = ";".join(str(v) for _, v in clean)
    return kt, vals


def beam(path: str, T: float, b: float, d: float) -> str:
    """A travelling light on `path`: a gradient trail plus a glowing head, visible only during [b, b+d]."""
    e = 0.0001
    kt = f"0;{b / T:.4f};{min((b + d) / T, 1 - e):.4f};1"
    kt_op, vals_op = window(T, b, d, 0.12)
    return f"""<g opacity="0"><animate attributeName="opacity" dur="{T}s" repeatCount="indefinite" keyTimes="{kt_op}" values="{vals_op}"/>
  <path d="{path}" fill="none" stroke="url(#brand)" stroke-width="5" stroke-linecap="round" pathLength="100" stroke-dasharray="22 78" stroke-dashoffset="22">
    <animate attributeName="stroke-dashoffset" dur="{T}s" repeatCount="indefinite" keyTimes="{kt}" values="22;22;-100;-100"/></path>
  <circle r="16" fill="url(#glow)"><animateMotion dur="{T}s" repeatCount="indefinite" path="{path}" keyPoints="0;0;1;1" keyTimes="{kt}" calcMode="linear"/></circle>
  <circle r="4.5" fill="#FFFFFF"><animateMotion dur="{T}s" repeatCount="indefinite" path="{path}" keyPoints="0;0;1;1" keyTimes="{kt}" calcMode="linear"/></circle>
</g>"""


def highlight(x: float, y: float, w: float, h: float, r: float, T: float, b: float, d: float, fill: str = "#F5F3FF") -> str:
    kt, vals = window(T, b, d)
    return f"""<g opacity="0"><animate attributeName="opacity" dur="{T}s" repeatCount="indefinite" keyTimes="{kt}" values="{vals}"/>
  <rect x="{x - 4}" y="{y - 4}" width="{w + 8}" height="{h + 8}" rx="{r + 4}" fill="{VIOLET}" opacity="0.22" filter="url(#soft)"/>
  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="url(#brand)" stroke-width="3"/>
</g>"""


def text(x: float, y: float, s: str, size: int, weight: int = 400, fill: str = INK, anchor: str = "start", spacing: float = 0) -> str:
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{ls}>{esc(s)}</text>'


def svg(w: int, h: int, body: str) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" font-family="{FONT}">{defs()}<rect width="{w}" height="{h}" fill="{BG}"/>{body}</svg>'


# ---------------------------------------------------------------- layers: how a request travels
def layers() -> str:
    W, H, T = 1600, 720, 10.0
    bands = [
        ("People and clients", "One door for every tool", [("Web app", "playground · agents · notebooks"), ("OpenAI-compatible SDKs", "LangGraph · CrewAI · ADK"), ("MCP clients", "Claude · Cursor · VS Code"), ("Low-code studios", "Langflow · n8n · Copilot Studio")]),
        ("Governance", "Nothing runs ungoverned", [("Identity", "Entra · Google · Okta · OIDC"), ("Role policy", "models · tools · connectors"), ("Budgets", "person · department · organisation"), ("Keys", "platform or personal, encrypted")]),
        ("Reasoning", "Predictable agents", [("Smart routing", "cheapest capable model"), ("Blueprints", "explicit step graphs"), ("Review gates", "pause · approve · resume"), ("Evaluation", "golden sets · canary · rollback")]),
        ("Knowledge and data", "Grounded answers", [("Knowledge Spaces", "hybrid search · citations"), ("Datasets", "mock sets · trusted sources"), ("Sandboxes", "notebooks · framework projects"), ("PostgreSQL", "runs · evaluations · ledger")]),
        ("Integrations", "Choice without lock-in", [("Models", "30 models · 11 providers"), ("MCP servers", "7,500 · admin approved"), ("Cloud runtimes", "Azure · AWS · Google · Anthropic"), ("Git and skills", "reference implementations")]),
        ("Ledger", "Cost that reconciles", [("One row per call", "who · feature · model · tokens in, out and cached · cost · latency · key · trace")]),
    ]
    bh, gap, top = 100, 20, 10
    spine = 342
    out = [f'<line x1="{spine}" y1="{top}" x2="{spine}" y2="{top + 6 * bh + 5 * gap}" stroke="{WIRE}" stroke-width="2" stroke-dasharray="2 6"/>']
    step = 1.35
    for i, (name, promise, chips) in enumerate(bands):
        y = top + i * (bh + gap)
        b = 0.3 + i * step
        out.append(f'<rect x="10" y="{y}" width="{W - 20}" height="{bh}" rx="18" fill="{CARD}" stroke="{BORDER}" filter="url(#shadow)"/>')
        out.append(highlight(10, y, W - 20, bh, 18, T, b + 0.35, step * (len(bands) - i) + 0.4, fill="#FBFAFF"))
        out.append(text(36, y + 45, name, 22, 600))
        out.append(text(36, y + 74, promise, 16, 500, VIOLET))
        cx0, cw, cg = 372, 282, 20
        if len(chips) == 1:
            cw = 4 * 282 + 3 * 20
        for j, (t, s) in enumerate(chips):
            cx = cx0 + j * (cw + cg)
            out.append(f'<rect x="{cx}" y="{y + 16}" width="{cw}" height="{bh - 32}" rx="12" fill="#F4F3FA" stroke="{BORDER}"/>')
            out.append(highlight(cx, y + 16, cw, bh - 32, 12, T, b + 0.45 + j * 0.16, 0.55, fill="#FFFFFF"))  # a brief shimmer as the light passes
            out.append(text(cx + 16, y + 45, t, 18, 600))
            out.append(text(cx + 16, y + 69, s, 14, 400, MUTED))
    out.append(beam(f"M {spine} {top} L {spine} {top + 6 * bh + 5 * gap}", T, 0.1, 6 * step + 0.2))
    return svg(W, H, "".join(out))


# ---------------------------------------------------------------- run: one agent run, start to finish
def run() -> str:
    W, H, T = 1600, 600, 12.0
    steps = [
        ("01 · ASK", "Blueprint and input", ["A person, a schedule, an SDK", "call or an MCP client starts it"]),
        ("02 · GOVERN", "Policy, budget, key", ["Role decides models and tools;", "a cap stops the call first"]),
        ("03 · ROUTE", "Smart routing", ["The cheapest capable model;", "the saving is recorded"]),
        ("04 · REASON", "Steps, tools, retrieval", ["Code where it can be, the model", "where judgement is needed"]),
        ("05 · REVIEW", "Human gate", ["An exception pauses the run;", "a person approves or rejects"]),
        ("06 · ANSWER", "Output and trace", ["Every step, token, dollar", "and citation, visible"]),
        ("07 · IMPROVE", "Evaluate and canary", ["Golden cases graded nightly;", "drift rolls back"]),
        ("08 · SHARE", "Notebook, SDK, cloud", ["The same run as a notebook,", "a project or a deployment"]),
    ]
    nw, nh, gap = 362, 170, 50
    x0, rows = 1, (60, 370)
    pos = []
    for i in range(8):
        col = i if i < 4 else 7 - i
        pos.append((x0 + col * (nw + gap), rows[0] if i < 4 else rows[1]))
    out = []
    # wires between consecutive nodes
    paths = []
    for i in range(7):
        (ax, ay), (bx, by) = pos[i], pos[i + 1]
        if ay == by:
            if bx > ax:
                p = f"M {ax + nw} {ay + nh / 2} L {bx} {by + nh / 2}"
            else:
                p = f"M {ax} {ay + nh / 2} L {bx + nw} {by + nh / 2}"
        else:
            p = f"M {ax + nw / 2} {ay + nh} L {bx + nw / 2} {by}"
        paths.append(p)
        out.append(f'<path d="{p}" stroke="{WIRE}" stroke-width="2.5" fill="none"/>')
    # timing: each node lights for `dwell`; travel `hop` between; review holds longer
    t, hop, dwell = 0.2, 0.45, 0.75
    lights = []
    for i in range(8):
        hold = 2.4 if i == 4 else dwell
        lights.append((t, hold))
        if i < 7:
            out.append(beam(paths[i], T, t + hold, hop))
        t += hold + hop
    for i, ((x, y), (eyebrow, title, sub)) in enumerate(zip(pos, steps, strict=True)):
        accent = PINK if i == 4 else VIOLET
        out.append(f'<rect x="{x}" y="{y}" width="{nw}" height="{nh}" rx="18" fill="{CARD}" stroke="{BORDER}" filter="url(#shadow)"/>')
        b, d = lights[i]
        out.append(highlight(x, y, nw, nh, 18, T, b, d + 0.2))
        out.append(text(x + 24, y + 40, eyebrow, 14, 600, accent, spacing=1.4))
        out.append(text(x + 24, y + 76, title, 22, 600))
        out.append(text(x + 24, y + 110, sub[0], 16, 400, BODY))
        out.append(text(x + 24, y + 134, sub[1], 16, 400, BODY))
    # the review pause: a pill that waits, then approves
    rx, ry = pos[4]
    b, d = lights[4]
    kt, vals = window(T, b + 0.2, 1.3, 0.15)
    out.append(f'<g opacity="0"><animate attributeName="opacity" dur="{T}s" repeatCount="indefinite" keyTimes="{kt}" values="{vals}"/><rect x="{rx + nw - 214}" y="{ry - 22}" width="200" height="40" rx="20" fill="#FEF3C7" stroke="{AMBER}"/>{text(rx + nw - 114, ry + 4, "Waiting for a reviewer", 15, 600, "#92400E", "middle")}</g>')
    kt, vals = window(T, b + 1.55, 1.0, 0.15)
    out.append(f'<g opacity="0"><animate attributeName="opacity" dur="{T}s" repeatCount="indefinite" keyTimes="{kt}" values="{vals}"/><rect x="{rx + nw - 214}" y="{ry - 22}" width="200" height="40" rx="20" fill="#D1FAE5" stroke="{EMERALD}"/>{text(rx + nw - 114, ry + 4, "Approved, resuming", 15, 600, "#065F46", "middle")}</g>')
    return svg(W, H, "".join(out))


# ---------------------------------------------------------------- agent: inside one agent
def agent() -> str:
    W, H, T = 1600, 560, 15.0
    kinds = {"tool": ("TOOL · CODE, NO MODEL", CYAN), "gate": ("GATE · A RULE DECIDES", AMBER), "human": ("HUMAN · PERSON DECIDES", PINK), "model": ("MODEL · NARROW BRIEF", VIOLET)}
    nw, nh = 244, 138
    nodes = {
        "load": (8, 70, "tool", "Load documents", "invoices, orders, contracts"),
        "extract": (284, 70, "tool", "Extract fields", "per-field confidence"),
        "validate": (560, 70, "tool", "Validate", "tolerances, master data"),
        "gate": (836, 70, "gate", "Quality gate", "clean or exception"),
        "human": (1092, 360, "human", "Human decision", "approve or reject"),
        "summary": (1348, 70, "model", "Write summary", "exceptions for finance"),
    }

    def right(n: str) -> tuple[float, float]:
        x, y = nodes[n][:2]
        return x + nw, y + nh / 2

    def left(n: str) -> tuple[float, float]:
        x, y = nodes[n][:2]
        return x, y + nh / 2

    seg = {
        "le": f"M {right('load')[0]} {right('load')[1]} L {left('extract')[0]} {left('extract')[1]}",
        "ev": f"M {right('extract')[0]} {right('extract')[1]} L {left('validate')[0]} {left('validate')[1]}",
        "vg": f"M {right('validate')[0]} {right('validate')[1]} L {left('gate')[0]} {left('gate')[1]}",
        "gs": f"M {right('gate')[0]} {right('gate')[1]} L {left('summary')[0]} {left('summary')[1]}",
        "gh": f"M {nodes['gate'][0] + nw / 2} {nodes['gate'][1] + nh} C {nodes['gate'][0] + nw / 2} {nodes['human'][1] + nh / 2} {nodes['gate'][0] + nw / 2} {nodes['human'][1] + nh / 2} {left('human')[0]} {left('human')[1]}",
        "hs": f"M {right('human')[0]} {right('human')[1]} C {nodes['summary'][0] + nw / 2} {nodes['human'][1] + nh / 2} {nodes['summary'][0] + nw / 2} {nodes['human'][1] + nh / 2} {nodes['summary'][0] + nw / 2} {nodes['summary'][1] + nh}",
    }
    out = [f'<path d="{d}" stroke="{WIRE}" stroke-width="2.5" fill="none"/>' for d in seg.values()]
    out.append(text(nodes["gate"][0] + nw + 40, nodes["gate"][1] + nh / 2 - 14, "clean", 16, 600, EMERALD))
    out.append(text(nodes["gate"][0] + nw / 2 + 16, nodes["human"][1] - 30, "exception", 16, 600, PINK))
    # two passes: a clean invoice, then an exception that waits for a person
    hop, dwell = 0.45, 0.6
    plan = [
        [("load", 0), ("extract", 0), ("validate", 0), ("gate", 0), ("summary", 0)],
        [("load", 0), ("extract", 0), ("validate", 0), ("gate", 0), ("human", 1.8), ("summary", 0)],
    ]
    edge = {("load", "extract"): "le", ("extract", "validate"): "ev", ("validate", "gate"): "vg", ("gate", "summary"): "gs", ("gate", "human"): "gh", ("human", "summary"): "hs"}
    lights: list[tuple[str, float, float]] = []
    t = 0.2
    for p, passes in enumerate(plan):
        for k, (n, extra) in enumerate(passes):
            hold = dwell + extra
            lights.append((n, t, hold))
            if k < len(passes) - 1:
                nxt = passes[k + 1][0]
                out.append(beam(seg[edge[(n, nxt)]], T, t + hold, hop if edge[(n, nxt)] not in ("gh", "hs") else 0.8))
                t += hold + (hop if edge[(n, nxt)] not in ("gh", "hs") else 0.8)
            else:
                t += hold
        if p == 0:
            t += 0.9
    for n, (x, y, kind, title, sub) in nodes.items():
        label, colour = kinds[kind]
        out.append(f'<rect x="{x}" y="{y}" width="{nw}" height="{nh}" rx="18" fill="{CARD}" stroke="{BORDER}" filter="url(#shadow)"/>')
        for ln, b, d in lights:
            if ln == n:
                out.append(highlight(x, y, nw, nh, 18, T, b, d + 0.15))
        out.append(f'<rect x="{x + 20}" y="{y + 20}" width="{nw - 40}" height="4" rx="2" fill="{colour}"/>')
        out.append(text(x + 20, y + 52, label, 11, 700, colour, spacing=0.6))
        out.append(text(x + 20, y + 86, title, 21, 600))
        out.append(text(x + 20, y + 114, sub, 15, 400, MUTED))
    hx, hy = nodes["human"][:2]
    hb = next(b for n, b, _ in lights if n == "human")
    kt, vals = window(T, hb + 0.1, 1.9, 0.15)
    out.append(f'<g opacity="0"><animate attributeName="opacity" dur="{T}s" repeatCount="indefinite" keyTimes="{kt}" values="{vals}"/><rect x="{hx + 11}" y="{hy - 60}" width="210" height="42" rx="21" fill="#FCE7F3" stroke="{PINK}"/>{text(hx + 116, hy - 33, "Paused, checkpointed", 15, 600, "#9D174D", "middle")}</g>')
    return svg(W, H, "".join(out))


# ---------------------------------------------------------------- hub: the cover
def hub() -> str:
    W = H = 820
    T = 9.0
    cx = cy = W / 2
    out = []
    # governance ring
    out.append(f'<circle cx="{cx}" cy="{cy}" r="178" fill="none" stroke="{BORDER}" stroke-width="2"/>')
    out.append(f'<circle cx="{cx}" cy="{cy}" r="178" fill="none" stroke="url(#brand)" stroke-width="3" stroke-dasharray="60 1058" stroke-linecap="round"><animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" to="360 {cx} {cy}" dur="{T}s" repeatCount="indefinite"/></circle>')
    sats = ["Models", "Agents", "Knowledge", "Notebooks", "Connectors", "Clouds"]
    subs = ["30 across 11 providers", "175 blueprints", "cited answers", "browser or sandbox", "7,500 MCP servers", "Azure · AWS · Google"]
    R = 318
    step = T / len(sats)
    for i, (s, sub) in enumerate(zip(sats, subs, strict=True)):
        a = -math.pi / 2 + i * 2 * math.pi / len(sats)
        sx, sy = cx + R * math.cos(a), cy + R * math.sin(a)
        ex, ey = cx + 120 * math.cos(a), cy + 120 * math.sin(a)
        tx, ty = cx + (R - 60) * math.cos(a), cy + (R - 60) * math.sin(a)
        p = f"M {ex:.1f} {ey:.1f} L {tx:.1f} {ty:.1f}"
        out.append(f'<path d="{p}" stroke="{WIRE}" stroke-width="2.5"/>')
        b = 0.15 + i * step
        out.append(beam(p, T, b, 0.7))
        w, h = 200, 76
        out.append(f'<rect x="{sx - w / 2:.1f}" y="{sy - h / 2:.1f}" width="{w}" height="{h}" rx="16" fill="{CARD}" stroke="{BORDER}" filter="url(#shadow)"/>')
        out.append(highlight(sx - w / 2, sy - h / 2, w, h, 16, T, b + 0.65, step - 0.2))
        out.append(text(sx, sy - 4, s, 22, 600, INK, "middle"))
        out.append(text(sx, sy + 22, sub, 15, 400, MUTED, "middle"))
    # governance labels on the ring
    for lbl, ang in (("Identity", -135), ("Policy", -45), ("Budget", 45), ("Ledger", 135)):
        a = math.radians(ang)
        lx, ly = cx + 178 * math.cos(a), cy + 178 * math.sin(a)
        out.append(f'<rect x="{lx - 58:.1f}" y="{ly - 18:.1f}" width="116" height="36" rx="18" fill="#F5F3FF" stroke="#DDD6FE"/>')
        out.append(text(lx, ly + 6, lbl, 15, 600, VIOLET, "middle"))
    # hub
    out.append(f'<circle cx="{cx}" cy="{cy}" r="118" fill="{VIOLET}" opacity="0.14" filter="url(#soft)"/>')
    out.append(f'<circle cx="{cx}" cy="{cy}" r="112" fill="{CARD}" stroke="url(#brand)" stroke-width="4"/>')
    out.append(text(cx, cy - 8, "Governed", 27, 700, INK, "middle"))
    out.append(text(cx, cy + 24, "gateway", 27, 700, INK, "middle"))
    return svg(W, H, "".join(out))


# ---------------------------------------------------------------- journeys: the features used together
def journeys() -> str:
    W, H, T = 1600, 600, 12.5
    rows = [
        ("Choose the right model", "best answer, lowest price", ["Models", "Compare four", "Smart routing", "Cost savings"]),
        ("Blueprint to production", "an agent you can trust", ["Blueprint", "Run on mock data", "Notebook", "Golden set, gate", "Nightly canary", "Cloud guide"]),
        ("Agent on your own data", "grounded, auditable answers", ["Your documents", "Knowledge Space", "Wizard agent", "Skills, MCP tools", "Run", "Trace, citations"]),
        ("Bring your own code", "existing code, now governed", ["Personal token", "SDK gateway", "Framework project", "Sandbox run", "Traces, cost"]),
        ("Prove the value", "results leaders can defend", ["Console", "Cost drill-down", "Adoption, ROI", "Showcase", "Leaderboard"]),
    ]
    rh, gap, top = 96, 18, 22
    cx0, cw, cg = 340, 191, 20
    out = []
    per = T / len(rows)
    for i, (name, outcome, chips) in enumerate(rows):
        y = top + i * (rh + gap)
        b = 0.15 + i * per
        out.append(f'<rect x="4" y="{y}" width="{W - 8}" height="{rh}" rx="18" fill="{CARD}" stroke="{BORDER}" filter="url(#shadow)"/>')
        out.append(highlight(4, y, W - 8, rh, 18, T, b, per - 0.25, fill="#FBFAFF"))
        out.append(text(28, y + 44, name, 20, 600))
        out.append(text(28, y + 70, outcome, 15, 500, VIOLET))
        n = len(chips)
        x_end = cx0 + n * cw + (n - 1) * cg
        cy = y + rh / 2
        out.append(f'<line x1="{cx0}" y1="{cy}" x2="{x_end}" y2="{cy}" stroke="{WIRE}" stroke-width="2.5"/>')
        d = 0.32 * n + 0.2
        for j, c in enumerate(chips):
            x = cx0 + j * (cw + cg)
            out.append(f'<rect x="{x}" y="{y + 20}" width="{cw}" height="{rh - 40}" rx="12" fill="#F4F3FA" stroke="{BORDER}"/>')
            tj = b + 0.1 + d * (j + 0.5) / n
            out.append(highlight(x, y + 20, cw, rh - 40, 12, T, tj, b + per - 0.35 - tj, fill="#FFFFFF"))
            out.append(text(x + cw / 2, cy + 6, c, 16, 600, INK, "middle"))
        out.append(beam(f"M {cx0} {cy} L {x_end} {cy}", T, b + 0.1, d))
    return svg(W, H, "".join(out))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in (("hub", hub), ("layers", layers), ("run", run), ("agent", agent), ("journeys", journeys)):
        (OUT / f"{name}.svg").write_text(fn(), encoding="utf-8")
        print(f"wrote docs/images/deck/{name}.svg")
