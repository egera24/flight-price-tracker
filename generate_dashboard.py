"""
generate_dashboard.py – Beolvassa a prices.csv-t és legenerálja a docs/index.html-t.
Az adatok JSON-ként vannak beágyazva, külső függőség nélkül fut.
"""

import csv
import json
import os
from datetime import datetime

CSV_PATH = "data/prices.csv"
OUTPUT_PATH = "docs/index.html"

SERIES = [
    {"key": "outbound_09:00",      "label": "Oda 09:00 (one-way)",      "color": "#378ADD", "dashed": False},
    {"key": "outbound_14:10",      "label": "Oda 14:10 (one-way)",       "color": "#1D9E75", "dashed": False},
    {"key": "inbound_18:35",       "label": "Vissza 18:35 (one-way)",    "color": "#D85A30", "dashed": False},
    {"key": "roundtrip_09:00",     "label": "Roundtrip 09:00",           "color": "#7F77DD", "dashed": False},
    {"key": "roundtrip_14:10",     "label": "Roundtrip 14:10",           "color": "#BA7517", "dashed": False},
    {"key": "oneway_total_09:00",  "label": "One-way összesen 09:00",    "color": "#D4537E", "dashed": True},
    {"key": "oneway_total_14:10",  "label": "One-way összesen 14:10",    "color": "#888780", "dashed": True},
]


def load_csv(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_chart_data(rows: list[dict]) -> list[dict]:
    by_ts = {}
    for r in rows:
        ts = r.get("timestamp", "")[:16]
        if not ts:
            continue
        if ts not in by_ts:
            by_ts[ts] = {"ts": ts}
        key = f"{r['search_type']}_{r['departure_time']}"
        try:
            by_ts[ts][key] = float(r["price"])
        except (ValueError, KeyError):
            pass

    chart_data = []
    for d in sorted(by_ts.values(), key=lambda x: x["ts"]):
        out09 = d.get("outbound_09:00")
        out14 = d.get("outbound_14:10")
        inb   = d.get("inbound_18:35")
        if out09 and inb:
            d["oneway_total_09:00"] = round(out09 + inb, 2)
        if out14 and inb:
            d["oneway_total_14:10"] = round(out14 + inb, 2)
        chart_data.append(d)
    return chart_data


def compute_stats(chart_data: list[dict]) -> dict:
    if not chart_data:
        return {}
    latest = chart_data[-1]
    rt09  = latest.get("roundtrip_09:00")
    ow09  = latest.get("oneway_total_09:00")
    all_rt09 = [d["roundtrip_09:00"] for d in chart_data if "roundtrip_09:00" in d]
    return {
        "roundtrip_09_now":  rt09,
        "oneway_total_09_now": ow09,
        "savings_09": round(ow09 - rt09, 0) if rt09 and ow09 else None,
        "min_roundtrip_09": min(all_rt09) if all_rt09 else None,
        "total_rows": len(rows := chart_data),
        "datapoints": len(chart_data),
        "last_updated": latest.get("ts", ""),
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="hu">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Repülőjegy árfigyelő – BUD ↔ IST</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, -apple-system, sans-serif; background: #f4f4f0; color: #1a1a1a; min-height: 100vh; }}
  .container {{ max-width: 960px; margin: 0 auto; padding: 2rem 1rem; }}
  h1 {{ font-size: 1.4rem; font-weight: 500; margin-bottom: 0.25rem; }}
  .subtitle {{ font-size: 0.8rem; color: #666; margin-bottom: 1.5rem; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 1.5rem; }}
  .card {{ background: #fff; border-radius: 10px; padding: 1rem; border: 0.5px solid #e0e0e0; }}
  .card-label {{ font-size: 0.72rem; color: #888; margin-bottom: 4px; }}
  .card-value {{ font-size: 1.4rem; font-weight: 500; }}
  .card-sub {{ font-size: 0.7rem; color: #aaa; margin-top: 2px; }}
  .chart-box {{ background: #fff; border-radius: 10px; padding: 1.25rem; border: 0.5px solid #e0e0e0; margin-bottom: 1rem; }}
  .legend {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 1rem; }}
  .legend-item {{ display: flex; align-items: center; gap: 5px; font-size: 0.72rem; color: #555;
    background: #f9f9f7; border: 0.5px solid #ddd; border-radius: 6px; padding: 3px 8px; cursor: pointer; transition: opacity .15s; }}
  .legend-item.hidden {{ opacity: 0.35; }}
  .legend-line {{ width: 18px; height: 3px; border-radius: 2px; flex-shrink: 0; }}
  .legend-dashed {{ width: 18px; height: 0; border-bottom: 2px dashed; flex-shrink: 0; }}
  .chart-wrap {{ position: relative; height: 340px; }}
  .footer {{ font-size: 0.7rem; color: #aaa; text-align: right; margin-top: 0.5rem; }}
  @media (max-width: 500px) {{ .card-value {{ font-size: 1.1rem; }} }}
</style>
</head>
<body>
<div class="container">
  <h1>BUD ↔ IST repülőjegy árfigyelő</h1>
  <p class="subtitle">Turkish Airlines · augusztus 10–18. · Utoljára frissítve: {last_updated}</p>

  <div class="cards">
    <div class="card">
      <div class="card-label">Roundtrip 09:00 (most)</div>
      <div class="card-value" style="color:#7F77DD">{roundtrip_09_now}</div>
      <div class="card-sub">return jegy</div>
    </div>
    <div class="card">
      <div class="card-label">One-way összesen 09:00 (most)</div>
      <div class="card-value" style="color:#D4537E">{oneway_total_09_now}</div>
      <div class="card-sub">oda + vissza külön</div>
    </div>
    <div class="card">
      <div class="card-label">Megtakarítás return jeggyel</div>
      <div class="card-value" style="color:#1D9E75">{savings_09}</div>
      <div class="card-sub">09:00-ás járattal</div>
    </div>
    <div class="card">
      <div class="card-label">Legolcsóbb roundtrip eddig</div>
      <div class="card-value">{min_roundtrip_09}</div>
      <div class="card-sub">09:00 oda · 18:35 vissza</div>
    </div>
  </div>

  <div class="chart-box">
    <div class="legend" id="legend"></div>
    <div class="chart-wrap">
      <canvas id="chart"></canvas>
    </div>
    <p class="footer">{datapoints} mérési pont · {total_rows} adatsor</p>
  </div>
</div>

<script>
const SERIES = {series_json};
const CHART_DATA = {chart_data_json};

const labels = CHART_DATA.map(d => d.ts.slice(5));

const hidden = {{}};

function buildDatasets() {{
  return SERIES.map(s => ({{
    label: s.label,
    data: CHART_DATA.map(d => d[s.key] ?? null),
    borderColor: s.color,
    backgroundColor: s.color + "22",
    borderWidth: 2,
    borderDash: s.dashed ? [5, 3] : [],
    pointRadius: 3,
    pointHoverRadius: 5,
    tension: 0.1,
    spanGaps: true,
    hidden: hidden[s.key] || false,
  }}));
}}

const chart = new Chart(document.getElementById("chart"), {{
  type: "line",
  data: {{ labels, datasets: buildDatasets() }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ ticks: {{ color: "#888", font: {{ size: 11 }}, maxRotation: 45 }}, grid: {{ color: "#f0f0f0" }} }},
      y: {{ ticks: {{ color: "#888", font: {{ size: 11 }}, callback: v => v + "€" }}, grid: {{ color: "#f0f0f0" }} }}
    }},
    interaction: {{ mode: "index", intersect: false }},
  }}
}});

const legend = document.getElementById("legend");
SERIES.forEach((s, i) => {{
  const item = document.createElement("div");
  item.className = "legend-item";
  item.dataset.index = i;
  const line = document.createElement("div");
  line.className = s.dashed ? "legend-dashed" : "legend-line";
  line.style.background = s.dashed ? "none" : s.color;
  line.style.borderColor = s.color;
  item.appendChild(line);
  item.appendChild(document.createTextNode(s.label));
  item.addEventListener("click", () => {{
    const ds = chart.data.datasets[i];
    ds.hidden = !ds.hidden;
    item.classList.toggle("hidden", ds.hidden);
    chart.update();
  }});
  legend.appendChild(item);
}});
</script>
</body>
</html>"""


def fmt(val, suffix=" EUR"):
    if val is None:
        return "–"
    return f"{val:.0f}{suffix}"


def generate(csv_path: str, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    rows = load_csv(csv_path)
    chart_data = build_chart_data(rows)
    stats = compute_stats(chart_data)

    html = HTML_TEMPLATE.format(
        last_updated=stats.get("last_updated", "–"),
        roundtrip_09_now=fmt(stats.get("roundtrip_09_now")),
        oneway_total_09_now=fmt(stats.get("oneway_total_09_now")),
        savings_09=fmt(stats.get("savings_09")),
        min_roundtrip_09=fmt(stats.get("min_roundtrip_09")),
        datapoints=stats.get("datapoints", 0),
        total_rows=len(rows),
        series_json=json.dumps(SERIES, ensure_ascii=False),
        chart_data_json=json.dumps(chart_data, ensure_ascii=False),
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Jekyll kikapcsolása – GitHub Pages ne próbálja feldolgozni a HTML-t
    nojekyll_path = os.path.join(os.path.dirname(output_path), ".nojekyll")
    open(nojekyll_path, "w").close()

    print(f"Dashboard legenerálva: {output_path} ({len(chart_data)} mérési pont)")


if __name__ == "__main__":
    generate(CSV_PATH, OUTPUT_PATH)
