# UK macro chartbook

A designed one-page macro readout from public series: ONS with no API key,
plus an optional FRED row. One script, one HTML page, and the individual
chart tiles as PNGs.

![Producer prices tile](outputs/ppi_gap.png)

## Why it exists

Most macro reporting is either a dashboard nobody reads or a chart pasted
without its provenance. This is the third thing: a chartbook designed to be
read in one pass, where every chart carries its source, series ID and data
vintage in the footer. A chart that cannot say where it came from is an
opinion with axes.

The outputs are committed deliberately, so the repo shows its product, not
just its code.

## Run it

```
python3 -m venv .venv && .venv/bin/pip install matplotlib
.venv/bin/python chartbook.py
```

Open `outputs/chartbook.html`. Set `FRED_API_KEY` (free from fred.stlouisfed.org)
and three more tiles appear: Brent, US CPI, GBP/USD. Without it the ONS
charts are unaffected.

## The tiles

| Tile | Series | The question it answers |
|---|---|---|
| Consumer prices | D7BT | What is headline inflation, computed from the index rather than quoted |
| Producer price gap | GHIK, GHIM, GB7S | Are input costs and factory gate prices telling the same story |
| Pay against prices | K54U, D7BT | Is the real-wage squeeze unwinding |
| Steel pair | GHGJ, EW6T | One sector's inputs against its own factory gate |
| Food pair | GHEF, EVOQ | The other cost world, same economy |
| Unemployment | MGSX | The labour market behind the earnings line |

All ONS series fetched from the undated timeseries endpoints (the dated ones
can serve frozen editions silently); annual changes computed from index
levels, not quoted rates.

## Design rules

Direct end-labels with the latest value, never a legend box. A zero line on
every rate chart. One palette, shared with [the portfolio site]
(https://sdouglas8787.github.io), so public output reads as one body of work.
Source, series ID and vintage on every tile, without exception.

## Licence and attribution

ONS data under the Open Government Licence v3.0. FRED data per the FRED
terms of use where shown.
