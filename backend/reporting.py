from html import escape
from typing import Any


def build_report(record: dict[str, Any]) -> str:
    details = record["details"]
    quality = details.get("data_quality", {})
    indications = details.get("potential_indications", [])
    rows = "".join(
        f"<tr><td>R{index}</td><td>{item['x']}</td><td>{item['y']}</td>"
        f"<td>{item['area']} mm²</td><td>{escape(item['severity'])}</td></tr>"
        for index, item in enumerate(indications, 1)
    )
    if not rows:
        rows = '<tr><td colspan="5">No potential high-response regions identified.</td></tr>'
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Inspection Report {escape(record['id'])}</title>
<style>body{{font:15px system-ui;color:#1b2833;max-width:900px;margin:40px auto}}
h1{{color:#126e73}}h2{{border-bottom:1px solid #ccd9df;padding-bottom:8px}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccd9df;padding:8px;text-align:left}}
.note{{padding:12px;background:#edf7f6;border-left:4px solid #53a8a1}}</style></head>
<body><h1>C-Scan Damage Mapping in Composite Materials</h1>
<p><strong>Inspection report</strong> | {escape(record['created_at'])}</p>
<h2>Inspection information</h2><p>Inspection ID: {escape(record['id'])}<br>
Material: {escape(record['material'])}<br>Thickness: {record['thickness_mm']} mm</p>
<h2>Input data</h2><p>CSV: {escape(record['csv_filename'])}<br>
PLY: {escape(record['ply_filename'] or 'Not provided')}<br>
Surface image: {escape(record['surface_filename'] or 'Not provided')}</p>
<h2>Data quality</h2><p>Score: {quality.get('score', 'Unavailable')}/100</p>
<h2>Potential damage indications</h2><table><tr><th>Region</th><th>X</th><th>Y</th>
<th>Area</th><th>Relative severity</th></tr>{rows}</table>
<p class="note">These are analytical potential damage indications based on relative
signal response. They are not validated defects and do not constitute a certified
NDT assessment.</p></body></html>"""
