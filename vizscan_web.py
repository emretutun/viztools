"""
viztools web arayuzu: yerel bir sunucu acar, tarayicida sayfayi gosterir.

  python vizscan_web.py            -> http://127.0.0.1:8765 (tarayici otomatik acilir)
  python vizscan_web.py --no-open  -> tarayiciyi acma

Yalnizca 127.0.0.1'i dinler ve yalnizca 127.0.0.1:6100'e (salt okunur) baglanir.
"""
import argparse
import glob
import json
import os
import sys
import threading
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vizengine import VizClient, VizCommandBlocked, VizError
from vizengine.template import build_scene_model, write_outputs, render_markdown
from vizengine.via import read_via, list_scenes, ViaError
from vizengine.gen_csharp import write_csharp
from vizengine.analiz import analiz_et, rapor as analiz_raporu
from vizengine import uygulama as U

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
SCENES_DIR = os.path.join(HERE, "scenes")
STATE_FILE = os.path.join(HERE, ".viztools_web.json")
PORT_ENGINE = 6100

_lock = threading.Lock()
STATE = {"model": None, "paths": {}, "scanning": False, "progress": [0, 0], "error": None, "analiz": None}
IS = {"calisiyor": False, "satirlar": [], "ok": None, "hedef": None, "cozum": None}


def _load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"recent": []}


def _save_state(st):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def _remember(path, scene):
    st = _load_state()
    rec = [r for r in st.get("recent", []) if not (r["path"] == path and r.get("scene") == scene)]
    rec.insert(0, {"path": path, "scene": scene})
    st["recent"] = rec[:10]
    _save_state(st)


def _cli():
    return VizClient("127.0.0.1", PORT_ENGINE)


def _public_model(model):
    m = dict(model)
    m.pop("raw", None)
    return m


def _finish(model, source):
    jp, mp = write_outputs(model, SCENES_DIR)
    cp = write_csharp(model, SCENES_DIR)
    an = analiz_et(model)
    ap = os.path.join(os.path.dirname(jp), os.path.splitext(os.path.basename(jp))[0] + ".analiz.md")
    with open(ap, "w", encoding="utf-8") as f:
        f.write(analiz_raporu(an))
    with _lock:
        STATE["model"] = model
        STATE["analiz"] = an
        STATE["paths"] = {"md": mp, "json": jp, "cs": cp, "dir": os.path.dirname(mp), "analiz": ap}
        STATE["scanning"] = False
        STATE["error"] = None


def _scan_async(layer, details):
    def prog(i, n):
        STATE["progress"] = [i, n]

    def work():
        try:
            with _cli() as c:
                model = build_scene_model(c, layer, details, progress=prog)
            _finish(model, "live")
        except Exception as e:  # noqa
            with _lock:
                STATE["scanning"] = False
                STATE["error"] = f"{e}"
    with _lock:
        STATE["scanning"] = True
        STATE["progress"] = [0, 0]
        STATE["error"] = None
    threading.Thread(target=work, daemon=True).start()


def _via_files():
    found = []
    for folder in (os.path.join(HERE, "samples"), os.path.expanduser("~/Desktop"), os.path.expanduser("~/Downloads")):
        for p in glob.glob(os.path.join(folder, "*.via")):
            found.append({"path": p, "name": os.path.basename(p), "size": os.path.getsize(p)})
    seen, out = set(), []
    for f in found:
        if f["path"].lower() not in seen:
            seen.add(f["path"].lower())
            out.append(f)
    return out


def _sahne_yolu_hatirla(ad, yol):
    st = _load_state()
    st.setdefault("sahne_yollari", {})[ad] = yol
    _save_state(st)


def _uretim_async(plan, hedef, guncelle, arayuz):
    def work():
        try:
            ok, satirlar = U.uygula(plan, hedef, STATE["paths"]["json"], guncelle=guncelle, arayuz=arayuz)
            with _lock:
                IS["satirlar"] += satirlar
                IS["ok"] = ok
        except Exception as e:  # noqa
            with _lock:
                IS["satirlar"].append(f"HATA: {e}")
                IS["ok"] = False
        with _lock:
            IS["calisiyor"] = False
            IS["cozum"] = U.cozum_dosyasi(hedef)
    with _lock:
        IS.update({"calisiyor": True, "satirlar": [("Guncelleniyor: " if guncelle else "Uretiliyor: ") + hedef],
                   "ok": None, "hedef": hedef, "cozum": None})
    threading.Thread(target=work, daemon=True).start()


def _taramalar():
    out = []
    for p in glob.glob(os.path.join(SCENES_DIR, "*", "*.json")):
        ad = os.path.splitext(os.path.basename(p))[0]
        if os.path.basename(os.path.dirname(p)) == ad:
            out.append({"path": p, "name": ad, "zaman": os.path.getmtime(p)})
    return sorted(out, key=lambda x: -x["zaman"])[:12]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # sessiz
        pass

    # ---- yardimcilar
    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, name, ctype):
        try:
            with open(os.path.join(WEB, name), "rb") as f:
                body = f.read()
        except OSError:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    # ---- GET
    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path in ("/", "/index.html"):
            return self._file("index.html", "text/html; charset=utf-8")
        if u.path == "/app.js":
            return self._file("app.js", "application/javascript; charset=utf-8")
        if u.path == "/uyg.js":
            return self._file("uyg.js", "application/javascript; charset=utf-8")
        if u.path == "/style.css":
            return self._file("style.css", "text/css; charset=utf-8")
        if u.path == "/api/status":
            info = {"engine": False, "layers": {}, "on_air": None}
            try:
                with _cli() as c:
                    info["engine"] = True
                    info["on_air"] = c.try_send("IS_ON_AIR GET")
                    for L in ("MAIN_SCENE", "FRONT_SCENE", "BACK_SCENE"):
                        info["layers"][L] = c.try_send(L + "*NAME GET")
            except OSError:
                pass
            with _lock:
                info.update({"scanning": STATE["scanning"], "progress": STATE["progress"], "error": STATE["error"],
                             "loaded": STATE["model"]["scene"] if STATE["model"] else None, "paths": STATE["paths"]})
            info["recent"] = _load_state().get("recent", [])
            info["via_files"] = _via_files()
            info["taramalar"] = _taramalar()
            return self._json(info)
        if u.path == "/api/model":
            with _lock:
                m = STATE["model"]
            return self._json({"model": _public_model(m) if m else None, "paths": STATE["paths"]})
        if u.path == "/api/via/scenes":
            path = (q.get("path") or [""])[0]
            try:
                return self._json({"scenes": list_scenes(path)})
            except (ViaError, OSError) as e:
                return self._json({"error": str(e)}, 400)
        if u.path == "/api/vizscript":
            with _lock:
                m = STATE["model"]
            if not m:
                return self._json({"error": "sahne yuklu degil"}, 400)
            md = render_markdown(m)
            vb = md.split("```vb")[1].split("```")[0].strip() if "```vb" in md else ""
            return self._json({"text": vb})
        if u.path == "/api/uygulama/analiz":
            with _lock:
                m, an = STATE["model"], STATE["analiz"]
            if not m:
                return self._json({"error": "sahne yuklu degil"}, 400)
            ad = m["scene"]["name"]
            return self._json({
                "sahne_adi": ad,
                "sahne_yolu": m["scene"].get("path") or _load_state().get("sahne_yollari", {}).get(ad, ""),
                "yol_engineden": bool(m["scene"].get("path")),
                "liste": U.kalemler(m, an),
                "sorular": an["sorular"],
                "uygulamalar": U.mevcut_uygulamalar(),
                "repos": U.REPOS})
        if u.path == "/api/uygulama/durum":
            with _lock:
                return self._json(dict(IS))
        if u.path == "/api/uygulama/ac":
            what, hedef = (q.get("what") or [""])[0], (q.get("hedef") or [""])[0]
            yol = U.cozum_dosyasi(hedef) if what == "cozum" else hedef
            if yol and os.path.exists(yol):
                os.startfile(yol)
                return self._json({"ok": True})
            return self._json({"error": "bulunamadi"}, 400)
        if u.path == "/api/open":
            what = (q.get("what") or [""])[0]
            p = STATE["paths"].get(what)
            if p and os.path.exists(p):
                os.startfile(p)
                return self._json({"ok": True})
            return self._json({"error": "dosya yok"}, 400)
        self.send_error(404)

    # ---- POST
    def do_POST(self):
        u = urlparse(self.path)
        data = self._body()
        if u.path == "/api/scan":
            if STATE["scanning"]:
                return self._json({"error": "tarama suruyor"}, 409)
            _scan_async(data.get("layer", "MAIN_SCENE"), bool(data.get("details", True)))
            return self._json({"ok": True})
        if u.path == "/api/via/load":
            path, scene = data.get("path", ""), data.get("scene") or None
            try:
                scenes = list_scenes(path)
                if len(scenes) > 1 and not scene:
                    return self._json({"choose": scenes})
                model = read_via(path, scene)
            except (ViaError, OSError) as e:
                return self._json({"error": str(e)}, 400)
            _finish(model, "via")
            _remember(path, scene)
            return self._json({"ok": True, "scene": model["scene"]})
        if u.path == "/api/uygulama/hedef":
            return self._json({"hedef": U.varsayilan_hedef(data.get("ad", "")), "namespace": U.namespace_yap(data.get("ad", ""))})
        if u.path == "/api/uygulama/kontrol":
            with _lock:
                m, an = STATE["model"], STATE["analiz"]
            eski = U.plan_oku(data.get("hedef", ""))
            if not m or not eski:
                return self._json({"error": "sahne yuklu degil ya da klasor viztools uygulamasi degil"}, 400)
            return self._json({"plan": {k: v for k, v in eski.items() if k not in U.PLAN_ALANLARI},
                               "liste": U.kalemler(m, an, eski)})
        if u.path == "/api/uygulama/uret":
            if IS["calisiyor"]:
                return self._json({"error": "uretim suruyor"}, 409)
            with _lock:
                m = STATE["model"]
            plan, hedef, guncelle = data.get("plan") or {}, os.path.abspath(data.get("hedef") or "."), bool(data.get("guncelle"))
            if not m:
                return self._json({"error": "sahne yuklu degil"}, 400)
            for alan in ("uygulama", "namespace", "sahne"):
                if not str(plan.get(alan, "")).strip():
                    return self._json({"error": f"'{alan}' bos"}, 400)
            if guncelle and not U.plan_oku(hedef):
                return self._json({"error": "Bu klasor viztools ile uretilmis bir uygulama degil (kumanda.json yok)"}, 400)
            if not guncelle and os.path.isdir(hedef) and os.listdir(hedef):
                return self._json({"error": "Hedef klasor bos degil. Mevcut uygulamayi guncellemek icin 'Mevcut uygulama'yi secin."}, 400)
            hatalar = U.dogrula(plan, m)
            if hatalar:
                return self._json({"error": "Plan sahneyle uyusmuyor: " + "; ".join(hatalar[:6])}, 400)
            _sahne_yolu_hatirla(m["scene"]["name"], plan["sahne"])
            eski = U.plan_oku(hedef) if guncelle else None
            if eski:
                plan["namespace"] = eski["namespace"]   # proje klasoru namespace adini tasir; degismez
            arayuz = bool(eski) and (bool(data.get("arayuz")) or U.kontrol_farki(eski, plan))
            _uretim_async(plan, hedef, guncelle, arayuz)
            return self._json({"ok": True})
        if u.path == "/api/tarama/load":
            path = os.path.abspath(data.get("path", ""))
            if os.path.dirname(os.path.dirname(path)) != os.path.abspath(SCENES_DIR):
                return self._json({"error": "yalnizca scenes klasorundeki taramalar"}, 400)
            try:
                with open(path, encoding="utf-8") as f:
                    model = json.load(f)
            except (OSError, ValueError) as e:
                return self._json({"error": str(e)}, 400)
            _finish(model, "tarama")
            return self._json({"ok": True, "scene": model["scene"]})
        if u.path == "/api/send":
            try:
                with _cli() as c:
                    return self._json({"result": c.send(data.get("command", "")) or "(bos cevap)"})
            except VizCommandBlocked as e:
                return self._json({"error": f"Reddedildi (salt okunur): {e}"}, 400)
            except VizError as e:
                return self._json({"error": f"Engine hatasi: {e}"}, 400)
            except OSError as e:
                return self._json({"error": f"Baglanti yok: {e}"}, 400)
        self.send_error(404)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    url = f"http://127.0.0.1:{a.port}/"
    print("viztools web:", url, "(kapatmak icin Ctrl+C)")
    if not a.no_open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
