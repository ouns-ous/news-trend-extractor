"""Interactive HTML5 and SVG visual dashboard generator for news intelligence."""

from __future__ import annotations
import html
from pathlib import Path
from typing import Dict, List

from news_extractor.models import Digest, Article, TrendTopic


class DashboardGenerator:
    """Renders standalone visual analytics dashboards in HTML5 with vector SVG charts."""

    @staticmethod
    def _generate_donut_svg(pos: int, neu: int, neg: int, width: int = 240, height: int = 240) -> str:
        """Construct an SVG donut chart representing sentiment polarity distribution."""
        total = pos + neu + neg
        if total == 0:
            return "<svg width='240' height='240'><circle cx='120' cy='120' r='80' fill='#334155'/></svg>"

        p_pct = pos / total
        n_pct = neu / total
        ng_pct = neg / total

        circumference = 2 * 3.14159 * 70  # radius = 70
        p_len = p_pct * circumference
        n_len = n_pct * circumference
        ng_len = ng_pct * circumference

        offset_p = 0
        offset_n = -p_len
        offset_ng = -(p_len + n_len)

        svg = f"""
        <svg viewBox="0 0 200 200" width="{width}" height="{height}" class="donut-chart">
            <circle cx="100" cy="100" r="70" fill="transparent" stroke="#1e293b" stroke-width="28" />
            <circle cx="100" cy="100" r="70" fill="transparent" stroke="#10b981" stroke-width="28"
                    stroke-dasharray="{p_len:.1f} {circumference:.1f}" stroke-dashoffset="{offset_p:.1f}"
                    transform="rotate(-90 100 100)" />
            <circle cx="100" cy="100" r="70" fill="transparent" stroke="#64748b" stroke-width="28"
                    stroke-dasharray="{n_len:.1f} {circumference:.1f}" stroke-dashoffset="{offset_n:.1f}"
                    transform="rotate(-90 100 100)" />
            <circle cx="100" cy="100" r="70" fill="transparent" stroke="#ef4444" stroke-width="28"
                    stroke-dasharray="{ng_len:.1f} {circumference:.1f}" stroke-dashoffset="{offset_ng:.1f}"
                    transform="rotate(-90 100 100)" />
            <text x="100" y="96" text-anchor="middle" font-size="20" font-weight="bold" fill="#f8fafc">{total}</text>
            <text x="100" y="115" text-anchor="middle" font-size="11" fill="#94a3b8">Stories</text>
        </svg>
        """
        return svg

    @staticmethod
    def _generate_bar_chart_svg(categories: Dict[str, int], max_width: int = 500) -> str:
        """Construct a horizontal SVG bar chart for category distributions."""
        if not categories:
            return "<p class='text-muted'>No categories found</p>"

        sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:6]
        max_val = max(c[1] for c in sorted_cats) if sorted_cats else 1
        bar_height = 24
        gap = 14
        total_height = len(sorted_cats) * (bar_height + gap) + 10

        bars_svg = []
        for idx, (cat, val) in enumerate(sorted_cats):
            y = idx * (bar_height + gap) + 10
            bar_w = max(10, int((val / max_val) * (max_width - 160)))
            safe_cat = html.escape(cat)

            bars_svg.append(f"""
            <text x="0" y="{y + 17}" font-size="12" fill="#cbd5e1" font-weight="500">{safe_cat[:18]}</text>
            <rect x="140" y="{y}" width="{bar_w}" height="{bar_height}" rx="5" fill="#3b82f6" />
            <text x="{150 + bar_w}" y="{y + 17}" font-size="12" font-weight="bold" fill="#93c5fd">{val}</text>
            """)

        return f"""
        <svg viewBox="0 0 {max_width} {total_height}" width="100%" height="{total_height}">
            {''.join(bars_svg)}
        </svg>
        """

    @classmethod
    def render(cls, digest: Digest, articles: List[Article]) -> str:
        """Render complete interactive HTML5 dashboard."""
        pos = digest.sentiment.positive_count
        neu = digest.sentiment.neutral_count
        neg = digest.sentiment.negative_count
        donut_svg = cls._generate_donut_svg(pos, neu, neg)
        bar_svg = cls._generate_bar_chart_svg(digest.category_breakdown)

        # Build trend pills
        trend_pills = []
        for t in digest.top_trends[:12]:
            safe_phrase = html.escape(t.phrase)
            trend_pills.append(
                f'<span class="badge badge-trend" title="Score: {t.score:.1f} | Mentions: {t.frequency}">'
                f'🔥 {safe_phrase} <small class="text-dim">({t.frequency})</small></span>'
            )
        trend_html = "".join(trend_pills) or "<p class='text-muted'>No active trends detected.</p>"

        # Build article rows
        table_rows = []
        for idx, art in enumerate(articles, start=1):
            safe_title = html.escape(art.title)
            safe_source = html.escape(art.source)
            safe_cat = html.escape(art.category)
            url_link = f'<a href="{html.escape(art.url)}" target="_blank" class="art-link">🔗 Read</a>' if art.url else ""

            badge_cls = "badge-neutral"
            if art.sentiment_label == "Positive":
                badge_cls = "badge-positive"
            elif art.sentiment_label == "Negative":
                badge_cls = "badge-negative"

            kw_tags = " ".join(f'<span class="kw-tag">{html.escape(k)}</span>' for k in art.keywords[:3])

            table_rows.append(f"""
            <tr data-category="{safe_cat}" data-sentiment="{art.sentiment_label}">
                <td>{idx}</td>
                <td>
                    <strong>{safe_title}</strong>
                    <div class="art-meta">{safe_source} &bull; {art.scraped_at.strftime('%Y-%m-%d %H:%M')}</div>
                    <div class="kw-container">{kw_tags}</div>
                </td>
                <td><span class="badge badge-cat">{safe_cat}</span></td>
                <td><span class="badge {badge_cls}">{art.sentiment_label} ({art.sentiment_score:+.2f})</span></td>
                <td>{url_link}</td>
            </tr>
            """)
        table_html = "".join(table_rows)

        # Unique categories for filter dropdown
        categories_opts = "".join(f'<option value="{html.escape(c)}">{html.escape(c)}</option>' for c in sorted(digest.category_breakdown.keys()))

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NewsPulse &bull; Intelligence Dashboard</title>
    <style>
        :root {{
            --bg-main: #0b0f19;
            --bg-card: #131c2e;
            --bg-card-hover: #1e293b;
            --border: #1e293b;
            --text-main: #f8fafc;
            --text-dim: #94a3b8;
            --primary: #3b82f6;
            --success: #10b981;
            --danger: #ef4444;
            --neutral: #64748b;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-main);
            color: var(--text-main);
            padding: 24px;
            line-height: 1.5;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
            padding-bottom: 20px;
            margin-bottom: 24px;
        }}
        .header h1 {{ font-size: 26px; display: flex; align-items: center; gap: 10px; }}
        .header .meta {{ color: var(--text-dim); font-size: 14px; text-align: right; }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
        }}
        .kpi-title {{ font-size: 13px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px; }}
        .kpi-value {{ font-size: 28px; font-weight: bold; margin-top: 6px; color: var(--text-main); }}
        .charts-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 24px;
        }}
        @media (max-width: 900px) {{ .charts-grid {{ grid-template-columns: 1fr; }} }}
        .card h2 {{ font-size: 17px; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }}
        .donut-container {{ display: flex; align-items: center; justify-content: space-around; flex-wrap: wrap; }}
        .legend {{ display: flex; flex-direction: column; gap: 8px; font-size: 13px; }}
        .legend-item {{ display: flex; align-items: center; gap: 8px; }}
        .dot {{ width: 10px; height: 10px; border-radius: 50%; }}
        .dot-pos {{ background: var(--success); }}
        .dot-neu {{ background: var(--neutral); }}
        .dot-neg {{ background: var(--danger); }}
        .trends-card {{ margin-bottom: 24px; }}
        .trends-container {{ display: flex; flex-wrap: wrap; gap: 10px; }}
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }}
        .badge-trend {{ background: rgba(59, 130, 246, 0.15); color: #93c5fd; border: 1px solid rgba(59, 130, 246, 0.3); }}
        .badge-cat {{ background: #1e293b; color: #cbd5e1; }}
        .badge-positive {{ background: rgba(16, 185, 129, 0.2); color: #6ee7b7; }}
        .badge-neutral {{ background: rgba(100, 116, 139, 0.2); color: #cbd5e1; }}
        .badge-negative {{ background: rgba(239, 68, 68, 0.2); color: #fca5a5; }}
        .table-controls {{
            display: flex;
            gap: 12px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }}
        .search-box, .filter-select {{
            background: #0f172a;
            border: 1px solid var(--border);
            color: #f8fafc;
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 14px;
        }}
        .search-box {{ flex-grow: 1; min-width: 200px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        th, td {{
            padding: 12px 14px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        th {{ color: var(--text-dim); font-weight: 600; font-size: 12px; text-transform: uppercase; }}
        tr:hover {{ background-color: var(--bg-card-hover); }}
        .art-meta {{ font-size: 12px; color: var(--text-dim); margin-top: 3px; }}
        .kw-container {{ display: flex; gap: 6px; margin-top: 5px; flex-wrap: wrap; }}
        .kw-tag {{ font-size: 11px; background: #0f172a; padding: 2px 6px; border-radius: 4px; color: #94a3b8; }}
        .art-link {{ color: var(--primary); text-decoration: none; font-weight: 500; }}
        .art-link:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>📰 NewsPulse Intelligence Dashboard</h1>
            <p style="color: var(--text-dim); font-size: 14px; margin-top: 4px;">Automated Cross-Source News & Trend Extraction</p>
        </div>
        <div class="meta">
            <div>Generated: <strong>{digest.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</strong></div>
            <div>Time Window: <strong>Last {digest.timeframe_hours} Hours</strong></div>
        </div>
    </div>

    <div class="kpi-grid">
        <div class="card">
            <div class="kpi-title">Total Ingested Articles</div>
            <div class="kpi-value">{digest.total_articles}</div>
        </div>
        <div class="card">
            <div class="kpi-title">Average Sentiment Index</div>
            <div class="kpi-value">{digest.sentiment.average_score:+.2f}</div>
        </div>
        <div class="card">
            <div class="kpi-title">Top Trending Topic</div>
            <div class="kpi-value" style="font-size: 20px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                {html.escape(digest.top_trends[0].phrase if digest.top_trends else 'N/A')}
            </div>
        </div>
        <div class="card">
            <div class="kpi-title">Active Sources</div>
            <div class="kpi-value">{len(digest.source_breakdown)}</div>
        </div>
    </div>

    <div class="charts-grid">
        <div class="card">
            <h2>📊 Sentiment Distribution</h2>
            <div class="donut-container">
                {donut_svg}
                <div class="legend">
                    <div class="legend-item"><span class="dot dot-pos"></span> Positive: <strong>{pos}</strong> ({digest.sentiment.positive_percentage:.1f}%)</div>
                    <div class="legend-item"><span class="dot dot-neu"></span> Neutral: <strong>{neu}</strong> ({digest.sentiment.neutral_percentage:.1f}%)</div>
                    <div class="legend-item"><span class="dot dot-neg"></span> Negative: <strong>{neg}</strong> ({digest.sentiment.negative_percentage:.1f}%)</div>
                </div>
            </div>
        </div>
        <div class="card">
            <h2>🌐 Coverage by Category</h2>
            {bar_svg}
        </div>
    </div>

    <div class="card trends-card">
        <h2>🔥 Trending N-Grams & Topic Momentum</h2>
        <div class="trends-container">
            {trend_html}
        </div>
    </div>

    <div class="card">
        <h2>📑 Ingested Article Feed & Stories</h2>
        <div class="table-controls">
            <input type="text" id="searchInput" class="search-box" placeholder="🔍 Search by headline or keyword..." onkeyup="filterTable()">
            <select id="catSelect" class="filter-select" onchange="filterTable()">
                <option value="">All Categories</option>
                {categories_opts}
            </select>
            <select id="sentSelect" class="filter-select" onchange="filterTable()">
                <option value="">All Polarities</option>
                <option value="Positive">Positive</option>
                <option value="Neutral">Neutral</option>
                <option value="Negative">Negative</option>
            </select>
        </div>
        <table>
            <thead>
                <tr>
                    <th style="width: 40px;">#</th>
                    <th>Headline & Topics</th>
                    <th style="width: 140px;">Category</th>
                    <th style="width: 140px;">Sentiment</th>
                    <th style="width: 80px;">Action</th>
                </tr>
            </thead>
            <tbody id="articlesBody">
                {table_html}
            </tbody>
        </table>
    </div>

    <script>
        function filterTable() {{
            const search = document.getElementById("searchInput").value.toLowerCase();
            const cat = document.getElementById("catSelect").value;
            const sent = document.getElementById("sentSelect").value;
            const rows = document.querySelectorAll("#articlesBody tr");

            rows.forEach(row => {{
                const text = row.innerText.toLowerCase();
                const rowCat = row.getAttribute("data-category");
                const rowSent = row.getAttribute("data-sentiment");

                const matchSearch = text.includes(search);
                const matchCat = !cat || rowCat === cat;
                const matchSent = !sent || rowSent === sent;

                row.style.display = (matchSearch && matchCat && matchSent) ? "" : "none";
            }});
        }}
    </script>
</body>
</html>"""

    @classmethod
    def export(cls, digest: Digest, articles: List[Article], output_path: Path | str) -> Path:
        """Write HTML dashboard file to disk."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        html_content = cls.render(digest, articles)
        path.write_text(html_content, encoding="utf-8")
        return path
