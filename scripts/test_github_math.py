#!/usr/bin/env python3
"""
Test GitHub math rendering compatibility.

Sends markdown snippets to GitHub's API to see how cmark-gfm processes
underscores in inline math, then renders the same formulas locally with
both MathJax and KaTeX for comparison.

Usage:
    python scripts/test_github_math.py

Output:
    Opens output/math_render_test.html in your default browser.
"""

import html as html_mod
import json
import sys
import webbrowser
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Test cases: various escape strategies for underscore in inline math
# Each tuple: (label, raw_markdown_formula)
# The markdown is exactly what would appear in the .md source file.
# ---------------------------------------------------------------------------

FORMULAS = [
    # --- Simple feature name: logret_1 ---
    (
        "A1: }_{} subscript (original)",
        r"$\text{logret}_{1}(t) = \log(C_t / C_{t-1})$",
    ),
    (
        r"A2: \_ inside \text{}",
        r"$\text{logret\_1}(t) = \log(C_t / C_{t-1})$",
    ),
    (
        r"A3: \textunderscore",
        r"$\text{logret\textunderscore 1}(t) = \log(C_t / C_{t-1})$",
    ),
    (
        r"A4: \operatorname bare _",
        r"$\operatorname{logret_1}(t) = \log(C_t / C_{t-1})$",
    ),
    (
        r"A5: \operatorname escaped \_",
        r"$\operatorname{logret\_1}(t) = \log(C_t / C_{t-1})$",
    ),
    (
        r"A6: \mathrm + math subscript",
        r"$\mathrm{logret}_1(t) = \log(C_t / C_{t-1})$",
    ),
    (
        r"A7: double-backslash \\_",
        r"$\text{logret\\_1}(t) = \log(C_t / C_{t-1})$",
    ),
    (
        "A8: backtick-dollar $` `$",
        r"$`\text{logret_1}(t) = \log(C_t / C_{t-1})`$",
    ),
    (
        r"A9: \text with {\_}",
        r"$\text{logret{\_}1}(t) = \log(C_t / C_{t-1})$",
    ),
    (
        r"A10: \htmlStyle workaround",
        r"$\text{logret\text{\textunderscore}1}(t) = \log(C_t / C_{t-1})$",
    ),
    # --- Complex formula: vol_24 with nested feature names ---
    (
        "B1: vol complex original",
        r"$\text{vol}_{24}(t) = \text{std}( \text{logret}_{1}(t-i) )_{i=0..23}$",
    ),
    (
        r"B2: vol complex \_",
        r"$\text{vol\_24}(t) = \text{std}( \text{logret\_1}(t-i) )_{i=0..23}$",
    ),
    (
        "B3: vol complex backtick-dollar",
        r"$`\text{vol}_{24}(t) = \text{std}( \text{logret}_{1}(t-i) )_{i=0..23}`$",
    ),
    (
        r"B4: vol complex \operatorname",
        r"$\operatorname{vol\_24}(t) = \operatorname{std}( \operatorname{logret\_1}(t-i) )_{i=0..23}$",
    ),
    # --- EMA with compound name ---
    (
        r"C1: ema_ratio \textunderscore",
        r"$\text{ema\textunderscore ratio}(t) = \text{EMA}_{12}(t) / \text{EMA}_{26}(t) - 1$",
    ),
    (
        r"C2: ema_ratio \_",
        r"$\text{ema\_ratio}(t) = \text{EMA}_{12}(t) / \text{EMA}_{26}(t) - 1$",
    ),
    (
        r"C3: ema_ratio \operatorname \_",
        r"$\operatorname{ema\_ratio}(t) = \operatorname{EMA}_{12}(t) / \operatorname{EMA}_{26}(t) - 1$",
    ),
    (
        "C4: ema_ratio backtick-dollar",
        r"$`\text{ema\_ratio}(t) = \text{EMA}_{12}(t) / \text{EMA}_{26}(t) - 1`$",
    ),
]


def build_markdown() -> str:
    """Build a complete markdown document with all test cases."""
    lines = ["# Math Rendering Test\n"]

    # Standalone tests
    lines.append("## Standalone (outside table)\n")
    for label, formula in FORMULAS:
        lines.append(f"**{label}**: {formula}\n")

    # Table tests (more aggressive GFM processing)
    lines.append("\n## In table\n")
    lines.append("| # | Label | Formula |")
    lines.append("| --- | --- | --- |")
    for i, (label, formula) in enumerate(FORMULAS, 1):
        lines.append(f"| {i} | {label} | {formula} |")

    return "\n".join(lines)


def call_github_api(markdown_text: str) -> str:
    """Render markdown through GitHub's actual API (cmark-gfm)."""
    resp = requests.post(
        "https://api.github.com/markdown",
        json={"text": markdown_text, "mode": "gfm"},
        headers={"Accept": "application/vnd.github+json"},
        timeout=30,
    )
    if resp.status_code == 403:
        return "<p style='color:orange'>⚠️ GitHub API rate-limited. Push the test .md file to the repo instead.</p>"
    resp.raise_for_status()
    return resp.text


def extract_katex_tex(markdown_formula: str) -> str:
    """Extract the TeX content from a $...$ or $`...`$ markdown formula."""
    s = markdown_formula.strip()
    if s.startswith("$`") and s.endswith("`$"):
        return s[2:-2]
    if s.startswith("$") and s.endswith("$"):
        return s[1:-1]
    return s


def generate_html(github_html: str, markdown_source: str) -> str:
    """Generate comparison HTML with GitHub output + local KaTeX + MathJax."""
    katex_data = json.dumps(
        [(label, extract_katex_tex(formula)) for label, formula in FORMULAS]
    )
    escaped_md = html_mod.escape(markdown_source)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>GitHub Math Rendering Test</title>
<!-- MathJax (same version GitHub uses) -->
<script>
MathJax = {{
  tex: {{
    inlineMath: [['$', '$']],
    displayMath: [['$$', '$$']]
  }},
  options: {{ skipHtmlTags: ['code', 'pre', 'script'] }}
}};
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js" async></script>
<!-- KaTeX (same version VS Code uses) -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<style>
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    max-width: 1400px; margin: 20px auto; padding: 0 20px;
    font-size: 14px; line-height: 1.6;
}}
h1 {{ border-bottom: 2px solid #0366d6; padding-bottom: 8px; }}
h2 {{ color: #0366d6; margin-top: 30px; }}
table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
th, td {{ border: 1px solid #d0d7de; padding: 6px 12px; text-align: left; vertical-align: top; }}
th {{ background: #f6f8fa; font-weight: 600; }}
.ok {{ color: #1a7f37; font-weight: bold; }}
.err {{ color: #cf222e; font-weight: bold; }}
.github-box {{
    border: 2px solid #0366d6; padding: 20px; border-radius: 6px;
    margin: 15px 0; background: #fff;
}}
pre {{
    background: #f6f8fa; padding: 12px; border-radius: 6px;
    overflow-x: auto; font-size: 12px; white-space: pre-wrap;
}}
.legend {{ background: #fffbdd; border: 1px solid #d4a72c; padding: 10px; border-radius: 4px; margin: 15px 0; }}
</style>
</head>
<body>

<h1>🔬 GitHub Math Rendering Test</h1>

<div class="legend">
<strong>Goal:</strong> Find LaTeX syntax for underscores that renders correctly on
<strong>both</strong> GitHub (MathJax after cmark-gfm) <strong>and</strong> VS Code (KaTeX).
Each row tests a different escape strategy.
</div>

<!-- ================================================================== -->
<h2>1 — GitHub API rendering (cmark-gfm → MathJax)</h2>
<p><em>This is the actual HTML returned by <code>POST /markdown</code>,
rendered in your browser with MathJax.</em></p>
<div class="github-box">
{github_html}
</div>

<!-- ================================================================== -->
<h2>2 — Local KaTeX rendering (like VS Code)</h2>
<table>
<thead><tr><th>#</th><th>Label</th><th>KaTeX render</th><th>Status</th></tr></thead>
<tbody id="katex-table"></tbody>
</table>

<script>
document.addEventListener("DOMContentLoaded", function() {{
    // Wait for KaTeX to load
    function tryRender() {{
        if (typeof katex === "undefined") {{
            setTimeout(tryRender, 200);
            return;
        }}
        const cases = {katex_data};
        const tbody = document.getElementById("katex-table");
        cases.forEach(function(item, idx) {{
            const label = item[0];
            const tex = item[1];
            const row = tbody.insertRow();
            row.insertCell().textContent = idx + 1;
            row.insertCell().textContent = label;
            const renderCell = row.insertCell();
            const statusCell = row.insertCell();
            try {{
                katex.render(tex, renderCell, {{ throwOnError: true, displayMode: false }});
                statusCell.innerHTML = '<span class="ok">✅ OK</span>';
            }} catch(e) {{
                renderCell.style.fontFamily = "monospace";
                renderCell.style.fontSize = "11px";
                renderCell.style.color = "#666";
                renderCell.textContent = tex;
                statusCell.innerHTML = '<span class="err">❌ ' + e.message.substring(0, 80) + '</span>';
            }}
        }});
    }}
    tryRender();
}});
</script>

<!-- ================================================================== -->
<h2>3 — Raw markdown source</h2>
<pre>{escaped_md}</pre>

<!-- ================================================================== -->
<h2>4 — GitHub API raw HTML (inspect for &lt;em&gt; tags = emphasis leak)</h2>
<pre>{html_mod.escape(github_html)}</pre>

</body>
</html>"""


def main():
    md_source = build_markdown()

    # Save test markdown for manual push if needed
    test_md_path = Path(__file__).parent.parent / "output" / "math_render_test.md"
    test_md_path.parent.mkdir(exist_ok=True)
    test_md_path.write_text(md_source, encoding="utf-8")
    print(f"Test markdown saved to: {test_md_path}")

    # Call GitHub API
    print("Calling GitHub API to render markdown...")
    try:
        github_html = call_github_api(md_source)
        print("✓ GitHub API response received.")
    except Exception as e:
        print(f"⚠ GitHub API error: {e}")
        github_html = (
            f"<p style='color:red'>GitHub API error: {html_mod.escape(str(e))}</p>"
            "<p>You can manually push <code>output/math_render_test.md</code> "
            "to the repo to test on GitHub.</p>"
        )

    # Generate comparison HTML
    output_html = Path(__file__).parent.parent / "output" / "math_render_test.html"
    full_html = generate_html(github_html, md_source)
    output_html.write_text(full_html, encoding="utf-8")
    print(f"Comparison HTML saved to: {output_html}")

    # Open in browser
    webbrowser.open(output_html.as_uri())
    print("Opened in browser. Compare the 3 panels to find compatible syntax.")


if __name__ == "__main__":
    main()
