"""
Viz Engine MCP sunucusu (salt okunur, yalnizca 127.0.0.1).

Claude Code'a baglamak icin .mcp.json:
  { "mcpServers": { "vizengine": { "command": "python", "args": ["<bu dosyanin tam yolu>"] } } }
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp.server.mcpserver import MCPServer

from vizengine import VizClient, VizCommandBlocked, VizError
from vizengine.parse import parse_tree, flatten
from vizengine.template import build_scene_model, render_markdown, write_outputs

PORT = int(os.environ.get("VIZ_PORT", "6100"))
OUT_DIR = os.environ.get("VIZ_SCENES_DIR",
                         os.path.join(os.path.dirname(os.path.abspath(__file__)), "scenes"))

server = MCPServer(
    "vizengine",
    description="Yerel Viz Engine'i (127.0.0.1:6100) SALT OKUNUR sorgular. "
                "Sahneyi, Graphic Hub'i veya engine durumunu degistiren hicbir komut gondermez.",
)


def _cli() -> VizClient:
    return VizClient("127.0.0.1", PORT)


def _errors(fn):
    """Hatalari metin olarak dondur (MCP istemcisi exception yerine aciklama gorsun)."""
    import functools

    @functools.wraps(fn)
    def wrapped(*a, **k):
        try:
            return fn(*a, **k)
        except VizCommandBlocked as e:
            return f"REDDEDILDI (salt okunur kural): {e}"
        except VizError as e:
            return f"ENGINE HATASI: {e}"
        except OSError as e:
            return f"BAGLANTI HATASI: {e} (Viz Engine 127.0.0.1:{PORT} calisiyor mu?)"
    return wrapped


@server.tool()
@_errors
def viz_status() -> str:
    """Engine erisilebilir mi, on-air mi, katmanlarda hangi sahneler yuklu."""
    with _cli() as c:
        lines = [f"engine 127.0.0.1:{PORT} OK", f"on_air={c.try_send('IS_ON_AIR GET')}"]
        for layer in ("MAIN_SCENE", "FRONT_SCENE", "BACK_SCENE"):
            lines.append(f"{layer}: {c.try_send(layer + '*NAME GET') or '(bos)'}")
        return "\n".join(lines)


@server.tool()
@_errors
def viz_send(command: str) -> str:
    """Ham komut gonderir. YALNIZCA GET / GET_* / IS_* fiilleri kabul edilir; SET, START, LOAD vb. reddedilir.
    Ornek: 'MAIN_SCENE*TREE*$baslik*GEOM*TEXT GET'"""
    with _cli() as c:
        return c.send(command) or "(bos cevap)"


@server.tool()
@_errors
def viz_tree(layer: str = "MAIN_SCENE") -> str:
    """Katmandaki sahnenin container agacini girintili liste olarak verir ($isim$yolu, #id).
    Aktiflik/text icin viz_container veya viz_scene_dump(details=True)."""
    with _cli() as c:
        roots = parse_tree(c.tree_raw(layer))
    if not roots:
        return "(agac bos: katmanda sahne yok veya sahne bos)"
    out = []
    for n in flatten(roots):
        out.append(f"{'  ' * n.depth}{n.name}  {n.name_path}  #{n.id}")
    return "\n".join(out)


@server.tool()
@_errors
def viz_stage(layer: str = "MAIN_SCENE") -> str:
    """Stage'deki director'lari, alt director'lari ve her birinin animasyon uyguladigi container/kanallari verir.
    Kapali (expand edilmemis) dallar icin uyari ekler."""
    with _cli() as c:
        model = build_scene_model(c, layer)
    out = []
    for d in model["directors"]:
        line = f"{d['name_path']}  #{d['id']}"
        if d["sub_directors"]:
            line += f"  alt: {', '.join(d['sub_directors'])}"
        out.append(line)
        for a in d["animated"]:
            out.append(f"    {a['container'] or '(director)'}: {', '.join(a['channels'])}")
    for w in model["warnings"]:
        out.append("UYARI: " + w)
    return "\n".join(out) or "(stage bos)"


@server.tool()
@_errors
def viz_container(name_path: str, layer: str = "MAIN_SCENE") -> str:
    """Tek container'in okunabilir ozellikleri. name_path: '$kok$alt' veya sadece '$isim'."""
    if not name_path.startswith("$"):
        name_path = "$" + name_path
    props = ["NAME", "ACTIVE", "GEOM*TEXT", "TRANSFORMATION*POSITION", "TRANSFORMATION*ROTATION",
             "TRANSFORMATION*SCALING", "ALPHA*ALPHA", "IMAGE", "KEY*ACTIVE"]
    with _cli() as c:
        out = []
        for p in props:
            v = c.try_send(f"{layer}*TREE*{name_path}*{p} GET")
            if v is not None:
                out.append(f"{p} = {v}")
    return "\n".join(out) or f"{name_path} bulunamadi"


@server.tool()
@_errors
def viz_scene_dump(layer: str = "MAIN_SCENE", details: bool = False, out_dir: str = "") -> str:
    """Sahnenin tamamini tarar; scenes/ altina <sahne>.md (sablon) ve <sahne>.json yazar, sablonu dondurur.
    details=True her container'in GEOM*TEXT degerini de okur (buyuk sahnede daha yavas)."""
    with _cli() as c:
        model = build_scene_model(c, layer, details)
    jp, mp = write_outputs(model, out_dir or OUT_DIR)
    return f"Yazildi: {mp}\nYazildi: {jp}\n\n" + render_markdown(model)


@server.tool()
@_errors
def viz_scene_json(layer: str = "MAIN_SCENE") -> str:
    """Sahne modelini JSON olarak dondurur (kod uretimi icin)."""
    with _cli() as c:
        model = build_scene_model(c, layer)
    model.pop("raw", None)
    return json.dumps(model, ensure_ascii=False, indent=1)


@server.tool()
def viz_scene_csharp(layer: str = "MAIN_SCENE", via_path: str = "", scene: str = "",
                     namespace: str = "VizScenes", out_dir: str = "") -> str:
    """Sahneden C# sabit sinifi uretir (Directors.X, Containers.Y yollari + komut yardimcilari) ve
    scenes/<Sahne>.cs yazar. via_path verilirse .via'dan, verilmezse canli engine'den okur."""
    from vizengine.gen_csharp import write_csharp, render_csharp
    try:
        if via_path:
            from vizengine.via import read_via, ViaError
            model = read_via(via_path, scene or None)
        else:
            with _cli() as c:
                model = build_scene_model(c, layer, details=True)
    except Exception as e:  # noqa
        return f"HATA: {e}"
    p = write_csharp(model, out_dir or OUT_DIR, namespace)
    return f"Yazildi: {p}\n\n" + render_csharp(model, namespace)


@server.tool()
def viz_via_scenes(via_path: str) -> str:
    """Bir .via arsivindeki sahne adlarini listeler (arsivde onlarca sahne olabilir)."""
    from vizengine.via import list_scenes, ViaError
    try:
        scenes = list_scenes(via_path)
    except (ViaError, OSError) as e:
        return f"VIA HATASI: {e}"
    return f"{len(scenes)} sahne:\n" + "\n".join(scenes)


@server.tool()
def viz_via_dump(via_path: str, scene: str = "", out_dir: str = "") -> str:
    """Bir .via arsivindeki sahneyi (engine olmadan) okur: container agaci, geometri/plugin adlari,
    director hiyerarsisi. scenes/ altina sablon yazar. Arsivde birden fazla sahne varsa scene zorunlu
    (viz_via_scenes ile listeleyin). Kanal eslesmesi, aktiflik ve text .via'dan cikarilamaz."""
    from vizengine.via import read_via, ViaError
    try:
        model = read_via(via_path, scene or None)
    except (ViaError, OSError) as e:
        return f"VIA HATASI: {e}"
    jp, mp = write_outputs(model, out_dir or OUT_DIR)
    return f"Yazildi: {mp}\nYazildi: {jp}\n\n" + render_markdown(model)


if __name__ == "__main__":
    server.run("stdio")
