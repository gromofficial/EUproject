#!/usr/bin/env python3
"""Consolă locală de administrare a pozelor site-ului 1000KM.
Rulează pe 127.0.0.1:8742 — servește site-ul + /admin pentru alegerea pozelor."""
import http.server, socketserver, json, os, io, hashlib, subprocess, urllib.parse
from PIL import Image, ImageOps

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
THUMBS = os.path.join(ROOT, "img", ".thumbs")
os.makedirs(THUMBS, exist_ok=True)

SOURCES = {
    "paris":        "/Volumes/GROM T7/Paris ",
    "milan":        "/Volumes/GROM T7/Milan ",
    "schiaparelli": os.path.join(ROOT, "img", "paris-recovered"),
    "haine":        "/Volumes/SECOND T7/Content pentru site grom /Commercials photo, haine ",
    "mbbfw":        "/Volumes/SECOND T7/2026/MBBFW",
}
# slot → (etichetă, dimensiune max export)
SLOTS = [
    ("danil",     "★ PORTRET DANIL", 1600),
    ("heronew",   "HERO", 1800),
    ("cityparis", "PARIS PANEL", 1600),
    ("citymilan", "MILAN PANEL", 1600),
    ("fwwide",    "FW STRIP 1", 1800),
    ("fwgloves",  "FW STRIP 2 (+ SOCIAL 3)", 1400),
    ("fwrunway",  "FW STRIP 3", 1400),
    ("fwsilver",  "FW STRIP 4", 1400),
    ("fwcream",   "FW STRIP 5 (+ CLIENTS)", 1400),
    ("fwprofile", "FW STRIP 6", 1400),
    ("grey2",     "WORK 01 (+ SOCIAL 1)", 1400),
    ("glasses",   "WORK 02", 1400),
    ("carpet1",   "WORK 03", 1400),
    ("suit1",     "WORK 04", 1400),
    ("golf1",     "WORK 05", 1400),
    ("trench",    "WORK 06 (+ SOCIAL 2)", 1400),
    ("carpet2",   "WORK 07", 1400),
    ("ring",      "WORK 08", 1400),
    ("grey3",     "WORK 09", 1400),
    ("golf2",     "WORK 10", 1400),
    ("suit2",     "WORK 11", 1400),
    ("grey1",     "WORK 12", 1400),
]
_listcache = {}

# navigare liberă: doar sub aceste rădăcini (securitate localhost)
BROWSE_ROOTS = ["/Volumes", os.path.expanduser("~/Downloads"), os.path.expanduser("~/Desktop"), os.path.expanduser("~/Pictures"), ROOT]

def safe_path(p):
    rp = os.path.realpath(p)
    for r in BROWSE_ROOTS:
        rr = os.path.realpath(r)
        if rp == rr or rp.startswith(rr + os.sep):
            return rp
    return None

def list_source(key):
    root = SOURCES.get(key)
    if not root or not os.path.isdir(root):
        return None
    if key in _listcache:
        return _listcache[key]
    out = []
    for dp, dn, fns in os.walk(root):
        if "@eaDir" in dp or "/.": pass
        if "@eaDir" in dp: continue
        for f in sorted(fns):
            if f.startswith("."): continue
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                out.append(os.path.relpath(os.path.join(dp, f), root))
    _listcache[key] = out
    return out

def thumb_for(key, rel):
    src = os.path.join(SOURCES[key], rel)
    h = hashlib.md5((key + "|" + rel).encode()).hexdigest()
    tp = os.path.join(THUMBS, h + ".jpg")
    if not os.path.exists(tp):
        im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
        im.thumbnail((360, 360), Image.LANCZOS)
        im.save(tp, quality=72)
    return tp

class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path == "/admin":
            self.path = "/admin.html"
            return super().do_GET()
        if u.path == "/api/sources":
            return self._json({k: (list_source(k) is not None) for k in SOURCES})
        if u.path == "/api/slots":
            return self._json([{"slot": s, "label": l, "dim": d} for s, l, d in SLOTS])
        if u.path == "/api/browse":
            p = q.get("path", ["/Volumes"])[0]
            rp = safe_path(p)
            if not rp or not os.path.isdir(rp):
                return self._json({"error": "folder inexistent sau nepermis"}, 404)
            dirs, imgs = [], []
            try:
                for e in sorted(os.listdir(rp)):
                    if e.startswith(".") or e == "@eaDir" or e == "@tmp": continue
                    fp = os.path.join(rp, e)
                    if os.path.isdir(fp): dirs.append(e)
                    elif e.lower().endswith((".jpg", ".jpeg", ".png")): imgs.append(e)
            except PermissionError:
                return self._json({"error": "fără permisiune"}, 403)
            return self._json({"path": rp, "dirs": dirs, "images": imgs})
        if u.path == "/api/list":
            key = q.get("src", [""])[0]
            files = list_source(key)
            if files is None: return self._json({"error": "sursa nu e montată"}, 404)
            return self._json(files)
        if u.path == "/thumb":
            key = q.get("src", [""])[0]; rel = q.get("id", [""])[0]
            if key == "__slot__":
                tp = os.path.join(ROOT, "img", "final", os.path.basename(rel) + ".jpg")
                if not os.path.exists(tp): return self._json({"error": "n/a"}, 404)
                im = Image.open(tp).convert("RGB"); im.thumbnail((360, 360)); buf = io.BytesIO(); im.save(buf, "JPEG", quality=70)
                b = buf.getvalue()
            elif key == "__path__":
                p = safe_path(rel)
                if not p or not os.path.isfile(p): return self._json({"error": "cale nepermisă"}, 403)
                h = hashlib.md5(("P|" + p + str(os.path.getmtime(p))).encode()).hexdigest()
                tp = os.path.join(THUMBS, h + ".jpg")
                try:
                    if not os.path.exists(tp):
                        im = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
                        im.thumbnail((360, 360), Image.LANCZOS)
                        im.save(tp, quality=72)
                    b = open(tp, "rb").read()
                except Exception as e: return self._json({"error": str(e)}, 500)
            else:
                if key not in SOURCES: return self._json({"error": "?"}, 404)
                try: b = open(thumb_for(key, rel), "rb").read()
                except Exception as e: return self._json({"error": str(e)}, 500)
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "max-age=86400")
            self.end_headers()
            self.wfile.write(b)
            return
        return super().do_GET()

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/api/assign":
            ln = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(ln))
            slot, key, rel = body.get("slot"), body.get("src"), body.get("id")
            dims = {s: d for s, l, d in SLOTS}
            if slot not in dims:
                return self._json({"error": "slot invalid"}, 400)
            if key == "__path__":
                src = safe_path(rel)
                if not src: return self._json({"error": "cale nepermisă"}, 403)
            elif key in SOURCES:
                src = os.path.join(SOURCES[key], rel)
            else:
                return self._json({"error": "sursă invalidă"}, 400)
            try:
                im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
                im.thumbnail((dims[slot], dims[slot]), Image.LANCZOS)
                out = os.path.join(ROOT, "img", "final", slot + ".jpg")
                im.save(out, quality=68, progressive=True, optimize=True)
                r = subprocess.run(["python3", "build.py"], capture_output=True, text=True, cwd=ROOT)
                if r.returncode != 0:
                    return self._json({"error": "build a eșuat: " + r.stderr[-300:]}, 500)
                return self._json({"ok": True, "size": os.path.getsize(out) // 1024})
            except Exception as e:
                return self._json({"error": str(e)}, 500)
        return self._json({"error": "?"}, 404)

socketserver.ThreadingTCPServer.allow_reuse_address = True
with socketserver.ThreadingTCPServer(("127.0.0.1", 8742), H) as httpd:
    print("admin pe http://localhost:8742/admin")
    httpd.serve_forever()
