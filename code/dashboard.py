"""
Ghostinel - Local Web Dashboard Server.
Launches a lightweight local server to explore all 518 cases, their audit status,
discovered risks, and step-by-step plans in the browser.

Usage:
    python code/dashboard.py
"""
import http.server
import socketserver
import webbrowser
import os
import sys

PORT = 8000
DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)


def main():
    if not os.path.exists(os.path.join(DIRECTORY, "index.html")):
        print("Building dashboard first...")
        import subprocess
        subprocess.run([sys.executable, "code/build_web_dashboard.py"], check=True)

    url = f"http://localhost:{PORT}/"
    print("=" * 60)
    print("        🚀 GHOSTINEL WEB DASHBOARD SERVER")
    print("=" * 60)
    print(f"  • Serving dashboard at: {url}")
    print(f"  • Local directory:      {DIRECTORY}")
    print("  • Press Ctrl+C in terminal to stop server.")
    print("=" * 60)

    try:
        webbrowser.open(url)
    except Exception:
        pass

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")


if __name__ == "__main__":
    main()
