# Canvas TV – lokální server (YouTube přes yt-dlp + proxy streamů + tunel Cloudflare)
import http.server, socketserver, urllib.request, urllib.parse, json, subprocess, threading
import os, re, sys, time, secrets, ssl

PORT = 8765
DIR = os.path.dirname(os.path.abspath(__file__))
KEYF = os.path.join(DIR, 'key.txt')
if not os.path.exists(KEYF):
    open(KEYF, 'w').write(secrets.token_urlsafe(9))
KEY = open(KEYF).read().strip()
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36'
CACHE = {}  # id -> (čas, data)
CTX = ssl.create_default_context()

def yt_info(vid):
    c = CACHE.get(vid)
    if c and time.time() - c[0] < 1800:
        return c[1]
    url = 'https://www.youtube.com/watch?v=' + vid
    cmd = [os.path.join(DIR, 'yt-dlp.exe'), '--no-playlist', '--no-warnings',
           '-f', 'b[vcodec!=none][acodec!=none][ext=mp4]/b[vcodec!=none][acodec!=none]',
           '--print', 'title', '--print', 'urls', url]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=90,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    lines = [l for l in p.stdout.splitlines() if l.strip()]
    if p.returncode != 0 or len(lines) < 2:
        raise RuntimeError((p.stderr or 'yt-dlp selhal').strip().splitlines()[-1][:300])
    data = {'title': lines[0], 'url': lines[1]}
    CACHE[vid] = (time.time(), data)
    return data

def wrap(u):
    return '/p?key=' + KEY + '&u=' + urllib.parse.quote(u, safe='')

def rewrite_m3u8(text, base):
    out = []
    for line in text.splitlines():
        s = line.strip()
        if s and not s.startswith('#'):
            out.append(wrap(urllib.parse.urljoin(base, s)))
        elif 'URI="' in s:
            out.append(re.sub(r'URI="([^"]+)"', lambda m: 'URI="' + wrap(urllib.parse.urljoin(base, m.group(1))) + '"', line))
        else:
            out.append(line)
    return '\n'.join(out)

class H(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self, *a): pass
    def cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Range')
        self.send_header('Access-Control-Expose-Headers', 'Content-Length, Content-Range')
    def send(self, code, body, ctype='application/json; charset=utf-8'):
        if isinstance(body, str): body = body.encode('utf-8')
        self.send_response(code); self.cors()
        self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def do_OPTIONS(self):
        self.send_response(204); self.cors(); self.send_header('Content-Length', '0'); self.end_headers()
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = dict(urllib.parse.parse_qsl(u.query))
        if u.path in ('/', '/index.html'):
            return self.send(200, open(os.path.join(DIR, 'index.html'), 'rb').read(), 'text/html; charset=utf-8')
        if q.get('key') != KEY:
            return self.send(403, '{"error":"spatny klic"}')
        try:
            if u.path == '/ping':
                return self.send(200, '{"ok":true}')
            if u.path == '/yt':
                d = yt_info(q.get('id', ''))
                return self.send(200, json.dumps({'title': d['title'], 'path': wrap(d['url'])}))
            if u.path == '/p':
                return self.proxy(q['u'])
            self.send(404, '{"error":"nenalezeno"}')
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as e:
            try: self.send(502, json.dumps({'error': str(e)}))
            except Exception: pass
    def proxy(self, target):
        hdr = {'User-Agent': UA}
        if self.headers.get('Range'): hdr['Range'] = self.headers['Range']
        r = urllib.request.urlopen(urllib.request.Request(target, headers=hdr), timeout=30, context=CTX)
        ct = r.headers.get('Content-Type', 'application/octet-stream')
        if 'mpegurl' in ct.lower() or urllib.parse.urlparse(r.geturl()).path.endswith('.m3u8'):
            return self.send(200, rewrite_m3u8(r.read().decode('utf-8', 'replace'), r.geturl()), 'application/vnd.apple.mpegurl')
        self.send_response(r.status); self.cors()
        for h in ('Content-Type', 'Content-Length', 'Content-Range', 'Accept-Ranges'):
            if r.headers.get(h): self.send_header(h, r.headers[h])
        if not r.headers.get('Content-Length'): self.send_header('Connection', 'close')
        self.end_headers()
        while True:
            chunk = r.read(65536)
            if not chunk: break
            self.wfile.write(chunk)
        if not r.headers.get('Content-Length'): self.close_connection = True

class S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True; allow_reuse_address = True

def tunnel():
    exe = os.path.join(DIR, 'cloudflared.exe')
    while True:
        p = subprocess.Popen([exe, 'tunnel', '--no-autoupdate', '--url', 'http://localhost:%d' % PORT],
                             stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        for line in p.stderr:
            m = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', line)
            if m:
                link = m.group(0) + '/?key=' + KEY
                open(os.path.join(DIR, 'odkaz.txt'), 'w').write(link + '\n')
                print('\n' + '=' * 70 + '\n  OTEVRI V PROHLIZECI (kdekoli):\n\n  ' + link + '\n' + '=' * 70 + '\n', flush=True)
        p.wait(); print('Tunel spadl, spoustim znovu...', flush=True); time.sleep(5)

if __name__ == '__main__':
    print('Canvas TV server bezi na http://localhost:%d/?key=%s' % (PORT, KEY), flush=True)
    threading.Thread(target=tunnel, daemon=True).start()
    S(('0.0.0.0', PORT), H).serve_forever()
