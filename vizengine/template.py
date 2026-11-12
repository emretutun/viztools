"""
Tree + stage verisinden sahne modeli ve okunabilir sablon (Markdown) uretir.

Sablonun amaci: sahneyi yapan/kullanan kisi container isim-yollarini, director
yollarini, hazir engine komutlarini ve VizScript parcalarini tek dosyada gorsun.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re

from .client import VizClient
from .parse import (Container, StageNode, parse_tree, parse_stage, flatten,
                    walk_stage, director_name_path, director_is_open)


# ------------------------------------------------------------- model -----
def build_scene_model(cli: VizClient, layer: str = "MAIN_SCENE",
                      details: bool = False, progress=None) -> dict:
    """progress: opsiyonel geri cagri progress(yapilan, toplam) (detay okuma sirasinda)."""
    scene_name = cli.try_send(f"{layer}*NAME GET") or "?"
    # Sahnenin Graphic Hub yolu: "SCENE*KLASOR/ALT/SAHNE" doner; uygulama bunu "/KLASOR/ALT/SAHNE" olarak kullanir.
    konum = (cli.try_send(f"{layer}*LOCATION_PATH GET") or "").strip()
    if konum.upper().startswith("SCENE*"):
        konum = konum[6:]
    scene_path = ("/" + konum.strip("/")) if konum and not konum.startswith("#") else ""
    tree_raw = cli.tree_raw(layer)
    stage_raw = cli.stage_raw(layer)
    flat_directors = cli.try_send(f"{layer}*STAGE*DIRECTOR GET") or ""
    on_air = cli.try_send("IS_ON_AIR GET") == "1"

    roots = parse_tree(tree_raw)
    containers = flatten(roots)
    stage_roots = parse_stage(stage_raw)

    directors: list[dict] = []
    warnings: list[str] = []
    closed: list[str] = []

    def visit(node: StageNode, ancestors: list[StageNode]):
        if node.is_director:
            animated = []
            subs = []
            for ch in node.children:
                if ch.is_container:
                    animated.append({
                        "container": ch.name, "id": ch.id, "open": ch.is_open,
                        "channels": [c.name for c in walk_stage(ch.children) if c.is_channel],
                    })
                elif ch.is_director:
                    subs.append(ch.name)
                elif ch.is_channel:
                    animated.append({"container": None, "id": ch.id, "channels": [ch.name]})
            is_open = director_is_open(node)
            d = {
                "name": node.name,
                "name_path": director_name_path(ancestors, node),
                "id": node.id, "stage_path": node.path, "open": is_open,
                "parent": ancestors[-1].name if ancestors and ancestors[-1].is_director else None,
                "sub_directors": subs, "animated": animated, "fields": node.fields,
            }
            directors.append(d)
            if is_open is False:
                closed.append(d["name_path"])
        for ch in node.children:
            visit(ch, ancestors + [node])

    for r in stage_roots:
        visit(r, [])

    if closed:
        warnings.append(
            f"{len(closed)} director Artist'te KAPALI oldugu icin icerigi okunamadi: "
            + ", ".join(closed)
            + ". Artist'te Stage panelinde bu dallari acin (expand), sahneyi kaydedin, tekrar tarayin."
        )

    known = {d["name"] for d in directors}
    for n in flat_directors.split():
        if n not in known:
            warnings.append(f"'{n}' director listesinde var ama STAGE GET agacinda yok (kapali dal olabilir).")

    texts: dict[str, str] = {}
    if details:
        for i, c in enumerate(containers, 1):
            if progress and (i % 10 == 0 or i == len(containers)):
                progress(i, len(containers))
            # Numarayla (#id) sorgula: ad yolu, ayni adli kardes container'larda ilk eslesene gider
            # ve digerlerinin metni/aktifligi okunamaz. Numara yoksa ad yoluna dus.
            hedef = f"#{c.id}" if isinstance(c.id, int) and c.id >= 0 else c.name_path
            act = cli.try_send(f"{layer}*TREE*{hedef}*ACTIVE GET")
            if act is not None:
                c.active = act.strip() == "1"
            # Yazi yalnizca geometrisi TEXT olan container'dan okunur; digerlerine GEOM*TEXT sormak
            # engine konsoluna her container icin "failed to process command" yazdirir.
            if cli.try_send(f"{layer}*TREE*{hedef}*GEOM GET"):
                tip = cli.try_send(f"{layer}*TREE*{hedef}*GEOM*TYPE GET") or ""
                if "TEXT" in tip.upper():
                    txt = cli.try_send(f"{layer}*TREE*{hedef}*GEOM*TEXT GET")
                    if txt is not None:
                        texts[c.name_path] = txt

    def cdict(c: Container):
        d = c.to_dict()
        if c.name_path in texts:
            d["text"] = texts[c.name_path]
        d["children"] = [cdict(ch) for ch in c.children]
        return d

    return {
        "scene": {
            "name": scene_name, "path": scene_path, "layer": layer, "on_air": on_air,
            "scanned_at": _dt.datetime.now().isoformat(timespec="seconds"),
            "container_count": len(containers), "director_count": len(directors),
        },
        "warnings": warnings,
        "tree": [cdict(r) for r in roots],
        "containers": [
            {"name": c.name, "name_path": c.name_path, "path": c.path, "id": c.id,
             "expanded": c.expanded, "active": c.active, "depth": c.depth,
             **({"text": texts[c.name_path]} if c.name_path in texts else {})}
            for c in containers
        ],
        "directors": directors,
        "raw": {"tree": tree_raw, "stage": stage_raw, "director_list": flat_directors},
    }


# ---------------------------------------------------------- markdown -----
def _vs_ident(name: str) -> str:
    out = "".join(ch if ch.isalnum() else "_" for ch in name)
    return ("d_" + out) if out[:1].isdigit() else (out or "x")


def render_markdown(model: dict) -> str:
    s = model["scene"]
    L = s["layer"]
    md: list[str] = []
    md.append(f"# Sahne sablonu: {s['name']}")
    md.append("")
    md.append(f"- Kaynak: {s.get('source', 'canli engine 127.0.0.1')}  ·  Katman: `{L}`  ·  "
              f"Tarama: {s['scanned_at']}  ·  {s['container_count']} container, {s['director_count']} director")
    if s["name"].startswith("#"):
        md.append("- Sahne adi `#id` seklinde: sahne henuz kaydedilmemis. "
                  "Kaydettikten sonra yeniden tarayin ki GH yolu sablona girsin.")
    else:
        md.append(f"- Harici komutlarda sahne yolu: `SCENE*{s['name']}*...` (katmana yuklenmeden) "
                  f"veya `{L}*...` (katmanda yukluyken)")
    if model["warnings"]:
        md.append("")
        md.append("## Uyarilar")
        for w in model["warnings"]:
            md.append(f"- {w}")

    # ---- directors
    md.append("")
    md.append("## Director'lar (Stage)")
    md.append("")
    md.append("| Director | Komut yolu | Durum | Animasyonlu container'lar / aksiyonlar |")
    md.append("|---|---|---|---|")
    for d in model["directors"]:
        def _a(a):
            if not a["container"]:
                return "/".join(a["channels"])
            if a["channels"]:
                return f"{a['container']} ({'/'.join(a['channels'])})"
            return f"{a['container']} (kapali)" if a.get("open") is False else a["container"]
        anim = ", ".join(_a(a) for a in d["animated"]) or "-"
        state = {True: "acik", False: "KAPALI (okunamadi)", None: ""}[d.get("open")]
        md.append(f"| {d['name']} | `{d['name_path']}` | {state} | {anim} |")
    md.append("")
    md.append("Harici komutlar (port 6100):")
    md.append("")
    md.append("```")
    for d in model["directors"]:
        p = d["name_path"]
        md.append(f"{L}*STAGE*DIRECTOR*{p} START")
        md.append(f"{L}*STAGE*DIRECTOR*{p} CONTINUE")
        md.append(f"{L}*STAGE*DIRECTOR*{p} STOP")
        md.append(f"{L}*STAGE*DIRECTOR*{p}*GOTO_TRIO 0      (basa sar)")
        md.append("")
    md.append("```")

    # ---- containers
    md.append("")
    md.append("## Container agaci (Tree)")
    md.append("")
    md.append("Girintili liste; her satirin yaninda komutlarda kullanilan `$isim$yolu`. "
              "Aktif/pasif ve text bilgisi `--details` ile taramada gelir.")
    md.append("")

    def walk(nodes, indent=0):
        for c in nodes:
            act = "" if c["active"] is None else ("  (aktif)" if c["active"] else "  (PASIF)")
            txt = f'  text="{" ".join(str(c["text"]).split())}"' if c.get("text") else ""
            plg = f"  [{', '.join(c['plugins'])}]" if c.get("plugins") else ""
            md.append(f"{'  ' * indent}- **{c['name']}**  `{c['name_path']}`  #{c['id']}{act}{txt}{plg}")
            walk(c["children"], indent + 1)
    walk(model["tree"])

    # ---- hazir komutlar
    md.append("")
    md.append("## Hazir container komutlari")
    md.append("")
    md.append("`<yol>` yerine yukaridaki `$isim$yolu` gelir:")
    md.append("")
    md.append("```")
    md.append(f"{L}*TREE*<yol>*GEOM*TEXT SET Yeni metin")
    md.append(f"{L}*TREE*<yol>*ACTIVE SET 1")
    md.append(f"{L}*TREE*<yol>*TRANSFORMATION*POSITION SET 0.0 0.0 0.0")
    md.append(f"{L}*TREE*<yol>*IMAGE SET IMAGE*/yol/resim")
    md.append(f"{L}*TREE*<yol>*GEOM*TEXT GET")
    md.append("```")
    md.append("")
    md.append("Bu sahnedeki her container icin hazir TEXT SET satiri:")
    md.append("")
    md.append("```")
    for c in model["containers"]:
        md.append(f"{L}*TREE*{c['name_path']}*GEOM*TEXT SET ")
    md.append("```")

    # ---- vizscript
    md.append("")
    md.append("## VizScript iskeleti")
    md.append("")
    md.append("Sahne script'ine yapistirip isleri doldurun; isimler bu sahneden alindi.")
    md.append("")
    md.append("```vb")
    from collections import Counter
    counts = Counter(c["name"] for c in model["containers"])
    unique = [c for c in model["containers"] if counts[c["name"]] == 1]
    dupes = sorted(n for n, k in counts.items() if k > 1)
    md.append("' --- Container referanslari (sahnede tek olan isimler) ---")
    for c in unique:
        md.append(f"dim c_{_vs_ident(c['name'])} as Container")
    if dupes:
        md.append("")
        md.append("' Asagidaki isimler sahnede birden fazla kez gecer; FindContainer belirsiz kalir.")
        md.append("' Bunlara ust container uzerinden FindSubContainer ile ya da tam yolla ulasin:")
        for n in dupes:
            paths = [c["name_path"] for c in model["containers"] if c["name"] == n]
            md.append(f"'   {n}: " + "  |  ".join(paths))
    md.append("")
    md.append("' --- Director referanslari (ayni isimli alt director'lar tam yoluyla adlandirilir) ---")
    dcounts = Counter(d["name"] for d in model["directors"])
    def _dir_ident(d):
        return _vs_ident(d["name"] if dcounts[d["name"]] == 1 else d["name_path"].lstrip("$").replace("$", "_"))
    for d in model["directors"]:
        md.append(f"dim dir_{_dir_ident(d)} as Director")
    md.append("")
    md.append("sub OnInitParameters()")
    md.append("end sub")
    md.append("")
    md.append("sub OnInit()")
    for c in unique:
        md.append(f'    c_{_vs_ident(c["name"])} = Scene.FindContainer("{c["name"]}")')
    for d in model["directors"]:
        dpath = d["name_path"].lstrip("$").replace("$", "/")
        md.append(f'    dir_{_dir_ident(d)} = Stage.FindDirector("{dpath}")')
    md.append("end sub")
    md.append("")
    md.append("' Ornek kullanim:")
    md.append("'   c_X.Geometry.Text = \"metin\"      (Text geometrisi olan container)")
    md.append("'   c_X.Active = true / false")
    md.append("'   c_X.Position.X = 100")
    md.append("'   dir_Y.StartAnimation()  /  dir_Y.ContinueAnimation()  /  dir_Y.Reset()")
    md.append("```")
    md.append("")
    return "\n".join(md)


def scene_base(model: dict) -> str:
    """Dosya/klasor adi olarak kullanilan guvenli sahne adi."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", model["scene"]["name"].strip("/#")) or "sahne"


def scene_dir(model: dict, out_dir: str) -> str:
    """Her sahnenin ciktilari kendi klasorunde: <out_dir>/<sahne>/<sahne>.md|.json|.cs"""
    d = os.path.join(out_dir, scene_base(model))
    os.makedirs(d, exist_ok=True)
    return d


def write_outputs(model: dict, out_dir: str) -> tuple[str, str]:
    base = scene_base(model)
    d = scene_dir(model, out_dir)
    jp = os.path.join(d, f"{base}.json")
    mp = os.path.join(d, f"{base}.md")
    with open(jp, "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, indent=2)
    with open(mp, "w", encoding="utf-8") as f:
        f.write(render_markdown(model))
    return jp, mp
