"""
Viz Engine TREE GET ve STAGE GET cevaplarini yapiya cevirir.

TREE GET  : {1 27473 kok_isim 1} {1/1 27486 ALT 0} {1/1/1 27490 yaprak}
            -> {path id name [expanded]}  son sayi = Artist agacinda dal acik mi;
               yapraklarda yoktur. AKTIFLIK DEGILDIR (ACTIVE GET ile okunur).
STAGE GET : ic ice parantezli agac:
            { 0 CDirectorTree #1166 "Default" -1 0 0 0 0 { ...cocuklar... } }
            { 0/0/1 CONTAINER #175154 "KATILIM_ORANI" 1 0 9 0 { ... } }
            { 0/0/1/0 CChannelFloat #175149 "Alpha" -1 0 4 0 {} }
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict


# ---------------------------------------------------------------- TREE ----
@dataclass
class Container:
    path: str            # "1/2/3" (TREE GET'in verdigi sayisal yol)
    id: int
    name: str
    expanded: bool | None   # TREE GET'teki son sayi: Artist agacinda dal acik mi (aktiflik DEGIL)
    depth: int
    active: bool | None = None  # --details ile ACTIVE GET'ten okunur
    name_path: str = ""  # "$kok$alt$yaprak" (komutlarda kullanilan isim yolu)
    children: list["Container"] = field(default_factory=list)

    def to_dict(self):
        return {
            "path": self.path, "id": self.id, "name": self.name, "expanded": self.expanded,
            "active": self.active, "depth": self.depth, "name_path": self.name_path,
            "children": [c.to_dict() for c in self.children],
        }


_TREE_ITEM = re.compile(r"\{([^{}]*)\}")


def parse_tree(raw: str) -> list[Container]:
    """Duz listeden (parent yolu ile) agac kurar; kok container listesini dondurur."""
    flat: list[Container] = []
    for m in _TREE_ITEM.finditer(raw):
        toks = m.group(1).split()
        if len(toks) < 3:
            continue
        path, id_ = toks[0], toks[1]
        if len(toks) >= 4 and toks[-1] in ("0", "1"):
            name, expanded = " ".join(toks[2:-1]), toks[-1] == "1"
        else:
            name, expanded = " ".join(toks[2:]), None
        try:
            idn = int(id_)
        except ValueError:
            idn = -1
        flat.append(Container(path=path, id=idn, name=name, expanded=expanded,
                              depth=path.count("/")))
    by_path = {c.path: c for c in flat}
    roots: list[Container] = []
    for c in flat:
        parent = by_path.get(c.path.rsplit("/", 1)[0]) if "/" in c.path else None
        if parent:
            parent.children.append(c)
            c.name_path = f"{parent.name_path}${c.name}"
        else:
            roots.append(c)
            c.name_path = f"${c.name}"
    return roots


def flatten(nodes: list[Container]) -> list[Container]:
    out: list[Container] = []
    def walk(n):
        out.append(n)
        for ch in n.children:
            walk(ch)
    for n in nodes:
        walk(n)
    return out


# --------------------------------------------------------------- STAGE ----
@dataclass
class StageNode:
    path: str
    type: str            # CDirectorTree | CONTAINER | CChannelFloat | ...
    id: int
    name: str
    fields: list[str]    # tipi bilinmeyen sayisal alanlar (ham)
    children: list["StageNode"] = field(default_factory=list)

    @property
    def is_director(self) -> bool:
        return self.type.startswith("CDirector")

    @property
    def is_container(self) -> bool:
        return self.type == "CONTAINER"

    @property
    def is_channel(self) -> bool:
        return self.type.startswith("CChannel")

    @property
    def is_open(self) -> bool | None:
        """Director ve CONTAINER satirlarinda ilk sayi: 1 acik (alt satirlar geldi), 0 kapali."""
        if (self.is_director or self.is_container) and self.fields:
            return self.fields[0] == "1"
        return None

    def to_dict(self):
        return {
            "path": self.path, "type": self.type, "id": self.id, "name": self.name,
            "fields": self.fields, "children": [c.to_dict() for c in self.children],
        }


_TOKEN = re.compile(r'\{|\}|"(?:[^"\\]|\\.)*"|[^\s{}"]+')


def parse_stage(raw: str) -> list[StageNode]:
    """
    Gercek engine ciktisi DUZ bir listedir; her blok bagimsizdir ve hiyerarsi
    yoldan (6, 6/4, 6/4/0 ...) kurulur. Bloklarin icindeki {} bos isaretcidir.
    Ic ice gelen (eski/alternatif) bicim de ayni kodla cozulur: ic bloklar da
    yollariyla kaydedilip ebeveynine baglanir.
    """
    tokens = _TOKEN.findall(raw)
    pos = 0
    flat: list[StageNode] = []

    def parse_block() -> None:
        nonlocal pos
        pos += 1  # '{'
        head: list[str] = []
        while pos < len(tokens) and tokens[pos] != "}":
            if tokens[pos] == "{":
                parse_block()
            else:
                head.append(tokens[pos])
                pos += 1
        pos += 1  # '}'
        if len(head) < 2:
            return
        path, type_ = head[0], head[1]
        rest = head[2:]
        id_ = -1
        if rest and rest[0].startswith("#"):
            try:
                id_ = int(rest[0][1:])
            except ValueError:
                pass
            rest = rest[1:]
        name = ""
        if rest and rest[0].startswith('"'):
            name = rest[0][1:-1]
            rest = rest[1:]
        flat.append(StageNode(path=path, type=type_, id=id_, name=name, fields=rest))

    while pos < len(tokens):
        if tokens[pos] == "{":
            parse_block()
        else:
            pos += 1

    by_path = {n.path: n for n in flat}
    roots: list[StageNode] = []
    for n in flat:
        parent = by_path.get(n.path.rsplit("/", 1)[0]) if "/" in n.path else None
        if parent is not None and parent is not n:
            parent.children.append(n)
        else:
            roots.append(n)
    return roots


def director_is_open(node: StageNode) -> bool | None:
    """Director satirindaki ilk sayi: 1 = Artist'te acik (alt satirlar geliyor), 0 = kapali."""
    if not node.is_director or not node.fields:
        return None
    return node.fields[0] == "1"


def walk_stage(nodes: list[StageNode]):
    for n in nodes:
        yield n
        yield from walk_stage(n.children)


def director_name_path(ancestors: list[StageNode], node: StageNode) -> str:
    """Komutlarda kullanilan director yolu: $ust$alt. 'Default' kok ise atlanir."""
    names = [a.name for a in ancestors if a.is_director] + [node.name]
    if names and names[0] == "Default" and len(names) > 1:
        names = names[1:]
    return "$" + "$".join(names)
