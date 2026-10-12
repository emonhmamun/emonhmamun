#!/usr/bin/env python3
""" Local live-preview of the profile README.

Serves a GitHub-dark styled render of README.md so every badge, image,
table and <details> block can be visually verified before pushing.
Local repo assets are served from disk; raw.githubusercontent URLs that
point at this repo are rewritten to the local server so you always see
the current checkout. External services (shields, skillicons, vercel…)
load straight from the internet in your browser.

Usage: python3 tools/preview.py [port]
"""

import http.server
import os
import socketserver
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000

PAGE = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>emonhmamun — profile README preview</title>
<script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>
<style>
  :root{color-scheme:dark}
  body{margin:0;background:#0d1117;color:#c9d1d9;
       font-family:-apple-system,'Segoe UI',Helvetica,Arial,sans-serif}
  header{position:sticky;top:0;z-index:9;background:#161b22ee;
       border-bottom:1px solid #30363d;padding:10px 22px;display:flex;
       justify-content:space-between;align-items:center}
  header b{color:#A855F7}
  header span{color:#22D3EE;font-size:12px}
  main{max-width:1012px;margin:0 auto;padding:34px 28px 90px;
       background:#0d1117}
  img{max-width:100%}
  h1,h2,h3,h4{border-bottom:1px solid #21262d;padding-bottom:.3em}
  a{color:#58a6ff}
  table{border-collapse:collapse;margin:12px auto}
  td,th{border:1px solid #30363d;padding:6px 10px}
  pre,code{background:#161b22;border-radius:6px}
  pre{padding:14px;overflow-x:auto}
  code{padding:2px 5px;font-family:ui-monospace,'JetBrains Mono',monospace}
  pre code{padding:0;background:none}
  details{background:#161b22;border:1px solid #30363d;border-radius:6px;
       padding:8px 14px;margin:8px 0}
  summary{cursor:pointer;font-weight:600}
  blockquote{border-left:3px solid #A855F7;margin:8px 0;padding:4px 14px;
       color:#8b949e;background:#161b2266}
  hr{border:0;border-top:2px solid #21262d;margin:26px 0}
  .md-loading{color:#8b949e;padding:40px;text-align:center}
</style></head><body>
<header><b>🌌 emonhmamun — profile preview</b>
<span>local checkout · external badges load live</span></header>
<main id="out"><div class="md-loading">rendering README.md …</div></main>
<script>
const RAW = /https:\\/\\/raw\\.githubusercontent\\.com\\/emonhmamun\\/emonhmamun\\/[^/]+\\//g;
fetch('/README.md').then(r => r.text()).then(md => {
  md = md.replace(RAW, '/');            // serve repo images from this checkout
  marked.setOptions({gfm:true, breaks:false});
  document.getElementById('out').innerHTML = marked.parse(md);
});
</script></body></html>
"""


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            body = PAGE.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

    def log_message(self, *a):
        pass


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == '__main__':
    with Server(('0.0.0.0', PORT), Handler) as httpd:
        print(f'preview on http://0.0.0.0:{PORT}/')
        httpd.serve_forever()
