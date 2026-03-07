#!/usr/bin/env python3
"""Build an interactive HTML dashboard of agent skills metadata."""

import json
import re
import os
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path("/home/shapor/src/skillathon")
SRC = ROOT / "src"

# Load existing stats
with open(ROOT / "skill_stats.json") as f:
    stats = json.load(f)

skills = stats["skills"]

# Parse download counts from openclaw README
readme = (SRC / "awesome-openclaw-skills" / "README.md").read_text()

# Parse category sections and skill->downloads mapping
current_category = "Uncategorized"
openclaw_categories = {}  # install_name -> category
openclaw_downloads = {}   # install_name -> count

for line in readme.split("\n"):
    # Category headers like "## Agent Core & Memory"
    m = re.match(r'^## (.+)$', line)
    if m and not m.group(1).startswith(("Install", "Contents", "Contributing", "License", "Awesome")):
        current_category = m.group(1).strip()

    # Table rows: | [**Name**](./skills/xyz) | `install_name` | Description... | [COUNT](url) |
    m = re.match(r'\|\s*\[.+?\]\(\.\/skills\/(.+?)\)\s*\|\s*`(.+?)`\s*\|.*?\|\s*\[([0-9,]+)\]', line)
    if m:
        folder_name = m.group(1)
        install_name = m.group(2)
        count = int(m.group(3).replace(",", ""))
        openclaw_downloads[folder_name] = count
        openclaw_categories[folder_name] = current_category

# Enrich skills with downloads and better categories
for skill in skills:
    skill["downloads"] = 0

    # Match openclaw skills by folder name
    if skill["repo"] == "awesome-openclaw-skills":
        # Extract folder name from path
        parts = skill["file_path"].split("/skills/")
        if len(parts) > 1:
            folder = parts[-1].split("/")[0]
            skill["downloads"] = openclaw_downloads.get(folder, 0)
            if folder in openclaw_categories:
                skill["display_category"] = openclaw_categories[folder]
            else:
                skill["display_category"] = skill.get("category", "Uncategorized")
        else:
            skill["display_category"] = "Uncategorized"
    elif skill["repo"] == "knowledge-work-plugins":
        # Use top-level dir as category
        parts = skill["file_path"].split("knowledge-work-plugins/")
        if len(parts) > 1:
            cat = parts[1].split("/")[0]
            skill["display_category"] = cat.replace("-", " ").title()
        else:
            skill["display_category"] = "Other"
    elif skill["repo"] == "anthropic-skills":
        skill["display_category"] = "Anthropic Official"
    elif skill["repo"] == "sundial-skills":
        skill["display_category"] = "Sundial Curated"
    else:
        skill["display_category"] = skill.get("category", "Other")

# Compute aggregates
total = len(skills)
by_repo = Counter(s["repo"] for s in skills)
by_category = Counter(s["display_category"] for s in skills)
with_scripts = sum(1 for s in skills if s.get("has_scripts"))
with_refs = sum(1 for s in skills if s.get("has_references"))
with_assets = sum(1 for s in skills if s.get("has_assets"))
with_none = sum(1 for s in skills if not s.get("has_scripts") and not s.get("has_references") and not s.get("has_assets"))
avg_lines = sum(s.get("line_count", 0) for s in skills) / max(total, 1)
avg_size = sum(s.get("file_size_bytes", 0) for s in skills) / max(total, 1)
top_downloads = sorted(skills, key=lambda s: s["downloads"], reverse=True)[:25]
max_dl = top_downloads[0]["downloads"] if top_downloads else 0

# Avg size by repo
avg_size_by_repo = {}
for repo, count in by_repo.items():
    repo_skills = [s for s in skills if s["repo"] == repo]
    avg_size_by_repo[repo] = sum(s.get("file_size_bytes", 0) for s in repo_skills) / max(len(repo_skills), 1)

# Line count distribution buckets
line_buckets = Counter()
for s in skills:
    lc = s.get("line_count", 0)
    if lc <= 50: line_buckets["0-50"] += 1
    elif lc <= 100: line_buckets["51-100"] += 1
    elif lc <= 200: line_buckets["101-200"] += 1
    elif lc <= 500: line_buckets["201-500"] += 1
    else: line_buckets["500+"] += 1

# Scatter data: line_count vs folder_size (sample to keep it reasonable)
scatter_data = [
    {"x": s.get("line_count", 0), "y": s.get("folder_size_bytes", 0), "name": s.get("name", "?"), "repo": s["repo"]}
    for s in skills if s.get("line_count", 0) > 0
]

# Top 15 categories
top_cats = by_category.most_common(15)

# Table data (all skills, sorted by downloads then line count)
table_data = sorted(skills, key=lambda s: (-s["downloads"], -s.get("line_count", 0)))

# Build the dashboard data object
dashboard_data = {
    "kpis": {
        "total": total,
        "repos": len(by_repo),
        "avg_lines": round(avg_lines, 1),
        "avg_size_bytes": round(avg_size),
        "with_scripts": with_scripts,
        "with_references": with_refs,
        "max_download": max_dl,
    },
    "by_repo": dict(by_repo.most_common()),
    "top_downloads": [{"name": s.get("name", "?"), "downloads": s["downloads"], "repo": s["repo"]} for s in top_downloads],
    "top_categories": {k: v for k, v in top_cats},
    "scatter": scatter_data[:500],  # cap for performance
    "resources_breakdown": {"Scripts": with_scripts, "References": with_refs, "Assets": with_assets, "None": with_none},
    "avg_size_by_repo": {k: round(v) for k, v in avg_size_by_repo.items()},
    "line_distribution": dict(line_buckets),
    "table": [
        {
            "name": s.get("name", "?"),
            "repo": s["repo"],
            "category": s.get("display_category", ""),
            "lines": s.get("line_count", 0),
            "size": s.get("file_size_bytes", 0),
            "folder_size": s.get("folder_size_bytes", 0),
            "downloads": s["downloads"],
            "scripts": s.get("has_scripts", False),
            "references": s.get("has_references", False),
            "files": s.get("file_count_in_folder", 0),
        }
        for s in table_data  # all skills
    ],
    "all_repos": sorted(by_repo.keys()),
    "all_categories": sorted(by_category.keys()),
}

data_json = json.dumps(dashboard_data, separators=(',', ':'))

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agent Skills Ecosystem Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1"></script>
<style>
:root {{
    --bg-primary: #f8f9fa; --bg-card: #ffffff; --bg-header: #1a1a2e;
    --text-primary: #212529; --text-secondary: #6c757d; --text-on-dark: #ffffff;
    --color-1: #4C72B0; --color-2: #DD8452; --color-3: #55A868; --color-4: #C44E52;
    --color-5: #8172B3; --color-6: #937860; --color-7: #DA8BC3; --color-8: #8C8C8C;
    --positive: #28a745; --negative: #dc3545; --gap: 16px; --radius: 8px;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:var(--bg-primary); color:var(--text-primary); line-height:1.5; }}
.container {{ max-width:1400px; margin:0 auto; padding:var(--gap); }}
header {{ background:var(--bg-header); color:var(--text-on-dark); padding:20px 24px; border-radius:var(--radius); margin-bottom:var(--gap); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; }}
header h1 {{ font-size:20px; font-weight:600; }}
.filters {{ display:flex; gap:12px; align-items:center; flex-wrap:wrap; }}
.filters label {{ font-size:12px; color:rgba(255,255,255,0.7); }}
.filters select {{ padding:6px 10px; border:1px solid rgba(255,255,255,0.2); border-radius:4px; background:rgba(255,255,255,0.1); color:var(--text-on-dark); font-size:13px; }}
.filters select option {{ background:var(--bg-header); color:var(--text-on-dark); }}
.kpi-row {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:var(--gap); margin-bottom:var(--gap); }}
.kpi-card {{ background:var(--bg-card); border-radius:var(--radius); padding:20px 24px; box-shadow:0 1px 3px rgba(0,0,0,0.08); }}
.kpi-label {{ font-size:12px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px; }}
.kpi-value {{ font-size:26px; font-weight:700; }}
.kpi-sub {{ font-size:12px; color:var(--text-secondary); }}
.chart-row {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(380px,1fr)); gap:var(--gap); margin-bottom:var(--gap); }}
.chart-card {{ background:var(--bg-card); border-radius:var(--radius); padding:20px 24px; box-shadow:0 1px 3px rgba(0,0,0,0.08); }}
.chart-card h3 {{ font-size:14px; font-weight:600; margin-bottom:12px; }}
.chart-card canvas {{ max-height:300px; }}
.table-section {{ background:var(--bg-card); border-radius:var(--radius); padding:20px 24px; box-shadow:0 1px 3px rgba(0,0,0,0.08); overflow-x:auto; margin-bottom:var(--gap); }}
.table-section h3 {{ font-size:14px; font-weight:600; margin-bottom:12px; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
thead th {{ text-align:left; padding:8px 10px; border-bottom:2px solid #dee2e6; color:var(--text-secondary); font-size:11px; text-transform:uppercase; letter-spacing:0.5px; cursor:pointer; user-select:none; white-space:nowrap; }}
thead th:hover {{ color:var(--text-primary); background:#f8f9fa; }}
tbody td {{ padding:8px 10px; border-bottom:1px solid #f0f0f0; }}
tbody tr:hover {{ background:#f8f9fa; }}
.tag {{ display:inline-block; padding:2px 6px; border-radius:3px; font-size:11px; font-weight:500; }}
.tag-yes {{ background:#d4edda; color:#155724; }}
.tag-no {{ background:#f8f9fa; color:#ccc; }}
footer {{ text-align:center; padding:12px; color:var(--text-secondary); font-size:12px; }}
@media(max-width:768px) {{ header {{ flex-direction:column; align-items:flex-start; }} .kpi-row {{ grid-template-columns:repeat(2,1fr); }} .chart-row {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="container">
<header>
    <h1>Agent Skills Ecosystem Dashboard</h1>
    <div class="filters">
        <label>Repo</label>
        <select id="f-repo" onchange="applyFilters()"><option value="all">All Repos</option></select>
        <label>Category</label>
        <select id="f-cat" onchange="applyFilters()"><option value="all">All Categories</option></select>
        <label style="display:flex;align-items:center;gap:4px;cursor:pointer">
            <input type="checkbox" id="f-noclaws" onchange="applyFilters()" style="cursor:pointer"> Hide OpenClaw (939)
        </label>
    </div>
</header>

<section class="kpi-row">
    <div class="kpi-card"><div class="kpi-label">Total Skills</div><div class="kpi-value" id="k-total">-</div><div class="kpi-sub">across all repos</div></div>
    <div class="kpi-card"><div class="kpi-label">Repositories</div><div class="kpi-value" id="k-repos">-</div><div class="kpi-sub">sources indexed</div></div>
    <div class="kpi-card"><div class="kpi-label">Avg SKILL.md</div><div class="kpi-value" id="k-avglines">-</div><div class="kpi-sub">lines per skill</div></div>
    <div class="kpi-card"><div class="kpi-label">With Scripts</div><div class="kpi-value" id="k-scripts">-</div><div class="kpi-sub">bundled code</div></div>
    <div class="kpi-card"><div class="kpi-label">With References</div><div class="kpi-value" id="k-refs">-</div><div class="kpi-sub">reference docs</div></div>
    <div class="kpi-card"><div class="kpi-label">Top Downloads</div><div class="kpi-value" id="k-maxdl">-</div><div class="kpi-sub">single skill max</div></div>
</section>

<section class="chart-row">
    <div class="chart-card"><h3>Skills Count by Repository</h3><canvas id="c-repo"></canvas></div>
    <div class="chart-card"><h3>Top 20 Skills by Downloads</h3><canvas id="c-downloads"></canvas></div>
</section>
<section class="chart-row">
    <div class="chart-card"><h3>Skills by Category (Top 15)</h3><canvas id="c-category"></canvas></div>
    <div class="chart-card"><h3>Bundled Resources Breakdown</h3><canvas id="c-resources"></canvas></div>
</section>
<section class="chart-row">
    <div class="chart-card"><h3>SKILL.md Size Distribution (Lines)</h3><canvas id="c-lines"></canvas></div>
    <div class="chart-card"><h3>Avg SKILL.md Lines by Repo</h3><canvas id="c-avgsize"></canvas></div>
</section>
<section class="chart-row">
    <div class="chart-card"><h3>% Skills with Scripts by Repo</h3><canvas id="c-scriptpct"></canvas></div>
    <div class="chart-card"><h3>% Skills with References by Repo</h3><canvas id="c-refpct"></canvas></div>
</section>

<section class="table-section">
    <h3>Skills Detail (Top 200)</h3>
    <table id="skill-table">
    <thead><tr>
        <th onclick="sortTable(0)">Name</th>
        <th onclick="sortTable(1)">Repo</th>
        <th onclick="sortTable(2)">Category</th>
        <th onclick="sortTable(3)">Lines</th>
        <th onclick="sortTable(4)">Size</th>
        <th onclick="sortTable(5)">Downloads</th>
        <th onclick="sortTable(6)">Scripts</th>
        <th onclick="sortTable(7)">Refs</th>
        <th onclick="sortTable(8)">Files</th>
    </tr></thead>
    <tbody id="table-body"></tbody>
    </table>
</section>

<footer>Skillathon 2026 &mdash; Agent Skills Ecosystem Overview &mdash; Data from Anthropic, Sundial, OpenClaw</footer>
</div>

<script>
const D = {data_json};
const COLORS = ['#4C72B0','#DD8452','#55A868','#C44E52','#8172B3','#937860','#DA8BC3','#8C8C8C','#CCB974','#64B5CD','#4C72B0','#DD8452','#55A868','#C44E52','#8172B3'];
let charts = {{}};
let sortCol = -1, sortDir = 1;
let currentFiltered = D.table;

function init() {{
    D.all_repos.forEach(r => {{
        const o = document.createElement('option'); o.value = r; o.textContent = r;
        document.getElementById('f-repo').appendChild(o);
    }});
    D.all_categories.forEach(c => {{
        const o = document.createElement('option'); o.value = c; o.textContent = c;
        document.getElementById('f-cat').appendChild(o);
    }});
    applyFilters();
}}

function fmt(n) {{ return n >= 1e6 ? (n/1e6).toFixed(1)+'M' : n >= 1e3 ? (n/1e3).toFixed(1)+'K' : n.toLocaleString(); }}

function countBy(arr, key) {{
    const m = {{}};
    arr.forEach(s => {{ const k = s[key] || 'Other'; m[k] = (m[k]||0) + 1; }});
    return Object.fromEntries(Object.entries(m).sort((a,b) => b[1]-a[1]));
}}

function makeChart(id, type, labels, data, opts={{}}) {{
    const ctx = document.getElementById(id).getContext('2d');
    if (charts[id]) charts[id].destroy();
    const datasets = [{{
        data: data,
        backgroundColor: opts.bg || COLORS.slice(0, Math.max(data.length, 1)).map(c=>c+'CC'),
        borderColor: opts.border || COLORS.slice(0, Math.max(data.length, 1)),
        borderWidth: 1, borderRadius: 3
    }}];
    charts[id] = new Chart(ctx, {{
        type, data: {{ labels, datasets }},
        options: {{
            responsive:true, maintainAspectRatio:false,
            indexAxis: opts.horizontal ? 'y' : 'x',
            plugins: {{
                legend: {{ display: type === 'doughnut' }},
                tooltip: {{ callbacks: {{ label: ctx => {{
                    let v;
                    if (ctx.chart.config.type === 'doughnut') v = ctx.parsed;
                    else if (ctx.chart.options.indexAxis === 'y') v = ctx.parsed.x;
                    else v = ctx.parsed.y;
                    return (ctx.label || '') + ': ' + fmt(typeof v === 'number' ? v : 0);
                }} }} }}
            }},
            scales: type === 'doughnut' ? {{}} : {{
                x: {{ grid:{{ display: !!opts.horizontal }}, ticks:{{ callback: function(v) {{ return opts.horizontal ? fmt(v) : this.getLabelForValue(v); }} }} }},
                y: {{ beginAtZero:true, grid:{{ display: !opts.horizontal }}, ticks:{{ callback: function(v) {{ return opts.horizontal ? this.getLabelForValue(v) : fmt(v); }} }} }}
            }}
        }}
    }});
}}

function renderAll(data) {{
    // KPIs
    const total = data.length;
    const repos = new Set(data.map(s=>s.repo)).size;
    const avgLines = total ? (data.reduce((a,s)=>a+s.lines,0)/total).toFixed(1) : 0;
    const wScripts = data.filter(s=>s.scripts).length;
    const wRefs = data.filter(s=>s.references).length;
    const maxDl = data.reduce((m,s)=>Math.max(m,s.downloads),0);
    document.getElementById('k-total').textContent = fmt(total);
    document.getElementById('k-repos').textContent = repos;
    document.getElementById('k-avglines').textContent = avgLines + ' lines';
    document.getElementById('k-scripts').textContent = fmt(wScripts);
    document.getElementById('k-refs').textContent = fmt(wRefs);
    document.getElementById('k-maxdl').textContent = fmt(maxDl);

    // Skills by repo
    const byRepo = countBy(data, 'repo');
    makeChart('c-repo', 'bar', Object.keys(byRepo), Object.values(byRepo));

    // Top downloads
    const topDl = [...data].sort((a,b)=>b.downloads-a.downloads).slice(0,20).filter(s=>s.downloads>0);
    makeChart('c-downloads', 'bar', topDl.map(s=>s.name), topDl.map(s=>s.downloads), {{horizontal:true}});

    // Top categories
    const byCat = countBy(data, 'category');
    const topCats = Object.entries(byCat).slice(0,15);
    makeChart('c-category', 'bar', topCats.map(e=>e[0]), topCats.map(e=>e[1]));

    // Resources breakdown
    const wAssets = data.filter(s=>s.files>2).length; // rough proxy
    const wNone = data.filter(s=>!s.scripts&&!s.references).length;
    makeChart('c-resources', 'doughnut', ['Scripts','References','Neither'], [wScripts, wRefs, wNone]);

    // Line distribution
    const lineBuckets = {{'0-50':0,'51-100':0,'101-200':0,'201-500':0,'500+':0}};
    data.forEach(s => {{
        if (s.lines<=50) lineBuckets['0-50']++;
        else if (s.lines<=100) lineBuckets['51-100']++;
        else if (s.lines<=200) lineBuckets['101-200']++;
        else if (s.lines<=500) lineBuckets['201-500']++;
        else lineBuckets['500+']++;
    }});
    makeChart('c-lines', 'bar', Object.keys(lineBuckets), Object.values(lineBuckets));

    // Avg lines by repo
    const repoLines = {{}}, repoCounts = {{}};
    data.forEach(s => {{ repoLines[s.repo] = (repoLines[s.repo]||0)+s.lines; repoCounts[s.repo] = (repoCounts[s.repo]||0)+1; }});
    const avgByRepo = Object.fromEntries(Object.keys(repoLines).map(r=>[r, Math.round(repoLines[r]/repoCounts[r])]));
    makeChart('c-avgsize', 'bar', Object.keys(avgByRepo), Object.values(avgByRepo));

    // % with scripts by repo
    const repoScripts = {{}};
    data.forEach(s => {{ if (!repoScripts[s.repo]) repoScripts[s.repo] = [0,0]; repoScripts[s.repo][1]++; if (s.scripts) repoScripts[s.repo][0]++; }});
    const scriptPct = Object.fromEntries(Object.entries(repoScripts).map(([r,[y,t]])=>[r, Math.round(y/t*100)]));
    makeChart('c-scriptpct', 'bar', Object.keys(scriptPct), Object.values(scriptPct));

    // % with references by repo
    const repoRefs = {{}};
    data.forEach(s => {{ if (!repoRefs[s.repo]) repoRefs[s.repo] = [0,0]; repoRefs[s.repo][1]++; if (s.references) repoRefs[s.repo][0]++; }});
    const refPct = Object.fromEntries(Object.entries(repoRefs).map(([r,[y,t]])=>[r, Math.round(y/t*100)]));
    makeChart('c-refpct', 'bar', Object.keys(refPct), Object.values(refPct));

    // Table
    renderTable(data);
}}

function renderTable(data) {{
    const show = data.slice(0, 200);
    const tbody = document.getElementById('table-body');
    tbody.innerHTML = show.map(s => `<tr>
        <td><strong>${{s.name}}</strong></td>
        <td>${{s.repo}}</td>
        <td>${{s.category}}</td>
        <td>${{s.lines}}</td>
        <td>${{fmt(s.size)}}</td>
        <td>${{s.downloads ? fmt(s.downloads) : '-'}}</td>
        <td><span class="tag ${{s.scripts?'tag-yes':'tag-no'}}">${{s.scripts?'Yes':'No'}}</span></td>
        <td><span class="tag ${{s.references?'tag-yes':'tag-no'}}">${{s.references?'Yes':'No'}}</span></td>
        <td>${{s.files}}</td>
    </tr>`).join('');
    document.querySelector('.table-section h3').textContent = 'Skills Detail (' + data.length + ' shown, top 200 in table)';
}}

function sortTable(col) {{
    if (sortCol === col) sortDir *= -1; else {{ sortCol = col; sortDir = 1; }}
    const keys = ['name','repo','category','lines','size','downloads','scripts','references','files'];
    const key = keys[col];
    currentFiltered = [...currentFiltered].sort((a,b) => {{
        const av = a[key], bv = b[key];
        const cmp = av < bv ? -1 : av > bv ? 1 : 0;
        return cmp * sortDir;
    }});
    renderTable(currentFiltered);
}}

function applyFilters() {{
    const repo = document.getElementById('f-repo').value;
    const cat = document.getElementById('f-cat').value;
    const hideOC = document.getElementById('f-noclaws').checked;
    currentFiltered = D.table.filter(s => {{
        if (hideOC && s.repo === 'awesome-openclaw-skills') return false;
        if (repo !== 'all' && s.repo !== repo) return false;
        if (cat !== 'all' && s.category !== cat) return false;
        return true;
    }});
    sortCol = -1; sortDir = 1;
    renderAll(currentFiltered);
}}

init();
</script>
</body>
</html>'''

with open(ROOT / "skills_dashboard.html", "w") as f:
    f.write(html)

print(f"Dashboard written to {ROOT / 'skills_dashboard.html'}")
print(f"Skills: {total}, Repos: {len(by_repo)}, Downloads tracked: {sum(1 for s in skills if s['downloads'] > 0)}")
