"""
Viz Artist arsiv dosyasi (.via, "VIZ3ARCH") okuyucu. SALT OKUNUR, dosyaya yazmaz.

Arsiv, ardisik nesnelerden olusur; her nesne  <u16 len><ad><u16 len><TIP>  basligi ile
baslar (TIP: SCENE, IMAGE, FONT, BASE_FONT, GEOM, MATERIAL ...). Bir arsivde onlarca
sahne olabilir; `list_scenes` ile listelenir, `read_via(path, scene=ad)` ile biri okunur.

Sahne verisi zlib bloklarinda, etiketli ic ice bir ikili bicimde durur:
  fe XX YY ... fe ~XX ~YY    (etiket, bit-tersi ile kapanir)
Bilinen etiketler (ornek dosyalardan cikarildi, resmi belge yok):
  07c4 container   0317 adi   0349 uuid   07c5 alt container listesi (07c4'un hemen ardindan kardes)
  0522 plugin tipi 0623 geometri/plugin adi  062e parametre adi
  042f director    0422 adi   0430 cocuk sayisi (sirali, director'dan sonra gelir)
Canli engine taramasinin aksine burada kanal/keyframe -> container eslesmesi,
aktiflik ve text degerleri CIKARILAMAZ; sablon bunu belirtir.
"""
from __future__ import annotations

import datetime as _dt
import os
import re
import struct
import zlib

_STRING_TAGS = {0x0422, 0x0317, 0x0623, 0x062e, 0x0349, 0x0629, 0x062f, 0x113a,
                0x05e4, 0x0522, 0x0706, 0x1808, 0x06f2}
T_CONTAINER, T_CNAME, T_CUUID, T_CHILDREN = 0x07c4, 0x0317, 0x0349, 0x07c5
T_PLUGIN_NAME, T_PLUGIN_TYPE = 0x0623, 0x0522
T_DIRECTOR, T_DNAME, T_DCOUNT = 0x042f, 0x0422, 0x0430

_ENTRY = re.compile(
    rb"(?P<nl>[\x01-\x40])\x00(?P<name>[\x20-\x7e]{1,64}?)(?P<tl>[\x03-\x10])\x00(?P<type>[A-Z_]{3,16})")


class ViaError(RuntimeError):
    pass


# --------------------------------------------------------------- archive --
def _read(path: str) -> bytes:
    data = open(path, "rb").read()
    if not data.startswith(b"VIZ3ARCH"):
        raise ViaError("Bu bir Viz arsivi degil (VIZ3ARCH basligi yok).")
    return data


def _entries(data: bytes) -> list[tuple[int, str, str]]:
    out = []
    for m in _ENTRY.finditer(data):
        if len(m.group("name")) != m.group("nl")[0] or len(m.group("type")) != m.group("tl")[0]:
            continue
        out.append((m.start(), m.group("name").decode("latin-1"), m.group("type").decode()))
    return out


def list_scenes(path: str) -> list[str]:
    """Arsivdeki sahne adlari (arsiv sirasiyla)."""
    return [n for _, n, t in _entries(_read(path)) if t == "SCENE"]


def _scene_slice(data: bytes, scene: str | None) -> tuple[str, bytes]:
    ents = _entries(data)
    scenes = [(i, o, n) for i, (o, n, t) in enumerate(ents) if t == "SCENE"]
    if not scenes:
        # tek nesneli eski bicim: tum dosya
        return os.path.basename("sahne"), data
    if scene is None:
        if len(scenes) > 1:
            raise ViaError("Arsivde birden fazla sahne var; scene= ile birini secin: "
                           + ", ".join(n for _, _, n in scenes))
        i, o, n = scenes[0]
    else:
        match = [s for s in scenes if s[2] == scene]
        if not match:
            raise ViaError(f"'{scene}' arsivde yok. Sahneler: " + ", ".join(n for _, _, n in scenes))
        i, o, n = match[0]
    end = ents[i + 1][0] if i + 1 < len(ents) else len(data)
    return n, data[o:end]


# ------------------------------------------------------------- low level --
_CHUNK = re.compile(rb"(?s)(.{4})(.{4})\x78[\x01\x5e\x9c\xda]")


def _desegment(sdata: bytes) -> tuple[bytes, int]:
    """
    Nesne verisi 51200 baytlik DILIMLERE bolunmustur; her dilimin basinda
        <u16 dilim sirasi><u32 dilim uzunlugu>
    vardir ve zlib parcalari bu dilim sinirlarini ortadan boler. Dilim basliklari
    soyulup surekli veri dondurulur. (ilk dilim basligi, ilk zlib parca basligindan
    6 bayt once bulunur.)  Donus: (surekli_veri, dilim_sayisi)
    """
    # Ilk GERCEK parcayi bul: dilimin basindaki kucuk resim verisi icinde sahte "78 01"
    # eslesmeleri olabilir; ancak basligi makul ve cozulup sağlamasi tutan ilk parca gecerlidir.
    pos = None
    for m in _CHUNK.finditer(sdata):
        if m.start() < 6:
            continue
        comp = struct.unpack("<I", m.group(1))[0]
        raw = struct.unpack("<I", m.group(2))[0]
        seg_len = struct.unpack_from("<I", sdata, m.start() - 4)[0]
        if not (2 < comp <= len(sdata)) or not (0 < raw <= 8 << 20) or not (0 < seg_len <= len(sdata)):
            continue
        try:
            d = zlib.decompressobj(-15)
            chunk = d.decompress(sdata[m.start() + 10:m.start() + 8 + comp])
            if len(d.unused_data) >= 4 and struct.unpack(">I", d.unused_data[:4])[0] == (zlib.adler32(chunk) & 0xFFFFFFFF):
                pos = m.start() - 6
                break
        except zlib.error:
            continue
    if pos is None:
        return sdata, 0
    out = bytearray()
    expect = struct.unpack_from("<H", sdata, pos)[0]   # dilim sirasi arsiv genelinde sayilabilir
    count = 0
    while pos + 6 <= len(sdata):
        idx = struct.unpack_from("<H", sdata, pos)[0]
        ln = struct.unpack_from("<I", sdata, pos + 2)[0]
        if idx != expect or ln == 0 or pos + 6 + ln > len(sdata):
            break
        out += sdata[pos + 6:pos + 6 + ln]
        pos += 6 + ln
        expect += 1
        count += 1
    return (bytes(out), count) if count else (sdata, 0)


def _zlib_blocks(data: bytes) -> list[bytes]:
    """
    Dilimleri soyulmus veri icinde parcalar arka arkaya gelir:
        <u32 sikistirilmis uzunluk><u32 acik uzunluk><zlib akisi (78 01 ...)><adler32>
    'sikistirilmis uzunluk' bu zlib basindan bir SONRAKI parcanin zlib basina kadar olan
    mesafedir (sonraki 8 baytlik baslik dahil). Her parca bagimsiz bir zlib akisidir ve
    adler32 sağlaması ile dogrulanir.
    """
    data, _ = _desegment(data)
    out = []
    pos = 0
    n = len(data)
    while True:
        m = _CHUNK.search(data, pos)
        if not m:
            break
        comp = struct.unpack("<I", m.group(1))[0]
        raw = struct.unpack("<I", m.group(2))[0]
        start = m.start() + 8
        if not (2 < comp <= n - start + 8) or not (0 < raw <= 8 << 20):
            pos = m.start() + 1
            continue
        body = data[start + 2:start + comp]
        try:
            d = zlib.decompressobj(-15)
            chunk = d.decompress(body)
        except zlib.error:
            pos = m.start() + 1
            continue
        trailer = d.unused_data[:4]
        adler_ok = len(trailer) == 4 and struct.unpack(">I", trailer)[0] == (zlib.adler32(chunk) & 0xFFFFFFFF)
        if not adler_ok and len(chunk) < min(raw, 64):
            pos = m.start() + 1
            continue
        out.append(chunk[:raw] if len(chunk) >= raw else chunk)
        pos = start + comp - 8
    return out


def verify_chunks(path: str, scene: str | None = None) -> dict:
    """Tani: parca sayisi, dilim sayisi ve sağlamasi tutmayan parcalar."""
    data = _read(path)
    _, sdata = _scene_slice(data, scene)
    cont, segs = _desegment(sdata)
    bad, total, pos, n = [], 0, 0, len(cont)
    while True:
        m = _CHUNK.search(cont, pos)
        if not m:
            break
        comp = struct.unpack("<I", m.group(1))[0]
        raw = struct.unpack("<I", m.group(2))[0]
        start = m.start() + 8
        if not (2 < comp <= n - start + 8) or not (0 < raw <= 8 << 20):
            pos = m.start() + 1
            continue
        try:
            d = zlib.decompressobj(-15)
            chunk = d.decompress(cont[start + 2:start + comp])
            ok = len(d.unused_data) >= 4 and struct.unpack(">I", d.unused_data[:4])[0] == (zlib.adler32(chunk) & 0xFFFFFFFF)
        except zlib.error:
            ok = False
        if not ok:
            bad.append(total)
        total += 1
        pos = start + comp - 8
    return {"segments": segs, "chunks": total, "bad_chunks": bad}


def _parse_tags(d: bytes) -> dict:
    root = {"tag": None, "children": [], "str": None}
    stack = [root]
    i, n = 0, len(d)
    while i < n:
        if d[i] == 0xFE and i + 2 < n:
            tag = (d[i + 1] << 8) | d[i + 2]
            comp = (((~d[i + 1]) & 0xFF) << 8) | ((~d[i + 2]) & 0xFF)
            for k in range(len(stack) - 1, 0, -1):
                if stack[k]["tag"] == comp:
                    del stack[k:]
                    break
            else:
                node = {"tag": tag, "children": [], "str": None}
                stack[-1]["children"].append(node)
                stack.append(node)
                i += 3
                if tag in _STRING_TAGS and i + 2 <= n:
                    ln = struct.unpack_from("<H", d, i)[0]
                    if 0 < ln < 4096 and i + 2 + ln <= n:
                        node["str"] = d[i + 2:i + 2 + ln].decode("utf-8", "replace")
                        i += 2 + ln
                continue
            i += 3
            continue
        i += 1
    return root


def _find_str(node, tag, depth=3):
    def rec(n, dd):
        for ch in n["children"]:
            if ch["tag"] == tag and ch["str"] is not None:
                return ch["str"]
            if dd > 0 and ch["tag"] != T_CHILDREN:
                r = rec(ch, dd - 1)
                if r:
                    return r
        return None
    return rec(node, depth)


# ------------------------------------------------------------ containers --
_CTOK = re.compile(
    rb"\xfe\x07\xc4|\xfe\xf8\x3b|\xfe\x07\xc5|\xfe\xf8\x3a|\xfe\x03\x17(..)|\xfe\x03\x49(..)|\xfe\x06\x23(..)",
    re.S)


def _container_tree_stream(stream: bytes) -> list[dict]:
    """
    Container agacini yalnizca su etiketleri izleyerek kurar (ikili payload'daki rastgele
    baytlarin yanlis kapanis sayilmasini onlemek icin genel etiket agaci kullanilmaz):
      07c4 container ac / f83b kapa, 07c5 alt liste ac / f83a kapa,
      0317 ad, 0349 uuid, 0623 geometri/plugin adi.
    Alt liste (07c5) ait oldugu container'in hemen ardindan kardes olarak gelir.
    """
    counter = [0]
    roots: list[dict] = []
    lists = [{"nodes": roots, "owner": None, "parent_np": "", "parent_path": ""}]  # acik listeler
    open_c: list[dict] = []  # acik container'lar
    pos = 0
    while True:
        m = _CTOK.search(stream, pos)
        if not m:
            break
        tok = stream[m.start():m.start() + 3]
        pos = m.end()
        if tok == b"\xfe\x07\xc4":
            lst = lists[-1]
            k = len(lst["nodes"]) + 1
            counter[0] += 1
            path = f"{lst['parent_path']}/{k}" if lst["parent_path"] else str(k)
            node = {"path": path, "id": counter[0], "name": None, "uuid": None, "plugins": [],
                    "expanded": None, "active": None, "depth": path.count("/"),
                    "name_path": None, "children": [], "_pnp": lst["parent_np"]}
            lst["nodes"].append(node)
            open_c.append(node)
        elif tok == b"\xfe\xf8\x3b":
            if open_c:
                n = open_c.pop()
                if n["name"] is None:
                    n["name"] = f"container_{n['id']}"
                n["name_path"] = f"{n.pop('_pnp')}${n['name']}"
        elif tok == b"\xfe\x07\xc5":
            lst = lists[-1]
            owner = lst["nodes"][-1] if lst["nodes"] else None
            if owner is None:
                # sahibi olmayan liste (en ust kok listesi): ayni duzeyde devam et
                lists.append({"nodes": lst["nodes"], "owner": None, "parent_np": lst["parent_np"], "parent_path": lst["parent_path"]})
            else:
                np_ = owner["name_path"] or f"{owner.get('_pnp', '')}${owner['name'] or ''}"
                lists.append({"nodes": owner["children"], "owner": owner, "parent_np": np_, "parent_path": owner["path"]})
        elif tok == b"\xfe\xf8\x3a":
            if len(lists) > 1:
                lists.pop()
        else:
            ln = struct.unpack("<H", m.group(1) or m.group(2) or m.group(3))[0]
            if not (0 < ln < 1024):
                continue
            text = stream[pos:pos + ln].decode("utf-8", "replace")
            pos += ln
            if not open_c:
                continue
            cur = open_c[-1]
            if m.group(1) is not None:
                if cur["name"] is None:
                    cur["name"] = text
            elif m.group(2) is not None:
                cur["uuid"] = cur["uuid"] or text
            else:
                cur["plugins"].append(text)
    # kapanmamis container'lari da tamamla
    for n in open_c:
        if n["name"] is None:
            n["name"] = f"container_{n['id']}"
        n["name_path"] = f"{n.pop('_pnp')}${n['name']}"
    return roots


# ------------------------------------------------------------- directors --
def _directors(d: bytes) -> list[dict]:
    """Ham baytlardan 0422 (ad) ve 0430 (cocuk sayisi) sirasini okuyup hiyerarsi kurar."""
    seq = []
    for m in re.finditer(rb"\xfe\x04\x22(..)|\xfe\x04\x30(....)", d, re.S):
        if m.group(1) is not None:
            ln = struct.unpack("<H", m.group(1))[0]
            if 0 < ln < 256:
                seq.append(("name", d[m.end():m.end() + ln].decode("utf-8", "replace")))
        else:
            seq.append(("count", struct.unpack("<I", m.group(2))[0]))
    out = []
    it = iter(seq)

    def parse(parent_path, parent_name):
        kind, name = next(it)
        while kind != "name":
            kind, name = next(it)
        shown = "Default" if name == "$root" else name
        name_path = f"{parent_path}${shown}" if parent_path else f"${shown}"
        node = {"name": shown, "name_path": name_path, "id": -1, "stage_path": "", "open": None,
                "parent": parent_name, "sub_directors": [], "animated": [], "fields": []}
        out.append(node)
        kind, cnt = next(it)
        if kind != "count" or cnt > 10000:
            return node
        child_parent = "" if (shown == "Default" and parent_path == "") else name_path
        for _ in range(cnt):
            child = parse(child_parent, shown)
            node["sub_directors"].append(child["name"])
        return node

    try:
        while True:
            parse("", None)
    except StopIteration:
        pass
    # Engine'in STAGE GET listesinde kok ("$root"/Default) yer almaz; ayni gorunum icin dusur.
    return [d for d in out if not (d["name_path"] == "$Default" and d["parent"] is None)]


# ------------------------------------------------------------------ main --
def read_via(path: str, scene: str | None = None) -> dict:
    data = _read(path)
    scene_name, sdata = _scene_slice(data, scene)
    blocks = _zlib_blocks(sdata)
    if not blocks:
        raise ViaError(f"'{scene_name}' icin cozulebilir sahne blogu bulunamadi.")

    ext_files = sorted(set(
        s.decode("latin-1") for s in
        re.findall(rb"[A-Za-z]:/[\x20-\x7e]+?\.(?:avi|mov|mp4|mxf|png|jpg|tga|wav)", sdata)))

    # Sahne verisi ~51 KB'lik parcalara bolunup her parca ayri sikistirilmis;
    # parcalar sirayla birlestirilince tek bir etiket akisi olusur.
    stream = b"".join(blocks)
    roots = _container_tree_stream(stream) if b"\xfe\x07\xc4" in stream else []
    directors = _directors(stream) if b"\xfe\x04\x22" in stream else []

    def flat(nodes):
        for n in nodes:
            yield n
            yield from flat(n["children"])
    containers = list(flat(roots))

    def strip(n):
        return {k: v for k, v in n.items() if k != "children"} | {"children": [strip(c) for c in n["children"]]}

    return {
        "scene": {
            "name": scene_name, "layer": "MAIN_SCENE", "on_air": False,
            "source": f"VIA dosyasi: {os.path.basename(path)}",
            "scanned_at": _dt.datetime.now().isoformat(timespec="seconds"),
            "container_count": len(containers), "director_count": len(directors),
        },
        "warnings": [
            "Bu sahne .via dosyasindan okundu: director'larin hangi container/kanali oynattigi, "
            "aktiflik ve text degerleri dosyadan cikarilamaz. Tam bilgi icin sahneyi Artist'te acip canli tarayin.",
        ] + ([f"Dis dosya referanslari: {', '.join(ext_files)}"] if ext_files else []),
        "tree": [strip(r) for r in roots],
        "containers": [{k: v for k, v in c.items() if k != "children"} for c in containers],
        "directors": directors,
        "raw": {"tree": "", "stage": "", "director_list": " ".join(d["name"] for d in directors)},
    }
