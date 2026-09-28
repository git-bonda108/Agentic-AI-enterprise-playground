"""Writes the client deck (Slides artifact) as project/deck.json plus one project/slides/<id>.html per slide.

Usage: python3 scripts/build_deck.py <out-root> <current deck.json>. Image sources are asset urls already uploaded to the
deck; the animated diagrams come from `npm run deck:gifs`. Typeface: Sora, the closest open face to Styrene A.
"""
import json, sys
from pathlib import Path

ROOT = Path(sys.argv[1]); SL = ROOT / "project" / "slides"; SL.mkdir(parents=True, exist_ok=True)

BG, ALT, CARD, BORDER = "#F7F7FB", "#EFEDF8", "#FFFFFF", "#E4E2F0"
INK, BODY, MUTED = "#14122B", "#454A63", "#5F6478"
VIOLET, PINK, CYAN, EMERALD, AMBER = "#7C3AED", "#DB2777", "#0891B2", "#047857", "#B45309"
DEEP = "#3B0764"
FONT = "'Sora', Verdana, sans-serif"
MONO = "'JetBrains Mono', 'Courier New', monospace"
GRAD = f"linear-gradient(90deg, {VIOLET} 0%, {PINK} 55%, {CYAN} 100%)"
SHADOW = "0 12px 32px rgba(30,27,75,0.08)"

A = {
    "hub": "/_blob/73466785a35231be7d9bb48b8388cfb8", "layers": "/_blob/0ab1bf0052f364aa6f1fe2f7aa031afe",
    "run": "/_blob/272d2584db0e12554ab9521f2f505ddd", "agent": "/_blob/d7ccc173d723f3a64482372dddc9b14f",
    "journeys": "/_blob/e181975b6d6ab3786c7112b0c0be83fd",
    "console": "/_blob/5ae1eb36fde1b03ea9bd65e90db69dd9", "models": "/_blob/fea3ba5c3c0b556b0eb7e4a9fd011277",
    "agents": "/_blob/7e633c6188c5ddcc7a75211cc14d57a8", "policies": "/_blob/f30d917584f04b59ceba8cce5caa9c61",
    "canary": "/_blob/0e4e03698fa3431e3f4e2d481c0b8720", "cost": "/_blob/a7baf41da7f7cf42907ef2e3eb11d679",
    "adoption": "/_blob/4de5c5e171cb58248c5ab4b29823b0ba", "connectors": "/_blob/b011bbe9d205f429a9a22b89b4e6409b",
}

MARK = ('<svg aria-label="Enterprise AI Playground mark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64" style="width:{s}px; height:{s}px">'
        '<defs><linearGradient id="mk{k}" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#7c3aed"/><stop offset="55%" stop-color="#c026d3"/><stop offset="100%" stop-color="#06b6d4"/></linearGradient></defs>'
        '<rect width="64" height="64" rx="17" fill="url(#mk{k})"/><g transform="translate(8 8) scale(0.75)">'
        '<circle cx="32" cy="32" r="21" stroke="#fff" stroke-opacity="0.45" stroke-width="1.8" stroke-dasharray="3.5 4.5" fill="none"/>'
        '<path d="M32 32 L32 11 M32 32 L13.8 42.5 M32 32 L50.2 42.5" stroke="#fff" stroke-opacity="0.9" stroke-width="2.8" stroke-linecap="round"/>'
        '<circle cx="32" cy="11" r="5.5" fill="#fff"/><circle cx="13.8" cy="42.5" r="5.5" fill="#fff"/><circle cx="50.2" cy="42.5" r="5.5" fill="#fff"/>'
        '<circle cx="32" cy="32" r="9" fill="#fff"/><path d="M53 8 L54.6 12.4 L59 14 L54.6 15.6 L53 20 L51.4 15.6 L47 14 L51.4 12.4 Z" fill="#fff"/></g></svg>')

ORDER: list[str] = []
SECTIONS: dict = {}
PART = {"label": ""}

def section(sid, body, bg=BG, footer=True, extra="", layout=None, transition="fade"):
    ORDER.append(sid); num = len(ORDER)
    lay = layout or f"padding:{'128px 128px 160px' if footer else '128px'}; display:flex; flex-direction:column; gap:48px"
    foot = ""
    if footer:
        fc = "#C4B5FD" if bg == DEEP else MUTED
        left = "Enterprise AI Playground" + (f"  ·  {PART['label']}" if PART["label"] else "")
        foot = (f'<p style="position:absolute; left:128px; bottom:64px; width:1200px; font-size:24px; color:{fc}">{left}</p>'
                f'<p style="position:absolute; right:128px; bottom:64px; width:200px; font-size:24px; color:{fc}; text-align:right">{num:02d}</p>')
    (SL / f"{sid}.html").write_text(f'<section id="{sid}" data-transition="{transition}" style="background:{bg}; color:{INK}; font-family:{FONT}; {lay}">\n{body}\n{extra}{foot}\n</section>\n', encoding="utf-8")

def header(eyebrow, title, dark=False):
    ec, tc = ("#C4B5FD", "#FFFFFF") if dark else (VIOLET, INK)
    return (f'<div style="display:flex; flex-direction:column; gap:16px">'
            f'<div style="width:72px; height:6px; border-radius:3px; background:{GRAD}"></div>'
            f'<p style="font-size:24px; font-weight:600; letter-spacing:3px; color:{ec}; text-transform:uppercase">{eyebrow}</p>'
            f'<h2 style="font-size:64px; font-weight:600; line-height:1.1; letter-spacing:-1px; color:{tc}">{title}</h2></div>')

def shot(key, w, h, alt):
    return (f'<img src="{A[key]}" alt="{alt}" style="width:{w}px; height:{h}px; object-fit:contain; border-radius:16px; '
            f'border:1px solid {BORDER}; box-shadow:{SHADOW}; background:{CARD}">')

def item(title, text, size=24):
    return (f'<div style="display:flex; flex-direction:column; gap:6px">'
            f'<p style="font-size:28px; font-weight:600; line-height:1.25; color:{INK}">{title}</p>'
            f'<p style="font-size:{size}px; line-height:1.4; color:{BODY}">{text}</p></div>')

def card(inner, pad=40, gap=16, flex="flex:1", bg=CARD, border=BORDER):
    return (f'<div style="{flex}; display:flex; flex-direction:column; gap:{gap}px; background:{bg}; border:1px solid {border}; '
            f'border-radius:24px; padding:{pad}px; box-shadow:{SHADOW}">{inner}</div>')

def icon(name, color=VIOLET, size=56):
    return f'<x-icon name="{name}" style="color:{color}; width:{size}px; height:{size}px"></x-icon>'

def pill(text, color=VIOLET, bg="#F1ECFE", size=24, pad="10px 24px"):
    return f'<p style="font-size:{size}px; font-weight:600; color:{color}; background:{bg}; padding:{pad}; border-radius:999px; white-space:nowrap">{text}</p>'

def beam_embed(left, top, width, height, n, gap, radius=24, period=7):
    tile = (width - (n - 1) * gap) / n; rects = ""
    for i in range(n):
        x = i * (tile + gap) + 1.5; d = f"animation-delay:-{i * period / n:.2f}s"
        for cls in ("r gl", "r"):
            rects += f'<rect class="{cls}" x="{x:.1f}" y="1.5" width="{tile - 3:.1f}" height="{height - 3}" rx="{radius}" pathLength="100" style="{d}"/>'
    return (f'<x-embed style="position:absolute; left:{left}px; top:{top}px; width:{width}px; height:{height}px">'
            f'<style>html,body{{margin:0;background:transparent;overflow:hidden}}'
            f'.r{{fill:none;stroke:url(#g);stroke-width:3;stroke-linecap:round;stroke-dasharray:13 87;animation:run {period}s linear infinite}}'
            f'.gl{{stroke-width:9;filter:url(#b);opacity:.5}}@keyframes run{{from{{stroke-dashoffset:0}}to{{stroke-dashoffset:-100}}}}'
            f'@media (prefers-reduced-motion: reduce){{.r{{animation:none;opacity:0}}}}</style>'
            f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"><defs>'
            f'<linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{VIOLET}"/><stop offset=".55" stop-color="{PINK}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>'
            f'<filter id="b" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="4"/></filter></defs>{rects}</svg></x-embed>\n')

def pinned_tiles(top, height, tiles, n=4, gap=32):
    tile = (1664 - (n - 1) * gap) / n; out = ""
    for i, inner in enumerate(tiles):
        out += (f'<div style="position:absolute; left:{128 + i * (tile + gap):.0f}px; top:{top}px; width:{tile:.0f}px; height:{height}px; '
                f'background:{CARD}; border:1px solid {BORDER}; border-radius:24px; padding:40px; display:flex; flex-direction:column; gap:20px; box-shadow:{SHADOW}">{inner}</div>\n')
    return out

def divider(sid, part, title, text, topics, big):
    tp = "".join(pill(t, INK, CARD) for t in topics)
    section(sid, (
        f'<p style="font-size:28px; font-weight:600; letter-spacing:4px; color:{VIOLET}; text-transform:uppercase">{part}</p>'
        f'<h1 style="font-size:96px; font-weight:700; line-height:1.05; letter-spacing:-2px; color:{INK}; width:1100px">{title}</h1>'
        f'<div style="width:200px; height:8px; border-radius:4px; background:{GRAD}"></div>'
        f'<p style="font-size:36px; line-height:1.35; color:{BODY}; width:1080px">{text}</p>'
        f'<div style="display:flex; gap:12px; flex-wrap:wrap; width:1100px">{tp}</div>'),
        bg=ALT, footer=False, transition="push",
        layout="padding:128px; display:flex; flex-direction:column; justify-content:center; gap:36px",
        extra=(f'<p style="position:absolute; left:1232px; top:300px; width:560px; font-size:400px; font-weight:700; line-height:1; letter-spacing:-12px; '
               f'text-align:right; background:{GRAD}; background-clip:text; -webkit-text-fill-color:transparent; color:{VIOLET}">{big}</p>\n'))

def asset_card(ic, name, count, find, can):
    return card(
        f'<div style="display:flex; gap:16px; align-items:center">{icon(ic, VIOLET, 44)}'
        f'<h3 style="flex:1; font-size:32px; font-weight:600; color:{INK}">{name}</h3>{pill(count, VIOLET, "#F1ECFE", 24, "6px 18px")}</div>'
        f'<p style="font-size:24px; line-height:1.4; color:{BODY}"><b style="color:{INK}">You find</b>  {find}</p>'
        f'<p style="font-size:24px; line-height:1.4; color:{BODY}"><b style="color:{VIOLET}">You can</b>  {can}</p>', pad=32, gap=14)

# =============================== OPENING ===============================
section("cover", (
    f'<div style="flex:1; display:flex; flex-direction:column; gap:32px">'
    f'{MARK.format(s=112, k="c")}'
    f'<div style="width:200px; height:8px; border-radius:4px; background:{GRAD}"></div>'
    f'<h1 style="font-size:88px; font-weight:700; line-height:1.05; letter-spacing:-2px; color:{INK}">Enterprise AI <span style="color:{VIOLET}">Playground</span></h1>'
    f'<p style="font-size:40px; line-height:1.3; color:{BODY}">One governed place to explore every model, build agents and see every token and dollar.</p>'
    f'<div style="display:flex; gap:16px; flex-wrap:wrap">{pill("Governed")}{pill("Agentic", PINK, "#FCE7F3")}{pill("Open", CYAN, "#E0F5FA")}{pill("Measured", EMERALD, "#DCF5EA")}</div></div>'
    f'<img src="{A["hub"]}" alt="A governed gateway at the centre, with light travelling out to models, agents, knowledge, notebooks, connectors and clouds" style="width:760px; height:760px; object-fit:contain">'),
    footer=False, layout="padding:128px; display:flex; flex-direction:row; align-items:center; gap:64px")
SECTIONS["s0"] = {"description": "The problem, the playground in one line, and how the deck is organised", "start": "cover"}

ch = [("Pilots everywhere, platform nowhere", "Teams try tools one by one. Nothing is shared, reused or supported."),
      ("Spend nobody can trace", "Keys on personal cards and invoices by provider, with no view by person, team or outcome."),
      ("Agents nobody can audit", "No record of which model saw which data, or who approved the answer."),
      ("Locked into one vendor", "Each tool chooses the model, the cloud and the price for you.")]
section("challenge", header("The challenge", "Where enterprise AI stalls") +
        f'<div style="display:grid; grid-template-columns:repeat(2, 1fr); gap:32px">' +
        "".join(card(f'<h3 style="font-size:40px; font-weight:600; line-height:1.15; color:{INK}">{t}</h3><p style="font-size:28px; line-height:1.4; color:{BODY}">{d}</p>') for t, d in ch) + '</div>', bg=ALT)

pr = [("Trust", VIOLET, "Governed", "Identity, role policy and budget are checked before every call, with one ledger row after it."),
      ("Lightning", PINK, "Agentic", "Agents are explicit steps. Code does what can be computed and people decide the exceptions."),
      ("Globe", CYAN, "Open", "30 models, 11 providers, any SDK, 7,500 integrations and four cloud runtimes."),
      ("Chart", EMERALD, "Measured", "Golden cases are graded nightly. Drift demotes an agent and rolls it back.")]
section("promise", header("The playground", "One governed place for all enterprise AI"),
        extra=pinned_tiles(330, 500, [f'{icon(i, c)}<h3 style="font-size:40px; font-weight:600; color:{INK}">{t}</h3><p style="font-size:28px; line-height:1.4; color:{BODY}">{d}</p>' for i, c, t, d in pr])
        + beam_embed(128, 330, 1664, 500, 4, 32))

p1 = ["Discover", "Build", "Ready-made agents", "Using the pieces together", "Take it anywhere", "Evaluate", "Dashboards", "Benefits"]
p2 = ["Architecture", "Technology stack", "Governance", "Agent runs", "Inside an agent", "Self-running operations", "Security", "Deployment"]
def part_card(n, title, items, color):
    lis = "".join(f'<li>{x}</li>' for x in items)
    return card(f'<div style="width:100%; height:6px; border-radius:3px; background:{color}"></div>'
                f'<p style="font-size:24px; font-weight:600; letter-spacing:3px; color:{color}">PART {n}</p>'
                f'<h3 style="font-size:40px; font-weight:600; line-height:1.15; color:{INK}">{title}</h3>'
                f'<ul style="font-size:28px; line-height:1.5; color:{BODY}">{lis}</ul>', gap=16)
section("agenda", header("Contents", "What it offers, and how it is built") +
        f'<div style="display:flex; gap:32px">{part_card(1, "What the platform offers", p1, VIOLET)}{part_card(2, "How the platform is built", p2, CYAN)}</div>')

# =============================== PART 1 ===============================
divider("part1", "Part 1", "What the platform offers",
        "What people can discover and build, how each piece is used on its own and with the others, and the dashboards that show the results.",
        ["Discover", "Build", "Use together", "Take anywhere", "Evaluate", "Dashboards"], "01")
SECTIONS["s1"] = {"description": "Part 1. What the platform offers: discover, build, use together, evaluate, dashboards", "start": "part1"}
PART["label"] = "Part 1 · What the platform offers"

areas = [("Home", "see where you stand", VIOLET, ["Console", "Documentation"]),
         ("Discover", "find what exists", VIOLET, ["Models", "Blueprints", "Frameworks", "Low-code studios", "Cloud platforms", "MCP Marketplace", "Popular Git repos", "Skills"]),
         ("Build", "make and run", PINK, ["Playground", "Agent Hub", "Notebooks", "Knowledge", "Datasets"]),
         ("Evaluate", "prove quality", CYAN, ["Evals", "Canary"]),
         ("Operate", "run and measure", CYAN, ["Runs", "Traces", "Cost", "Adoption"]),
         ("Community", "share and learn", EMERALD, ["Showcase", "Challenges", "Leaderboard"]),
         ("Admin", "set the rules", EMERALD, ["Users", "Policies", "Budgets", "Settings"])]
rows = ""
for name, sub, col, pages in areas:
    pills = "".join(pill(p, INK, CARD, 24, "8px 20px") for p in pages)
    rows += (f'<div style="display:flex; gap:24px; align-items:center">'
             f'<div style="width:260px; display:flex; flex-direction:column; gap:2px"><p style="font-size:28px; font-weight:600; color:{col}">{name}</p>'
             f'<p style="font-size:24px; color:{MUTED}">{sub}</p></div>'
             f'<div style="flex:1; display:flex; gap:12px; flex-wrap:wrap">{pills}</div></div>')
section("map", header("At a glance", "Twenty-eight pages in seven areas") + f'<div style="display:flex; flex-direction:column; gap:14px">{rows}</div>',
        layout="padding:128px 128px 160px; display:flex; flex-direction:column; gap:40px")

roles = [("Search", "Explorers", "Try every model safely, compare answers and learn by doing."),
         ("Wrench", "Builders", "Build agents, notebooks and knowledge, then take them to any SDK."),
         ("Users", "Champions", "Lead a department: adoption, showcases, challenges and results."),
         ("Settings", "Administrators", "Set policy, budgets and keys, approve integrations and see all spend.")]
section("roles", header("Who it serves", "Built for every role") +
        f'<div style="display:flex; gap:32px">' + "".join(card(f'{icon(i)}<h3 style="font-size:32px; font-weight:600; color:{INK}">{t}</h3><p style="font-size:28px; line-height:1.4; color:{BODY}">{d}</p>', gap=20) for i, t, d in roles) + '</div>'
        f'<div style="display:flex; align-items:center; gap:24px; background:{CARD}; border:1px solid {BORDER}; border-radius:24px; padding:28px 40px">'
        f'{icon("Key", VIOLET, 44)}<p style="font-size:28px; color:{BODY}">Sign in with <b>Microsoft Entra ID</b>, <b>Google Workspace</b>, <b>Okta</b> or any <b>OpenID Connect</b> provider.</p></div>')

d1 = [("Chat", "Models", "30 · 11 providers", "Prices, context, capabilities and tiers on one sheet, greyed until a key or policy allows them.", "Try one in the Playground, compare four, pin one to an agent or let Smart routing choose."),
      ("Book", "Blueprints", "175 · six families", "Ready agent designs, Gen AI or Agentic AI, each with its steps, tools and review gates.", "Run one on mock data, open it as a notebook, or export it to a framework or low-code tool."),
      ("Code", "Frameworks", "5 SDKs", "Any blueprint as an OpenAI Agents SDK, LangGraph, CrewAI, Agent Framework or ADK project.", "Download it, run its smoke test, or run it live in a sandbox through the governed gateway."),
      ("Link", "Low-code studios", "3 studios", "Importable Langflow flows, n8n workflows and Copilot Studio recipes for any blueprint.", "Give business builders the same agent inside the tool they already use.")]
section("discover", header("Discover", "Discover: models, blueprints, projects") +
        f'<div style="display:grid; grid-template-columns:repeat(2, 1fr); gap:24px">' + "".join(asset_card(*x) for x in d1) + '</div>')

d2 = [("Cloud", "Cloud platforms", "4 runtimes", "Microsoft Foundry, AWS AgentCore, Google Agent Runtime and Anthropic Managed Agents.", "Sign in from the CLI and follow a deploy guide written for your framework and model."),
      ("Globe", "MCP Marketplace", "7,500 servers", "Servers from the official MCP registry, with ready configuration for seven clients.", "Once an administrator approves one, attach it to agents or use it from Claude, Cursor or VS Code."),
      ("Star", "Popular Git repos", "60 repositories", "The frameworks, harnesses and reference implementations behind the playground, with licences.", "Study working code and start from a proven pattern instead of a blank page."),
      ("Tool", "Skills", "338 packs", "SKILL.md packs for testing, security, data, documents and more.", "Attach them to any agent in the wizard to give it a specialist's playbook.")]
section("discover2", header("Discover", "Discover: integrations and clouds") +
        f'<div style="display:grid; grid-template-columns:repeat(2, 1fr); gap:24px">' + "".join(asset_card(*x) for x in d2) + '</div>')

def captioned(key, w, h, alt, cap):
    return f'<div style="display:flex; flex-direction:column; gap:16px">{shot(key, w, h, alt)}<p style="font-size:24px; color:{MUTED}">{cap}</p></div>'
section("screens", header("Discover", "Discover, in the product") +
        f'<div style="display:flex; gap:104px">'
        + captioned("models", 780, 545, "Models page filtered to available models, with price, context and capabilities", "<b>Models</b>: one price sheet, filtered to what you may use")
        + captioned("connectors", 780, 545, "MCP Marketplace with approved servers and ready configuration", "<b>MCP Marketplace</b>: approved servers, ready to connect")
        + '</div>')

bld = [("Chat", "Playground", "Chat with any allowed model, compare four side by side and copy the request as code."),
       ("Play", "Agent Hub", "Run the ready agents with review gates, or build your own with knowledge, skills and tools."),
       ("Code", "Notebooks", "Open any blueprint or run as a notebook, in the browser or a sandbox with GPU options."),
       ("Book", "Knowledge", "Turn documents, pages and repositories into Knowledge Spaces with cited answers."),
       ("Database", "Datasets", "Eight mock datasets with schemas and downloads, plus trusted public sources with loaders.")]
bc = "".join(card(f'<div style="display:flex; gap:14px; align-items:center">{icon(i, VIOLET, 40)}<h3 style="font-size:30px; font-weight:600; color:{INK}">{t}</h3></div>'
                  f'<p style="font-size:24px; line-height:1.4; color:{BODY}">{d}</p>', pad=32, gap=14) for i, t, d in bld)
section("build", header("Build", "Build: five workbenches") +
        f'<div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:24px">{bc}'
        f'<div style="display:flex; align-items:center; justify-content:center">{shot("agents", 460, 321, "Agent Hub with runnable blueprints, step counts and human gates")}</div></div>')

ag = [("Document reconciliation", "Load → extract → validate → quality gate → summary", "Decides every invoice that fails validation"),
      ("Sage Lens deep research", "Clarity gate → research → validate coverage → synthesise with sources", "Clarifies a vague question"),
      ("Learning path generator", "Generate → critic review → curate vetted references → assemble", "Reviews the published path"),
      ("Review panel", "Five critics: legal, consistency, completeness, policy and tone", "Gives the verdict: revise or publish"),
      ("Data analyst", "Load the file → route the question → compute in code → narrate", "Not needed: every number comes from code"),
      ("Knowledge Q&amp;A", "Retrieve passages → answer with citations → verify each citation", "Sees any answer without valid citations")]
section("agents", header("Ready-made agents", "Six agents ready on day one") +
        f'<div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:24px">' + "".join(card(
            f'<h3 style="font-size:30px; font-weight:600; line-height:1.2; color:{INK}">{t}</h3>'
            f'<p style="font-size:24px; line-height:1.4; color:{BODY}">{s}</p>'
            f'<p style="font-size:24px; line-height:1.4; color:{PINK}"><b>Person:</b> <span style="color:{BODY}">{p}</span></p>', pad=32, gap=12) for t, s, p in ag) + '</div>')

section("journeys", header("Use together", "Using the pieces together") +
        f'<img src="{A["journeys"]}" alt="Five journeys: choose the right model; blueprint to production; agent on your own data; bring your own code; prove the value" style="width:1600px; height:600px; object-fit:contain">')

aw = [("Code", "Any SDK", "An OpenAI-compatible gateway governs and meters calls from existing code."),
      ("Book", "Five frameworks", "OpenAI Agents SDK, LangGraph, CrewAI, Microsoft Agent Framework and Google ADK."),
      ("Link", "Low-code", "Langflow flows, n8n workflows and Copilot Studio recipes."),
      ("Cloud", "Four clouds", "Microsoft Foundry, AWS AgentCore, Google Agent Runtime and Anthropic Managed Agents.")]
code = (f'<div style="background:#14122B; border-radius:20px; padding:32px 40px; display:flex; flex-direction:column; gap:8px">'
        f'<p style="font-family:{MONO}; font-size:26px; color:#C4B5FD">client = OpenAI(base_url=PLAYGROUND_URL, api_key=PERSONAL_TOKEN)</p>'
        f'<p style="font-family:{MONO}; font-size:26px; color:#E5E7EB">client.chat.completions.create(model=<span style="color:#F9A8D4">"smart"</span>, messages=[...])</p></div>')
section("anywhere", header("Take it anywhere", "Take any agent anywhere") +
        f'<div style="display:flex; gap:24px">' + "".join(card(f'{icon(i, VIOLET, 48)}<h3 style="font-size:32px; font-weight:600; color:{INK}">{t}</h3><p style="font-size:24px; line-height:1.4; color:{BODY}">{d}</p>', pad=32, gap=16) for i, t, d in aw) + f'</div>{code}',
        layout="padding:128px 128px 160px; display:flex; flex-direction:column; gap:40px")

lv = [("Draft", "Runs on mock data"), ("Golden", "Five golden cases and one evaluation"), ("Gated", "The latest evaluation clears the gate"),
      ("Canaried", "Three nightly canaries pass without drift"), ("Production", "Promoted by an administrator, with rollback")]
lvc = "".join(card(f'<p style="font-size:24px; font-weight:600; color:{VIOLET}">Level {i}</p><h3 style="font-size:32px; font-weight:600; color:{INK}">{n}</h3>'
                   f'<p style="font-size:24px; line-height:1.35; color:{BODY}">{d}</p>', pad=28, gap=8, bg="#F5F3FF" if i == 4 else CARD) for i, (n, d) in enumerate(lv))
section("quality", header("Evaluate", "Quality that is measured, not assumed") +
        f'<div style="display:flex; gap:20px">{lvc}</div>'
        f'<div style="display:flex; gap:48px; align-items:center">{shot("canary", 452, 316, "Canary: nightly reruns with pass rate and cost per case over time, and drift events")}'
        f'<div style="flex:1; display:flex; flex-direction:column; gap:20px">'
        + item("A judge model scores rubrics", "Deterministic checks first, then weighted criteria graded by an economy model.")
        + item("Gates hold the line", "Pass rate, cost per case and p95 latency must clear before promotion.") + '</div></div>',
        layout="padding:128px 128px 160px; display:flex; flex-direction:column; gap:36px")

section("console", header("Dashboards", "Dashboards: the console") +
        f'<div style="display:flex; gap:64px; align-items:center">{shot("console", 960, 600, "The console: credits, spend, tokens and hours by feature, with the governed gateway")}'
        f'<div style="flex:1; display:flex; flex-direction:column; gap:40px">'
        + item("Live from the ledger", "Credits, spend and tokens update within a second of every call.", 28)
        + item("Hours by feature", "Time in chat, agents and notebooks, per person and department.", 28)
        + item("One governed door", "Models, frameworks, clouds and connectors all start here.", 28) + '</div></div>')

def split(key, alt, items, w=820, h=573):
    return (f'<div style="display:flex; gap:64px; align-items:center">{shot(key, w, h, alt)}'
            f'<div style="flex:1; display:flex; flex-direction:column; gap:28px">' + "".join(item(t, d) for t, d in items) + '</div></div>')
section("cost", header("Dashboards", "Dashboards: cost to the ledger row") + split("cost", "Cost: spend by day and by department, reconciled to the ledger, with CSV export", [
    ("Drill down", "Organisation, department, person, feature, model, then the single call."),
    ("Savings recorded", "Smart routing logs each saving against a premium baseline."),
    ("Caps and alerts", "Alerts at 50, 80 and 100 percent per person, department and organisation."),
    ("Export and traces", "Any view or raw ledger rows as CSV, and every run as a step-by-step trace.")]))
section("adoption", header("Dashboards", "Dashboards: adoption and value") + split("adoption", "Adoption: hours per feature, outcomes, cost per outcome and an ROI matrix by department", [
    ("Hours by feature", "From ledger sessions, per person and department, with a weekly digest."),
    ("Cost per outcome", "Spend per completed run, answered conversation and comparison."),
    ("Return by department", "Hours saved and value, with every assumption shown and editable."),
    ("Community", "Showcase, rubric-judged challenges and a leaderboard earned from the ledger.")]))

nums = [("30", "models"), ("11", "providers"), ("175", "blueprints"), ("7,500", "MCP servers"), ("5", "agent frameworks"), ("4", "cloud runtimes")]
line_embed = ('<x-embed style="position:absolute; left:128px; top:888px; width:1664px; height:24px"><style>html,body{margin:0;background:transparent;overflow:hidden}'
              '.b{animation:m 6s linear infinite}@keyframes m{from{transform:translateX(-300px)}to{transform:translateX(1664px)}}'
              '@media (prefers-reduced-motion: reduce){.b{animation:none;opacity:0}}</style>'
              '<svg width="1664" height="24" viewBox="0 0 1664 24"><defs><linearGradient id="t" x1="0" x2="1"><stop offset="0" stop-color="#C4B5FD" stop-opacity="0"/>'
              '<stop offset=".7" stop-color="#F0ABFC"/><stop offset="1" stop-color="#FFFFFF"/></linearGradient><filter id="f"><feGaussianBlur stdDeviation="3"/></filter></defs>'
              '<rect x="0" y="11" width="1664" height="2" fill="#6D28D9"/><g class="b"><rect x="0" y="9" width="300" height="6" rx="3" fill="url(#t)" filter="url(#f)"/>'
              '<rect x="0" y="11" width="300" height="2" fill="url(#t)"/><circle cx="298" cy="12" r="5" fill="#FFFFFF"/></g></svg></x-embed>\n')
section("numbers", header("Choice without lock-in", "Everything in one catalogue", dark=True) +
        f'<div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:48px">' +
        "".join(f'<div style="display:flex; flex-direction:column; gap:8px"><p style="font-size:120px; font-weight:700; line-height:1; letter-spacing:-2px; color:#FFFFFF">{n}</p><p style="font-size:28px; color:#DDD6FE">{l}</p></div>' for n, l in nums) + '</div>',
        bg=DEEP, extra=line_embed, transition="push")

bf = [("Chart", VIOLET, "Business leaders", "Adoption you can see: hours, outcomes and value by department."),
      ("Lock", PINK, "IT and security", "One governed door for identity, policy, keys and approved integrations."),
      ("Database", CYAN, "Finance", "Every dollar attributed to a person, feature and outcome, with caps that hold."),
      ("Tool", EMERALD, "Builders", "Working agents in days, portable to any SDK, framework or cloud.")]
section("benefits", header("Benefits", "What each stakeholder gets"), bg=ALT,
        extra=pinned_tiles(330, 520, [f'{icon(i, c)}<h3 style="font-size:40px; font-weight:600; line-height:1.15; color:{INK}">{t}</h3><p style="font-size:28px; line-height:1.4; color:{BODY}">{d}</p>' for i, c, t, d in bf])
        + beam_embed(128, 330, 1664, 520, 4, 32))

# =============================== PART 2 ===============================
PART["label"] = ""
divider("part2", "Part 2", "How the platform is built",
        "The layers every request passes, the technology underneath, how agents run and pause for people, and how it is secured and deployed.",
        ["Architecture", "Stack", "Governance", "Agent runs", "Security", "Deployment"], "02")
SECTIONS["s2"] = {"description": "Part 2. How the platform is built: architecture, stack, governance, agents, security, deployment", "start": "part2"}
PART["label"] = "Part 2 · How the platform is built"

section("layers", header("Architecture", "How a request travels") +
        f'<img src="{A["layers"]}" alt="Six layers a request passes in order: people and clients, governance, reasoning, knowledge and data, integrations, ledger" style="width:1340px; height:603px; object-fit:contain; align-self:center">')

stack = [("Experience", "Next.js and React; Auth.js sign-in through Entra ID, Google, Okta or OpenID Connect"),
         ("Gateway and API", "FastAPI service with an OpenAI-compatible gateway; LiteLLM reaches 11 model providers"),
         ("Agent runtime", "LangGraph graphs with a persisted checkpointer, so a run can wait for a person and resume"),
         ("Knowledge", "Chunking, embeddings and hybrid retrieval, with every citation verified"),
         ("Data", "PostgreSQL for runs, evaluations, knowledge, budgets and the usage ledger"),
         ("Sandboxes", "Isolated sessions for notebooks and framework projects, with network egress disabled"),
         ("Platform", "Azure Container Apps, Container Registry and Key Vault, defined as code in Bicep"),
         ("Delivery", "GitHub Actions: lint, tests, end-to-end checks, secret scanning, dependency audit"),
         ("Integrations", "The playground is itself an MCP server for Claude, Cursor and other clients")]
trs = f'<tr style="background:#F1EFFA"><th style="width:24%; padding:12px 24px; font-weight:600">Layer</th><th style="width:76%; padding:12px 24px; font-weight:600">Built with</th></tr>'
for i, (c, h) in enumerate(stack):
    trs += f'<tr style="background:{"#FFFFFF" if i % 2 == 0 else "#FAF9FE"}"><td style="padding:12px 24px; font-weight:600">{c}</td><td style="padding:12px 24px; color:{BODY}">{h}</td></tr>'
section("stack", header("Technology", "The technology stack") + f'<table style="width:1664px; font-size:24px; color:{INK}; border:1px solid {BORDER}; border-radius:16px">{trs}</table>')

checks = [("1", "Identity.", "Who is asking, from your identity provider."),
          ("2", "Role policy.", "Which models, tools and connectors this role may use."),
          ("3", "Budget.", "Caps per person, department and organisation stop a call before it costs."),
          ("4", "Key.", "The platform key or the person's own, encrypted."),
          ("✓", "Ledger.", "One row per call: who, feature, model, tokens, cost, latency, key and trace.")]
rows = "".join(f'<div style="display:flex; gap:24px; align-items:flex-start">'
               f'<p style="font-size:28px; font-weight:700; color:#FFFFFF; background:{EMERALD if n == "✓" else VIOLET}; width:56px; height:56px; border-radius:28px; text-align:center; line-height:2">{n}</p>'
               f'<p style="flex:1; font-size:28px; line-height:1.4; color:{BODY}"><b>{t}</b> {d}</p></div>' for n, t, d in checks)
section("governance", header("Governance", "Four checks before every call") +
        f'<div style="display:flex; gap:64px; align-items:center"><div style="flex:1; display:flex; flex-direction:column; gap:28px">{rows}</div>'
        f'{shot("policies", 820, 471, "Policies: allowed model tiers, providers, output ceiling and Smart routing per role")}</div>')

section("run", header("Agent runs", "One agent run, start to finish") +
        f'<img src="{A["run"]}" alt="Eight steps: ask, govern, route, reason, review, answer, improve, share; the run pauses at the human gate until a reviewer approves" style="width:1600px; height:600px; object-fit:contain">')

section("inside", header("Behind the scenes", "Inside an agent") +
        f'<img src="{A["agent"]}" alt="Document reconciliation: three code steps, a quality gate, a human decision on exceptions and one model step that writes the summary" style="width:1440px; height:504px; object-fit:contain">'
        f'<p style="font-size:28px; line-height:1.4; color:{BODY}; width:1500px">Code loads, extracts and validates. A rule sends exceptions to a person. The model is used once, for the summary. That split keeps cost, speed and behaviour predictable.</p>',
        layout="padding:128px 128px 160px; display:flex; flex-direction:column; gap:24px")

pa = [("Activity", "Key health check", "Probes every platform key and raises an alert when a provider rejects one."),
      ("Warning", "Cost sentinel", "Compares yesterday's spend with the trailing week and explains any jump."),
      ("Verified", "Connector reviewer", "Shortlists new MCP servers and recommends approve, hold or block."),
      ("GraduationCap", "Onboarding coach", "Reads what a person has used and suggests their next three steps."),
      ("Chart", "Adoption digest", "Turns the analytics into a short weekly summary with recommendations."),
      ("Star", "Showcase writer", "Drafts a showcase post from a run, for a person to edit and publish.")]
section("platform", header("Self-running", "Built to run itself") +
        f'<div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:24px">' + "".join(card(
            f'<div style="display:flex; gap:16px; align-items:center">{icon(i, VIOLET, 40)}<h3 style="font-size:30px; font-weight:600; color:{INK}">{t}</h3></div>'
            f'<p style="font-size:24px; line-height:1.4; color:{BODY}">{d}</p>', pad=32, gap=16) for i, t, d in pa) + '</div>'
        f'<p style="font-size:28px; line-height:1.4; color:{BODY}">These platform agents use the same runtime, governance and traces as every business agent.</p>',
        layout="padding:128px 128px 160px; display:flex; flex-direction:column; gap:40px")

sec = [("Sign-in", "Microsoft Entra ID, Google Workspace, Okta or any OpenID Connect provider, with allow-lists"),
       ("Sessions", "Signed and stateless; signing out invalidates every earlier session"),
       ("API exposure", "Reachable only from the web tier, with an internal key and identity headers"),
       ("Keys", "Platform keys in Key Vault; personal keys encrypted; every call records the key"),
       ("Untrusted code", "Notebooks and framework projects run in isolated sandboxes without egress"),
       ("Data", "One region; calls reach only enabled providers; MCP servers only after approval"),
       ("Change control", "Every release passes tests, end-to-end checks, secret scanning and dependency audit")]
trs = f'<tr style="background:#F1EFFA"><th style="width:24%; padding:18px 24px; font-weight:600">Concern</th><th style="width:76%; padding:18px 24px; font-weight:600">How it is handled</th></tr>'
for i, (c, h) in enumerate(sec):
    trs += f'<tr style="background:{"#FFFFFF" if i % 2 == 0 else "#FAF9FE"}"><td style="padding:18px 24px; font-weight:600">{c}</td><td style="padding:18px 24px; color:{BODY}">{h}</td></tr>'
section("security", header("Security", "Security and identity") + f'<table style="width:1664px; font-size:24px; color:{INK}; border:1px solid {BORDER}; border-radius:16px">{trs}</table>')

dp = [("One command", "Provisions registry, database, key vault, sandboxes and both apps on Azure."),
      ("Any platform", "The same container images run on any container platform."),
      ("Safe releases", "Each release is a new revision; the previous one stays for rollback."),
      ("90–150 USD", "A month at pilot sizing, plus model usage shown per person.")]
idp = "".join(pill(x, INK, CARD) for x in ("Microsoft Entra ID", "Google Workspace", "Okta", "Any OpenID Connect"))
section("deploy", header("Deployment", "Runs in your cloud, under your identity") +
        f'<div style="display:flex; gap:32px">' + "".join(card(f'<h3 style="font-size:40px; font-weight:600; line-height:1.15; color:{VIOLET}">{t}</h3><p style="font-size:28px; line-height:1.4; color:{BODY}">{d}</p>', gap=16) for t, d in dp) + '</div>'
        f'<div style="display:flex; gap:16px; align-items:center; flex-wrap:wrap"><p style="font-size:28px; font-weight:600; color:{INK}">Sign-in</p>{idp}</div>')

# =============================== CLOSE ===============================
PART["label"] = ""
st = [("01", "Deploy", "The playground in your own cloud tenant, from one command."),
      ("02", "Connect", "Your identity provider, allowed domains and administrators."),
      ("03", "Configure", "Policies per role, budgets per department and platform keys."),
      ("04", "Adopt", "Run the ready agents, build your own and review adoption weekly.")]
section("start", header("Getting started", "From pilot to production in four steps") +
        f'<div style="display:flex; gap:32px">' + "".join(card(
            f'<p style="font-size:64px; font-weight:700; line-height:1; background:{GRAD}; background-clip:text; -webkit-text-fill-color:transparent; color:{VIOLET}">{n}</p>'
            f'<h3 style="font-size:40px; font-weight:600; color:{INK}">{t}</h3><p style="font-size:28px; line-height:1.4; color:{BODY}">{d}</p>', gap=20) for n, t, d in st) + '</div>')
SECTIONS["s3"] = {"description": "How to start, and contact", "start": "start"}

section("close", (
    f'{MARK.format(s=120, k="e")}'
    f'<h2 style="font-size:88px; font-weight:700; line-height:1.05; letter-spacing:-2px; color:{INK}; text-align:center">Enterprise AI <span style="color:{VIOLET}">Playground</span></h2>'
    f'<p style="font-size:40px; line-height:1.3; color:{BODY}; text-align:center">Govern every call. Build every agent. See every dollar.</p>'
    f'<div style="width:240px; height:8px; border-radius:4px; background:{GRAD}"></div>'
    f'<p style="font-size:28px; color:{MUTED}; text-align:center">Satya Bonda · satya.bonda@gmail.com</p>'),
    footer=False, bg=ALT, layout="padding:128px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:40px")

prev = json.loads(Path(sys.argv[2]).read_text())
prev.update({"title": prev.get("title", "Enterprise AI Playground"), "cover": "cover", "order": ORDER, "sections": SECTIONS,
             "faces": {"sora": {"family": "Sora", "href": "https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&display=swap"},
                       "jetbrains-mono": {"family": "JetBrains Mono", "href": "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap"}}})
(ROOT / "project" / "deck.json").write_text(json.dumps(prev, indent=1), encoding="utf-8")
print(len(ORDER), "slides:", ", ".join(ORDER))
