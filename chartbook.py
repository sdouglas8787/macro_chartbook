"""UK macro chartbook: a designed one-page readout from public series.

Pulls ONS series (no key) and, when FRED_API_KEY is set, a FRED row, and
renders a one-page HTML chartbook plus the individual PNG tiles. Every tile
carries its source, series ID and data vintage, because a chart that cannot
say where it came from is an opinion with axes.

Run:  python chartbook.py          ->  outputs/chartbook.html + outputs/*.png
"""

from __future__ import annotations

import base64
import io
import json
import os
import urllib.request
from dataclasses import dataclass
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager  # noqa: F401  (kept for system font resolution)

# ---- the palette: the portfolio site's, so public output shares one brand --
BG, INK, MUTED, LINE = "#fcfbf9", "#1c2430", "#5b6673", "#e4e0d8"
ACCENT, SECOND, THIRD = "#2a6f6a", "#b0543f", "#8a7f10"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
ONS = "https://www.ons.gov.uk"
PRICES = "economy/inflationandpriceindices/timeseries"
EARNINGS = "employmentandlabourmarket/peopleinwork/earningsandworkinghours/timeseries"
UNEMP = "employmentandlabourmarket/peoplenotinwork/unemployment/timeseries"
MONTHS = {m: i + 1 for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"])}
WINDOW_MONTHS = 60


@dataclass(frozen=True)
class OnsSeries:
    cdid: str
    path: str = PRICES


def fetch_ons(s: OnsSeries) -> dict[str, float]:
    url = f"{ONS}/{s.path}/{s.cdid.lower()}/data"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    payload = json.load(urllib.request.urlopen(req, timeout=60))
    out = {}
    for row in payload.get("months", []):
        y, m = row["date"].split()
        try:
            out[f"{int(y):04d}-{MONTHS[m.upper()[:3]]:02d}"] = float(row["value"])
        except (TypeError, ValueError, KeyError):
            continue
    return out


def fetch_fred(series_id: str, key: str) -> dict[str, float]:
    url = (f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}"
           f"&api_key={key}&file_type=json&observation_start=2019-01-01&frequency=m")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    payload = json.load(urllib.request.urlopen(req, timeout=60))
    out = {}
    for row in payload.get("observations", []):
        try:
            out[row["date"][:7]] = float(row["value"])
        except ValueError:
            continue
    return out


def yoy(levels: dict[str, float]) -> dict[str, float]:
    out = {}
    for k, v in levels.items():
        y, m = k.split("-")
        prior = f"{int(y) - 1:04d}-{m}"
        if levels.get(prior):
            out[k] = (v / levels[prior] - 1.0) * 100.0
    return out


def tail(series: dict[str, float], n: int = WINDOW_MONTHS) -> tuple[list[str], list[float]]:
    keys = sorted(series)[-n:]
    return keys, [series[k] for k in keys]


def _style(ax):
    ax.set_facecolor(BG)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(LINE)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.grid(axis="y", color=LINE, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)


def _xticks(ax, keys):
    idx = [i for i, k in enumerate(keys) if k.endswith("-01")]
    ax.set_xticks(idx)
    ax.set_xticklabels([keys[i][:4] for i in idx])


def tile(name, title, lines, footer, unit="%", zero_line=True):
    """One chart tile: `lines` = [(label, {date: value}, colour)]."""
    fig, ax = plt.subplots(figsize=(6.4, 3.4), dpi=150)
    fig.patch.set_facecolor(BG)
    _style(ax)
    drawn = []
    for label, series, colour in lines:
        if not series:
            continue
        keys, vals = tail(series)
        ax.plot(range(len(keys)), vals, color=colour, linewidth=1.8)
        drawn.append((label, keys, vals, colour))
    if not drawn:
        plt.close(fig)
        return None
    if zero_line:
        ax.axhline(0, color=MUTED, linewidth=0.8)
    keys = max((k for _, k, _, _ in drawn), key=len)
    _xticks(ax, keys)
    for label, kk, vals, colour in drawn:       # direct labels, no legend boxes
        txt = f"{label} {vals[-1]:+.1f}{unit}" if unit == "%" else f"{label} {vals[-1]:,.1f}"
        ax.annotate(txt.strip(), xy=(len(kk) - 1, vals[-1]), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=8.5,
                    color=colour, fontweight="bold")
        ax.plot(len(kk) - 1, vals[-1], "o", color=colour, markersize=4)
    ax.set_xlim(-1, len(keys) * 1.22)           # room for the end labels
    ax.set_title(title, loc="left", fontsize=11, color=INK, fontweight="bold", pad=10)
    fig.text(0.01, 0.015, footer, fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    path = f"outputs/{name}.png"
    fig.savefig(path, facecolor=BG)
    plt.close(fig)
    return path


def main() -> int:
    get = lambda cdid, path=PRICES: _safe(lambda: fetch_ons(OnsSeries(cdid, path)), cdid)
    def _safe(fn, label):
        try:
            return fn()
        except Exception as exc:
            print(f"  skipped {label}: {exc}")
            return {}

    cpi = get("D7BT")
    ghik, ghim, gb7s = get("GHIK"), get("GHIM"), get("GB7S")
    ghgj, ew6t = get("GHGJ"), get("EW6T")
    ghef, evoq = get("GHEF"), get("EVOQ")
    k54u = get("K54U", EARNINGS)
    mgsx = get("MGSX", UNEMP)

    vintages = {k: max(v) for k, v in [("CPI D7BT", cpi), ("PPI GHIK", ghik),
                ("AWE K54U", k54u), ("LFS MGSX", mgsx)] if v}
    newest = max(vintages.values()) if vintages else "?"

    tiles = []
    def add(p, caption):
        if p:
            tiles.append((p, caption))

    f = lambda ids, last: f"ONS {ids}, monthly, to {last}. Public data, Open Government Licence."
    add(tile("cpi", "Consumer prices, annual change",
             [("CPI", yoy(cpi), ACCENT)], f("D7BT", max(cpi) if cpi else "?")),
        "Headline CPI, computed from the index rather than quoted.")
    add(tile("ppi_gap", "Producer prices: the gap the headline hides",
             [("Materials", yoy(ghik), ACCENT), ("Fuels", yoy(ghim), SECOND),
              ("Factory gate", yoy(gb7s), INK)],
             f("GHIK, GHIM, GB7S", max(gb7s) if gb7s else "?")),
        "Inputs against output prices; the spread is the story.")
    add(tile("pay", "Pay against prices",
             [("Earnings", yoy(k54u), ACCENT), ("CPI", yoy(cpi), SECOND)],
             f("K54U, D7BT", max(k54u) if k54u else "?")),
        "Whole-economy earnings growth against CPI: the real-wage squeeze, or its unwind.")
    add(tile("steel", "Steel: inputs vs factory gate",
             [("Inputs", yoy(ghgj), SECOND), ("Factory gate", yoy(ew6t), ACCENT)],
             f("GHGJ, EW6T", max(ew6t) if ew6t else "?")),
        "One sector pair; co-movement is not pass-through.")
    add(tile("food", "Food: inputs vs factory gate",
             [("Meat inputs", yoy(ghef), SECOND), ("Grain mill output", yoy(evoq), ACCENT)],
             f("GHEF, EVOQ", max(evoq) if evoq else "?")),
        "The other cost world: same economy, different inflation.")
    add(tile("unemp", "Unemployment rate",
             [("Rate", mgsx, ACCENT)], f("MGSX", max(mgsx) if mgsx else "?"),
             zero_line=False),
        "LFS unemployment, 16 and over, seasonally adjusted.")

    key = os.environ.get("FRED_API_KEY", "").strip()
    if key:
        brent = _safe(lambda: fetch_fred("DCOILBRENTEU", key), "FRED Brent")
        uscpi = _safe(lambda: fetch_fred("CPIAUCSL", key), "FRED US CPI")
        cable = _safe(lambda: fetch_fred("DEXUSUK", key), "FRED GBPUSD")
        add(tile("brent", "Brent crude, USD/bbl", [("Brent", brent, ACCENT)],
                 "FRED DCOILBRENTEU, monthly average.", unit="", zero_line=False),
            "The common driver behind half the charts above.")
        add(tile("uscpi", "US consumer prices, annual change",
                 [("US CPI", yoy(uscpi), ACCENT)], "FRED CPIAUCSL."),
            "The comparison headline.")
        add(tile("gbpusd", "GBP/USD", [("USD per GBP", cable, ACCENT)],
                 "FRED DEXUSUK, monthly average.", unit="", zero_line=False),
            "Sterling, the input cost nobody budgets for.")
    else:
        print("  FRED_API_KEY not set - FRED row skipped (ONS charts unaffected)")

    # ---- the page -----------------------------------------------------------
    cards = []
    for path, caption in tiles:
        with open(path, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode()
        cards.append(f'<figure><img src="data:image/png;base64,{b64}" alt="">'
                     f"<figcaption>{caption}</figcaption></figure>")
    vint = " · ".join(f"{k} to {v}" for k, v in vintages.items())
    html = f"""<!doctype html><html lang="en-GB"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UK macro chartbook</title><style>
body{{margin:0;background:{BG};color:{INK};font:15px/1.5 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
main{{max-width:72rem;margin:0 auto;padding:2.5rem 1.25rem}}
h1{{font-size:1.6rem;margin:0}} .sub{{color:{MUTED};margin:.3rem 0 1.8rem;font-size:.95rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(21rem,1fr));gap:1.2rem}}
figure{{margin:0;border:1px solid {LINE};border-radius:8px;background:#fff;padding:.6rem}}
img{{width:100%;height:auto;display:block}}
figcaption{{font-size:.8rem;color:{MUTED};padding:.5rem .3rem .2rem}}
footer{{color:{MUTED};font-size:.8rem;margin-top:2rem}}</style></head><body><main>
<h1>UK macro chartbook</h1>
<p class="sub">Generated {date.today():%d %b %Y} · newest observation {newest} · {vint}.
Every chart names its source and series ID. Public data throughout.</p>
<div class="grid">{"".join(cards)}</div>
<footer>Built by chartbook.py. ONS data under the Open Government Licence; FRED
data where shown. A chart that cannot say where it came from is an opinion
with axes.</footer></main></body></html>"""
    with open("outputs/chartbook.html", "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"{len(tiles)} tiles -> outputs/chartbook.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
