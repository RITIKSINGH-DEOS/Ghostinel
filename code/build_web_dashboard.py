"""
Builds a standalone interactive web dashboard into docs/index.html
Can be opened directly in any browser (file://) or hosted on GitHub Pages!
"""
import os
import sys
import csv
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def build_dashboard():
    os.makedirs("docs", exist_ok=True)
    
    # 1. Read requests
    requests = {}
    with open("dataset/deletion_requests.csv", mode="r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            requests[r["case_id"]] = r

    # 2. Read output.csv
    outputs = {}
    with open("output.csv", mode="r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            outputs[r["case_id"]] = {
                "status": r["deletion_status"],
                "steps": json.loads(r["steps_json"])
            }

    # 3. Read identities
    users = {}
    with open("dataset/user_identities.csv", mode="r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            users[r["email"].lower()] = {
                "user_id": r["user_id"],
                "name": r["name"],
                "phone": r["phone"]
            }

    # Build combined cases list
    cases_data = []
    for cid, req in sorted(requests.items(), key=lambda x: int(x[0].split("_")[1]) if "_" in x[0] else 0):
        em = req["email"].lower()
        u = users.get(em, {})
        out = outputs.get(cid, {"status": "UNKNOWN", "steps": []})
        cases_data.append({
            "case_id": cid,
            "email": req["email"],
            "user_id": u.get("user_id", "Unknown"),
            "name": u.get("name", "Unknown"),
            "requested_at": req["requested_at"],
            "reported_status": req["reported_status"],
            "reported_at": req["reported_at"],
            "audit_at": req["audit_at"],
            "request_text": req["request_text"],
            "status": out["status"],
            "steps": out["steps"],
            "step_count": len(out["steps"])
        })

    cases_json = json.dumps(cases_data, separators=(",", ":"))

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ghostinel — AI Deletion Audit Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #0b0f19;
            --surface: #111827;
            --surface-hover: #1f2937;
            --border: #374151;
            --text-main: #f9fafb;
            --text-muted: #9ca3af;
            --primary: #3b82f6;
            --primary-glow: rgba(59, 130, 246, 0.2);
            --complete: #10b981;
            --complete-bg: rgba(16, 185, 129, 0.15);
            --incomplete: #ef4444;
            --incomplete-bg: rgba(239, 68, 68, 0.15);
            --na: #8b5cf6;
            --na-bg: rgba(139, 92, 246, 0.15);
            --finding: #f59e0b;
            --finding-bg: rgba(245, 158, 11, 0.15);
            --remediation: #3b82f6;
            --remediation-bg: rgba(59, 130, 246, 0.15);
            --verification: #10b981;
            --verification-bg: rgba(16, 185, 129, 0.15);
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background: var(--bg);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        header {{
            background: rgba(17, 24, 39, 0.8);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border);
            padding: 1rem 2rem;
            position: sticky;
            top: 0;
            z-index: 40;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .brand {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        .logo-icon {{
            width: 36px;
            height: 36px;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
            font-weight: 700;
            box-shadow: 0 0 15px var(--primary-glow);
        }}
        .brand-title h1 {{ font-size: 1.25rem; font-weight: 700; }}
        .brand-title p {{ font-size: 0.75rem; color: var(--text-muted); }}
        .header-links {{
            display: flex;
            gap: 1rem;
        }}
        .btn-link {{
            background: var(--surface);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 0.5rem 1rem;
            border-radius: 6px;
            text-decoration: none;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            transition: all 0.2s;
        }}
        .btn-link:hover {{
            background: var(--surface-hover);
            border-color: var(--primary);
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
            width: 100%;
            flex: 1;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .metric-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 1.25rem;
            position: relative;
            overflow: hidden;
        }}
        .metric-card::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
        }}
        .card-total::before {{ background: var(--primary); }}
        .card-complete::before {{ background: var(--complete); }}
        .card-incomplete::before {{ background: var(--incomplete); }}
        .card-na::before {{ background: var(--na); }}
        .metric-title {{ font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }}
        .metric-val {{ font-size: 2rem; font-weight: 700; margin: 0.5rem 0 0.25rem; }}
        .metric-sub {{ font-size: 0.8rem; color: var(--text-muted); }}
        
        .controls-row {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
        }}
        .search-box {{
            flex: 1;
            min-width: 300px;
            position: relative;
        }}
        .search-box input {{
            width: 100%;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.75rem 1rem 0.75rem 2.5rem;
            color: var(--text-main);
            font-size: 0.9rem;
            outline: none;
            transition: border-color 0.2s;
        }}
        .search-box input:focus {{
            border-color: var(--primary);
            box-shadow: 0 0 0 2px var(--primary-glow);
        }}
        .search-icon {{
            position: absolute;
            left: 0.85rem;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
            font-size: 0.9rem;
        }}
        .filter-group {{
            display: flex;
            gap: 0.5rem;
            background: var(--surface);
            padding: 0.35rem;
            border-radius: 8px;
            border: 1px solid var(--border);
        }}
        .filter-btn {{
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 0.4rem 0.9rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
            font-weight: 500;
            transition: all 0.2s;
        }}
        .filter-btn.active {{
            background: var(--primary);
            color: #fff;
        }}
        .table-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 10px;
            overflow: hidden;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.875rem;
            text-align: left;
        }}
        th {{
            background: rgba(31, 41, 55, 0.5);
            padding: 0.9rem 1.25rem;
            font-weight: 600;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border);
        }}
        td {{
            padding: 0.9rem 1.25rem;
            border-bottom: 1px solid rgba(55, 65, 81, 0.4);
        }}
        tr:hover td {{
            background: var(--surface-hover);
            cursor: pointer;
        }}
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.6rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.025em;
        }}
        .badge-COMPLETE {{ background: var(--complete-bg); color: var(--complete); border: 1px solid rgba(16, 185, 129, 0.3); }}
        .badge-INCOMPLETE {{ background: var(--incomplete-bg); color: var(--incomplete); border: 1px solid rgba(239, 68, 68, 0.3); }}
        .badge-NOT_APPLICABLE {{ background: var(--na-bg); color: var(--na); border: 1px solid rgba(139, 92, 246, 0.3); }}
        .badge-FINDING {{ background: var(--finding-bg); color: var(--finding); }}
        .badge-REMEDIATION {{ background: var(--remediation-bg); color: var(--remediation); }}
        .badge-VERIFICATION {{ background: var(--verification-bg); color: var(--verification); }}
        .mono {{ font-family: 'JetBrains Mono', monospace; }}

        /* Modal Styles */
        .modal-overlay {{
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(4px);
            z-index: 100;
            display: none;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
        }}
        .modal-overlay.open {{ display: flex; }}
        .modal-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            max-width: 900px;
            width: 100%;
            max-height: 90vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
            animation: modalPop 0.2s ease-out;
        }}
        @keyframes modalPop {{
            from {{ transform: scale(0.95); opacity: 0; }}
            to {{ transform: scale(1); opacity: 1; }}
        }}
        .modal-header {{
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .modal-close {{
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-size: 1.5rem;
            cursor: pointer;
            padding: 0.25rem;
            line-height: 1;
        }}
        .modal-close:hover {{ color: #fff; }}
        .modal-body {{
            padding: 1.5rem;
            overflow-y: auto;
            flex: 1;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1rem;
            background: rgba(0,0,0,0.25);
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(255,255,255,0.05);
        }}
        .info-item label {{ font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; }}
        .info-item div {{ font-size: 0.9rem; margin-top: 0.2rem; font-weight: 500; }}
        .steps-table {{
            margin-top: 1rem;
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow: hidden;
        }}
        .empty-steps {{
            padding: 2rem;
            text-align: center;
            color: var(--text-muted);
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
        }}
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <div class="logo-icon">G</div>
            <div class="brand-title">
                <h1>Ghostinel Deletion Audit Dashboard</h1>
                <p>AI Audit Agent for HackerRank Orchestrate (October 2026)</p>
            </div>
        </div>
        <div class="header-links">
            <a href="https://github.com/RITIKSINGH-DEOS/Ghostinel" target="_blank" class="btn-link">
                GitHub Repo
            </a>
            <a href="https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists" target="_blank" class="btn-link">
                Contest Page
            </a>
        </div>
    </header>

    <div class="container">
        <!-- Metrics Cards -->
        <div class="metrics-grid">
            <div class="metric-card card-total">
                <div class="metric-title">Total Deletion Requests</div>
                <div class="metric-val" id="metric-total">518</div>
                <div class="metric-sub">100% Cases Audited</div>
            </div>
            <div class="metric-card card-complete">
                <div class="metric-title">Complete Deletions</div>
                <div class="metric-val" id="metric-complete" style="color: var(--complete);">178</div>
                <div class="metric-sub">34.36% Verified Clean</div>
            </div>
            <div class="metric-card card-incomplete">
                <div class="metric-title">Incomplete Deletions</div>
                <div class="metric-val" id="metric-incomplete" style="color: var(--incomplete);">336</div>
                <div class="metric-sub">64.86% Ghost Data / Risks Detected</div>
            </div>
            <div class="metric-card card-na">
                <div class="metric-title">Not Applicable</div>
                <div class="metric-val" id="metric-na" style="color: var(--na);">4</div>
                <div class="metric-sub">0.77% Explicit Retention Requests</div>
            </div>
        </div>

        <!-- Controls -->
        <div class="controls-row">
            <div class="search-box">
                <span class="search-icon">🔍</span>
                <input type="text" id="search-input" placeholder="Search by case_id, email, user_id, or name...">
            </div>
            <div class="filter-group">
                <button class="filter-btn active" onclick="setFilter('ALL')">All (518)</button>
                <button class="filter-btn" onclick="setFilter('COMPLETE')">Complete (178)</button>
                <button class="filter-btn" onclick="setFilter('INCOMPLETE')">Incomplete (336)</button>
                <button class="filter-btn" onclick="setFilter('NOT_APPLICABLE')">Not Applicable (4)</button>
            </div>
        </div>

        <!-- Main Table -->
        <div class="table-card">
            <table>
                <thead>
                    <tr>
                        <th style="width: 110px;">Case ID</th>
                        <th style="width: 140px;">Status</th>
                        <th>User Info</th>
                        <th>Request Date</th>
                        <th>Reported Claim</th>
                        <th style="width: 90px; text-align: center;">Steps</th>
                    </tr>
                </thead>
                <tbody id="cases-tbody">
                    <!-- Populated by JavaScript -->
                </tbody>
            </table>
        </div>
    </div>

    <!-- Modal for Detailed Steps -->
    <div class="modal-overlay" id="case-modal">
        <div class="modal-card">
            <div class="modal-header">
                <div>
                    <h2 id="modal-case-id" class="mono" style="font-size: 1.25rem;">case_xx</h2>
                    <span id="modal-status-badge" class="badge">STATUS</span>
                </div>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="info-grid">
                    <div class="info-item">
                        <label>User Name & ID</label>
                        <div id="modal-user-info">-</div>
                    </div>
                    <div class="info-item">
                        <label>Email Address</label>
                        <div id="modal-email" class="mono">-</div>
                    </div>
                    <div class="info-item">
                        <label>Requested Timestamp</label>
                        <div id="modal-requested">-</div>
                    </div>
                    <div class="info-item">
                        <label>Reported Claim</label>
                        <div id="modal-reported">-</div>
                    </div>
                    <div class="info-item" style="grid-column: span 2;">
                        <label>Request Text</label>
                        <div id="modal-req-text" style="font-style: italic; color: #d1d5db; margin-top: 0.35rem;">"-"</div>
                    </div>
                </div>

                <h3 style="font-size: 1rem; margin-bottom: 0.75rem; display: flex; justify-content: space-between; align-items: center;">
                    <span>Audit Pipeline Execution Plan</span>
                    <span id="modal-step-count" style="font-size: 0.8rem; font-weight: normal; color: var(--text-muted);">-</span>
                </h3>

                <div id="modal-steps-container">
                    <!-- Steps table or empty state -->
                </div>
            </div>
        </div>
    </div>

    <script>
        const cases = {cases_json};
        let currentFilter = 'ALL';
        let searchQuery = '';

        function renderTable() {{
            const tbody = document.getElementById('cases-tbody');
            tbody.innerHTML = '';

            const filtered = cases.filter(c => {{
                const matchFilter = (currentFilter === 'ALL' || c.status === currentFilter);
                const query = searchQuery.toLowerCase();
                const matchQuery = !query || 
                    c.case_id.toLowerCase().includes(query) ||
                    c.email.toLowerCase().includes(query) ||
                    c.user_id.toLowerCase().includes(query) ||
                    c.name.toLowerCase().includes(query);
                return matchFilter && matchQuery;
            }});

            if (filtered.length === 0) {{
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 3rem; color: var(--text-muted);">No matching cases found.</td></tr>';
                return;
            }}

            filtered.forEach(c => {{
                const tr = document.createElement('tr');
                tr.onclick = () => openModal(c);
                tr.innerHTML = `
                    <td class="mono" style="font-weight: 600; color: var(--primary);">${{c.case_id}}</td>
                    <td><span class="badge badge-${{c.status}}">${{c.status}}</span></td>
                    <td>
                        <div style="font-weight: 500;">${{c.name !== 'Unknown' ? c.name : c.email}}</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted);" class="mono">${{c.email}} • ${{c.user_id}}</div>
                    </td>
                    <td style="color: var(--text-muted); font-size: 0.8rem;">${{c.requested_at.replace('T', ' ').replace('Z', '')}}</td>
                    <td><span style="font-size: 0.8rem;">${{c.reported_status}}</span></td>
                    <td style="text-align: center; font-weight: 600;" class="mono">${{c.step_count}}</td>
                `;
                tbody.appendChild(tr);
            }});
        }}

        function setFilter(filter) {{
            currentFilter = filter;
            document.querySelectorAll('.filter-btn').forEach(btn => {{
                btn.classList.toggle('active', btn.textContent.startsWith(filter === 'ALL' ? 'All' : (filter === 'COMPLETE' ? 'Complete' : (filter === 'INCOMPLETE' ? 'Incomplete' : 'Not'))));
            }});
            renderTable();
        }}

        document.getElementById('search-input').addEventListener('input', (e) => {{
            searchQuery = e.target.value.trim();
            renderTable();
        }});

        function openModal(c) {{
            document.getElementById('modal-case-id').textContent = c.case_id;
            const badge = document.getElementById('modal-status-badge');
            badge.className = `badge badge-${{c.status}}`;
            badge.textContent = c.status;

            document.getElementById('modal-user-info').textContent = `${{c.name}} (${{c.user_id}})`;
            document.getElementById('modal-email').textContent = c.email;
            document.getElementById('modal-requested').textContent = c.requested_at;
            document.getElementById('modal-reported').textContent = `${{c.reported_status}} at ${{c.reported_at}}`;
            document.getElementById('modal-req-text').textContent = `"${{c.request_text}}"`;
            document.getElementById('modal-step-count').textContent = `${{c.step_count}} steps generated`;

            const container = document.getElementById('modal-steps-container');
            if (c.steps.length === 0) {{
                container.innerHTML = '<div class="empty-steps">No steps required. User explicitly requested account retention or non-deletion service.</div>';
            }} else {{
                let tableHtml = `
                    <div class="steps-table">
                        <table>
                            <thead>
                                <tr>
                                    <th style="width: 50px;">#</th>
                                    <th style="width: 120px;">Phase</th>
                                    <th>Operation</th>
                                    <th>System & Resource</th>
                                    <th style="width: 100px;">State</th>
                                    <th>Evidence Cited</th>
                                </tr>
                            </thead>
                            <tbody>
                `;
                c.steps.forEach(s => {{
                    tableHtml += `
                        <tr>
                            <td class="mono">${{s.step_no}}</td>
                            <td><span class="badge badge-${{s.phase}}">${{s.phase}}</span></td>
                            <td class="mono" style="font-size: 0.8rem; color: #60a5fa;">${{s.operation}}</td>
                            <td>
                                <div style="font-weight: 500;">${{s.system_id}}</div>
                                <div class="mono" style="font-size: 0.75rem; color: var(--text-muted);">${{s.resource_id}}</div>
                            </td>
                            <td><span class="mono" style="font-size: 0.8rem;">${{s.state}}</span></td>
                            <td class="mono" style="font-size: 0.8rem; color: ${{s.evidence_id ? '#34d399' : 'var(--text-muted)'}};">${{s.evidence_id || '—'}}</td>
                        </tr>
                    `;
                }});
                tableHtml += '</tbody></table></div>';
                container.innerHTML = tableHtml;
            }}

            document.getElementById('case-modal').classList.add('open');
        }}

        function closeModal() {{
            document.getElementById('case-modal').classList.remove('open');
        }}

        document.getElementById('case-modal').addEventListener('click', (e) => {{
            if (e.target.id === 'case-modal') closeModal();
        }});

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closeModal();
        }});

        // Initial render
        renderTable();
    </script>
</body>
</html>
"""

    output_path = "docs/index.html"
    with open(output_path, mode="w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Successfully generated standalone dashboard at {output_path} ({len(html_content):,} bytes)!")


if __name__ == "__main__":
    build_dashboard()
