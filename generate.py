#!/usr/bin/env python3
"""
Generates the animated, transparent SVG assets for the GitHub profile README.

  assets/hero-{dark,light}.svg     glitch name + bio + avatar + animated stack
  assets/contrib-{dark,light}.svg  live contribution graph (needs GH_TOKEN)
  assets/btn-*-{dark,light}.svg    LinkedIn / LeetCode / Email buttons

Run locally:   GH_TOKEN=xxx python generate.py     (or  python generate.py --demo)
Run on GitHub: .github/workflows/profile.yml does it daily.
"""
import base64
import json
import os
import random
import sys
import urllib.request
from xml.sax.saxutils import escape

from icons import ICONS

# ───────────────────────── CONFIG (edit these) ─────────────────────────
USER = "mathely27"
NAME = "Mathely"
SUBTITLE = "cs student · india"
BIO = ["i build AI agents, macOS tools,", "and full-stack web apps."]
LINKEDIN = "https://linkedin.com/in/mathely27"
LEETCODE = "https://leetcode.com/mathely27"
EMAIL = "mailto:mathely27@gmail.com"

# (big symbol, label, icon key)
STACK = [
    ("Py", "Python", "Py"), ("Ht", "HTML", "Ht"), ("Cs", "CSS", "Cs"),
    ("Jv", "Java", "Jv"), ("Js", "JavaScript", "Js"),
    ("C", "C", "C"), ("Gi", "Git", "Gi"), ("Gh", "GitHub", "Gh"),
    ("Li", "Linux", "Li"), ("Vs", "VS Code", "Vs"),
    ("Ol", "Ollama", "Ol"), ("Su", "Supabase", "Su"), ("Sq", "SQL", "Sq"),
    ("Re", "React", "Re"), ("Ve", "Vercel", "Ve"),
]
# real brand colour each tile flashes when it “lights up”
BRAND = {
    "Py": "#3776AB", "Ht": "#E34F26", "Cs": "#1572B6", "Jv": "#F89820",
    "Js": "#F7DF1E", "C":  "#A8B9CC", "Gi": "#F05032", "Gh": "#8957e5",
    "Li": "#FCC624", "Vs": "#007ACC", "Ol": "#34D399", "Su": "#3ECF8E",
    "Sq": "#336791", "Re": "#61DAFB", "Ve": "#aaaaaa",
}
# ───────────────────────────────────────────────────────────────────────

THEMES = {
    "dark": dict(fg="#ffffff", muted="#8b949e", line="#4a525b", tile_op="0.04",
                 levels=[("#ffffff", "0.07"), ("#0e4429", "1"), ("#006d32", "1"), ("#26a641", "1"), ("#39d353", "1")]),
    "light": dict(fg="#1f2328", muted="#59636e", line="#afb8c1", tile_op="0.035",
                  levels=[("#000000", "0.06"), ("#9be9a8", "1"), ("#40c463", "1"), ("#30a14e", "1"), ("#216e39", "1")]),
}
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
RED, CYAN = "#ff0000", "#00ffff"


# ───────────────────────── glitch text (SMIL, no JS) ─────────────────────────
def glitch_name(text, x, y, size, fg, seed=7, dur=6.0, steps=48):
    """Slices-mode glitch: two clipped, shifted, coloured copies that jolt in bursts."""
    rnd = random.Random(seed)
    top, span = y - size * 0.82, size * 1.08
    width = size * len(text) * 0.75

    # active windows (in steps) – calm most of the time, then a short burst
    active = set()
    for start, length in [(30, rnd.randint(4, 6)), (39, rnd.randint(2, 4))]:
        active.update(range(start, start + length))

    kt = ";".join(f"{i / steps:.4f}" for i in range(steps))

    def band():
        ys, hs, dxs = [], [], []
        for i in range(steps):
            if i in active:
                h = size * rnd.uniform(0.08, 0.28)
                ys.append(top + rnd.uniform(0, span - h))
                hs.append(h)
                dxs.append(rnd.choice([-1, 1]) * rnd.uniform(size * 0.07, size * 0.2))
            else:
                ys.append(top)
                hs.append(0)
                dxs.append(0)
        return ys, hs, dxs

    def anim(attr, vals, extra=""):
        v = ";".join(f"{a:.2f}" for a in vals)
        return (f'<animate attributeName="{attr}" values="{v}" keyTimes="{kt}" '
                f'calcMode="discrete" dur="{dur}s" repeatCount="indefinite"{extra}/>')

    style = (f'font-family="{SANS}" font-weight="800" font-size="{size}" letter-spacing="-3" '
             f'x="{x}" y="{y}"')
    out = [f'<text {style} fill="{fg}">{escape(text)}</text>']
    defs = []
    for tag, colour, sd in (("a", RED, 0), ("b", CYAN, 1)):
        ys, hs, dxs = band()
        defs.append(
            f'<clipPath id="clip-{tag}"><rect x="{x - 40}" width="{width + 80}" y="{top:.2f}" height="0">'
            f'{anim("y", ys)}{anim("height", hs)}</rect></clipPath>')
        tx = ";".join(f"{d:.2f} 0" for d in dxs)
        out.append(
            f'<g clip-path="url(#clip-{tag})"><g>'
            f'<animateTransform attributeName="transform" type="translate" values="{tx}" keyTimes="{kt}" '
            f'calcMode="discrete" dur="{dur}s" repeatCount="indefinite"/>'
            f'<text {style} fill="{colour}">{escape(text)}</text></g></g>')
    return "".join(defs), "".join(out)


# ───────────────────────── avatar ─────────────────────────
def avatar_data_uri():
    try:
        req = urllib.request.Request(f"https://github.com/{USER}.png?size=240",
                                     headers={"User-Agent": "profile-readme"})
        data = urllib.request.urlopen(req, timeout=20).read()
        return "data:image/png;base64," + base64.b64encode(data).decode()
    except Exception as e:  # offline / demo
        print("avatar fetch failed:", e, file=sys.stderr)
        return None


# ───────────────────────── hero ─────────────────────────
def hero(theme, avatar):
    t = THEMES[theme]
    W, H = 900, 470
    defs, name_svg = glitch_name(NAME, 38, 205, 84, t["fg"])

    # avatar (top right, circled)
    cx, cy, r = 826, 68, 50
    if avatar:
        av = f'<image href="{avatar}" x="{cx - r}" y="{cy - r}" width="{2 * r}" height="{2 * r}" clip-path="url(#av)" preserveAspectRatio="xMidYMid slice"/>'
    else:
        av = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{t["fg"]}" fill-opacity="0.08"/>'
    avatar_svg = (f'<clipPath id="av"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>{av}'
                  f'<circle cx="{cx}" cy="{cy}" r="{r + 4}" fill="none" stroke="{t["line"]}" stroke-width="1.5"/>')

    # stack grid
    tw, gap, cols = 80, 8, 5
    gx, gy = 446, 188
    rnd = random.Random(42)
    tiles = []
    for i, (sym, label, key) in enumerate(STACK):
        col, row = i % cols, i // cols
        x, y = gx + col * (tw + gap), gy + row * (tw + gap)
        d = rnd.uniform(8, 15)          # each tile has independent period
        delay = -rnd.uniform(0, d)
        brand = BRAND.get(key, t["fg"])
        anim = f'style="animation-duration:{d:.1f}s;animation-delay:{delay:.1f}s"'

        # glowing border & background overlay on activation
        glow = (f'<rect class="glow" {anim} fill="{brand}" fill-opacity="0.14" '
                f'stroke="{brand}" stroke-width="1.5" '
                f'x="{x}" y="{y}" width="{tw}" height="{tw}" rx="14"/>')

        # 32x32 brand icon centered in tile (replaces 24x24 simple-icon scaled 1.333)
        # Position transform is on outer <g> so CSS opacity animation NEVER moves it
        ix = x + (tw - 32) / 2
        iy = y + 25
        icon = (f'<g transform="translate({ix:.1f},{iy:.1f}) scale(1.333)">'
                f'<path class="ico" {anim} d="{ICONS[key]}" fill="{brand}"/>'
                f'</g>')

        tiles.append(
            f'<rect x="{x}" y="{y}" width="{tw}" height="{tw}" rx="14" fill="{t["fg"]}" fill-opacity="{t["tile_op"]}" '
            f'stroke="{t["line"]}" stroke-width="1.5"/>'
            f'{glow}'
            f'<text x="{x + 10}" y="{y + 18}" font-family="{MONO}" font-size="11" fill="{t["muted"]}">{i + 1}</text>'
            f'<text class="sym" {anim} x="{x + tw / 2}" y="{y + 49}" text-anchor="middle" font-family="{MONO}" '
            f'font-weight="700" font-size="30" fill="{t["fg"]}">{sym}</text>'
            f'{icon}'
            f'<text x="{x + tw / 2}" y="{y + 69}" text-anchor="middle" font-family="{SANS}" font-size="11.5" fill="{t["muted"]}">{escape(label)}</text>')

    css = f"""
@keyframes sym {{
  0%, 82% {{ opacity: 1; }}
  85%, 96% {{ opacity: 0; }}
  99%, 100% {{ opacity: 1; }}
}}
@keyframes ico {{
  0%, 82% {{ opacity: 0; }}
  85%, 96% {{ opacity: 1; }}
  99%, 100% {{ opacity: 0; }}
}}
@keyframes glow {{
  0%, 82% {{ opacity: 0; }}
  85%, 96% {{ opacity: 1; }}
  99%, 100% {{ opacity: 0; }}
}}
.sym, .ico, .glow {{
  animation-iteration-count: infinite;
  animation-timing-function: ease-in-out;
}}
.sym {{ animation-name: sym; opacity: 1; }}
.ico {{ animation-name: ico; opacity: 0; }}
.glow {{ animation-name: glow; opacity: 0; }}
@media (prefers-reduced-motion: reduce) {{
  .sym, .ico, .glow {{ animation: none; }}
  .sym {{ opacity: 1; }}
  .ico, .glow {{ opacity: 0; }}
}}
"""
    body = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>{css}</style><defs>{defs}</defs>
{name_svg}
<text x="44" y="252" font-family="{SANS}" font-size="17.5" fill="{t['fg']}">{escape(SUBTITLE)}</text>
<text x="44" y="298" font-family="{SANS}" font-size="16.5" fill="{t['muted']}">{escape(BIO[0])}</text>
<text x="44" y="324" font-family="{SANS}" font-size="16.5" fill="{t['muted']}">{escape(BIO[1])}</text>
<line x1="426" y1="150" x2="426" y2="446" stroke="{t['line']}" stroke-width="1.5"/>
{avatar_svg}
<text x="{gx}" y="172" font-family="{MONO}" font-size="13" letter-spacing="5" fill="{t['muted']}">STACK</text>
{''.join(tiles)}
</svg>"""
    return body


# ───────────────────────── contributions ─────────────────────────
def fetch_calendar():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if "--demo" in sys.argv or not token:
        print("demo data (no token)", file=sys.stderr)
        rnd = random.Random(3)
        weeks, total = [], 0
        for w in range(53):
            days = []
            for d in range(7):
                lvl = rnd.choice([0, 0, 0, 1, 1, 2, 3, 4])
                total += lvl * 2
                days.append(dict(level=lvl, count=lvl * 2, date=f"2025-{(w // 5) % 12 + 1:02d}-01", weekday=d))
            weeks.append(days)
        return total, weeks
    q = """query($l:String!){user(login:$l){contributionsCollection{contributionCalendar{totalContributions
      weeks{contributionDays{contributionCount contributionLevel date weekday}}}}}}"""
    req = urllib.request.Request("https://api.github.com/graphql",
                                 data=json.dumps({"query": q, "variables": {"l": USER}}).encode(),
                                 headers={"Authorization": f"Bearer {token}", "User-Agent": "profile-readme"})
    cal = json.load(urllib.request.urlopen(req, timeout=30))["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    lv = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
    weeks = [[dict(level=lv[d["contributionLevel"]], count=d["contributionCount"], date=d["date"], weekday=d["weekday"])
              for d in w["contributionDays"]] for w in cal["weeks"]]
    return cal["totalContributions"], weeks


def contrib(theme, total, weeks):
    t = THEMES[theme]
    cell, gap, left, top = 11, 3, 44, 56
    step = cell + gap
    W, H = left + len(weeks) * step + 20, top + 7 * step + 26
    months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    parts, last_m = [], None
    for wi, days in enumerate(weeks):
        m = int(days[0]["date"][5:7]) - 1
        if m != last_m and wi < len(weeks) - 2:
            parts.append(f'<text x="{left + wi * step}" y="{top - 10}" font-family="{MONO}" font-size="11" fill="{t["muted"]}">{months[m]}</text>')
            last_m = m
        for d in days:
            col, op = t["levels"][d["level"]]
            parts.append(f'<rect class="c" style="animation-delay:{wi * 0.015:.3f}s" x="{left + wi * step}" y="{top + d["weekday"] * step}" '
                         f'width="{cell}" height="{cell}" rx="2.5" fill="{col}" fill-opacity="{op}"/>')
    for row, lab in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(f'<text x="0" y="{top + row * step + 10}" font-family="{MONO}" font-size="11" fill="{t["muted"]}">{lab}</text>')
    # legend
    lx = W - 20 - 5 * step - 80
    leg = f'<text x="{lx}" y="22" font-family="{MONO}" font-size="11" fill="{t["muted"]}">Less</text>'
    for i, (col, op) in enumerate(t["levels"]):
        leg += f'<rect x="{lx + 34 + i * step}" y="12" width="{cell}" height="{cell}" rx="2.5" fill="{col}" fill-opacity="{op}"/>'
    leg += f'<text x="{lx + 34 + 5 * step + 4}" y="22" font-family="{MONO}" font-size="11" fill="{t["muted"]}">More</text>'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>.c{{animation:pop .6s ease-out both}}@keyframes pop{{from{{opacity:0}}to{{opacity:1}}}}
@media (prefers-reduced-motion:reduce){{.c{{animation:none}}}}</style>
<text x="0" y="22" font-family="{MONO}" font-size="17" fill="{t['fg']}">{total:,} contributions in the last year</text>
{leg}{''.join(parts)}</svg>"""


# ───────────────────────── buttons ─────────────────────────
def button(theme, label, key):
    t = THEMES[theme]
    W, H = 190, 52
    if key == "mail":
        icon = (f'<g transform="translate(24,15)" fill="none" stroke="{t["muted"]}" stroke-width="1.8" stroke-linejoin="round">'
                f'<rect x="0" y="2" width="22" height="16" rx="3"/><path d="M1 4l10 8 10-8"/></g>')
    else:
        icon = f'<g transform="translate(24,14)"><path transform="scale(1.0)" d="{ICONS[key]}" fill="{t["muted"]}"/></g>'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="{(H - 3) / 2}" fill="none" stroke="{t['line']}" stroke-width="1.5"/>
{icon}<text x="62" y="31.5" font-family="{MONO}" font-size="16" fill="{t['muted']}">{label}</text></svg>"""


# ───────────────────────── main ─────────────────────────
def write(path, s):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)


if __name__ == "__main__":
    avatar = avatar_data_uri()
    total, weeks = fetch_calendar()
    for th in THEMES:
        write(f"assets/hero-{th}.svg", hero(th, avatar))
        write(f"assets/contrib-{th}.svg", contrib(th, total, weeks))
        for label, key in (("LinkedIn", "In"), ("LeetCode", "Lc"), ("Email", "mail")):
            write(f"assets/btn-{label.lower()}-{th}.svg", button(th, label, key))
    print("done")
