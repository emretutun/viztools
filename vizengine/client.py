"""
Salt okunur Viz Engine TCP istemcisi.

Guvenlik kurallari (kodla zorlanir, config ile acilamaz):
  * Yalnizca loopback adrese baglanir (127.0.0.1 / localhost / ::1).
  * Yalnizca okuma komutlari gonderir: fiil GET, GET_*, IS_* olmali.
    SET / START / STOP / LOAD / SAVE / DELETE ... hepsi reddedilir.
  * Graphic Hub'dan yol ile sahne cekmeyi (SCENE*/yol*...) reddeder;
    sadece engine'de zaten yuklu olan sahne (#id veya MAIN_SCENE) okunur.
"""
from __future__ import annotations

import re
import socket
import threading

LOOPBACK = {"127.0.0.1", "localhost", "::1"}
_VERB_OK = re.compile(r"^(GET|GET_[A-Z_]+|IS_[A-Z_]+)(\s.*)?$")
# SCENE*#808*... (yuklu nesne) serbest, SCENE*/HT/...*... (GH'dan cekme) yasak
_DB_PATH = re.compile(r"^SCENE\*(?!#)", re.IGNORECASE)


class VizError(RuntimeError):
    """Engine ERROR dondurdu."""


class VizCommandBlocked(PermissionError):
    """Komut salt-okunur kurali geregi gonderilmedi."""


def check_command(cmd: str) -> str:
    cmd = cmd.strip()
    if not cmd:
        raise VizCommandBlocked("bos komut")
    if "\n" in cmd or "\0" in cmd:
        raise VizCommandBlocked("komut tek satir olmali")
    parts = cmd.split(" ", 1)
    verb = parts[1].strip() if len(parts) == 2 else ""
    if not _VERB_OK.match(verb):
        raise VizCommandBlocked(
            f"yalnizca GET / GET_* / IS_* komutlarina izin var, reddedildi: {cmd}"
        )
    if _DB_PATH.match(cmd):
        raise VizCommandBlocked(
            "Graphic Hub'dan yol ile sahne okuma kapali (SCENE*/...). "
            "Sahneyi Artist'te acin ve MAIN_SCENE uzerinden okuyun."
        )
    return cmd


class VizClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 6100,
                 timeout: float = 5.0, encoding: str = "utf-8"):
        if host not in LOOPBACK:
            raise VizCommandBlocked(f"yalnizca loopback adrese izin var, reddedildi: {host}")
        self.host, self.port, self.timeout, self.encoding = host, port, timeout, encoding
        self._sock: socket.socket | None = None
        self._seq = 0
        self._lock = threading.Lock()

    # -- baglanti -----------------------------------------------------------
    def connect(self) -> "VizClient":
        if self._sock is None:
            s = socket.create_connection((self.host, self.port), timeout=self.timeout)
            s.settimeout(self.timeout)
            self._sock = s
        return self

    def close(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, *_):
        self.close()

    # -- komut --------------------------------------------------------------
    def _decode(self, raw: bytes) -> str:
        try:
            return raw.decode(self.encoding)
        except UnicodeDecodeError:
            return raw.decode("latin-1")

    def send(self, cmd: str) -> str:
        """Komutu gonderir, 'id ' onekini soyulmus cevabi dondurur. ERROR -> VizError."""
        cmd = check_command(cmd)
        with self._lock:
            self.connect()
            self._seq += 1
            seq = self._seq
            self._sock.sendall(f"{seq} {cmd}\0".encode(self.encoding, "replace"))
            buf = bytearray()
            while True:
                chunk = self._sock.recv(1 << 16)
                if not chunk:
                    self.close()
                    raise VizError("baglanti kapandi")
                buf += chunk
                if b"\0" in buf:
                    break
            raw = bytes(buf[: buf.index(b"\0")])
        text = self._decode(raw)
        prefix = f"{seq} "
        if text.startswith(prefix):
            text = text[len(prefix):]
        text = text.rstrip()
        if text.startswith("ERROR"):
            raise VizError(text)
        return text

    def try_send(self, cmd: str) -> str | None:
        """ERROR yerine None dondurur (opsiyonel ozellikleri okumak icin)."""
        try:
            return self.send(cmd)
        except VizError:
            return None

    # -- kisayollar ---------------------------------------------------------
    def is_on_air(self) -> bool:
        return self.send("IS_ON_AIR GET").strip() == "1"

    def scene_name(self, layer: str = "MAIN_SCENE") -> str:
        return self.send(f"{layer}*NAME GET")

    def tree_raw(self, layer: str = "MAIN_SCENE") -> str:
        return self.send(f"{layer}*TREE GET")

    def stage_raw(self, layer: str = "MAIN_SCENE") -> str:
        return self.send(f"{layer}*STAGE GET")

    def director_names(self, layer: str = "MAIN_SCENE") -> list[str]:
        return self.send(f"{layer}*STAGE*DIRECTOR GET").split()
