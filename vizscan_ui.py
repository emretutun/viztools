"""
viztools arayuzu (Tkinter, ek kurulum gerektirmez).

  python vizscan_ui.py

Iki kaynak: canli Viz Engine (127.0.0.1, salt okunur) veya bir .via dosyasi.
Hicbir zaman sahneye, engine'e ya da Graphic Hub'a yazmaz.
"""
import json
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vizengine import VizClient, VizCommandBlocked, VizError
from vizengine.template import build_scene_model, write_outputs, render_markdown
from vizengine.via import read_via, list_scenes, ViaError
from vizengine.gen_csharp import write_csharp

HERE = os.path.dirname(os.path.abspath(__file__))
SCENES_DIR = os.path.join(HERE, "scenes")
STATE_FILE = os.path.join(HERE, ".viztools_ui.json")
LAYERS = ("MAIN_SCENE", "FRONT_SCENE", "BACK_SCENE")

BG, PANEL, LINE = "#f4f5f7", "#ffffff", "#e1e4e8"
TEXT, MUTED, ACCENT, OK, WARN, ERR = "#1f2328", "#6a737d", "#1f6feb", "#1a7f37", "#9a6700", "#cf222e"
FONT, FONT_B, FONT_H, MONO = ("Segoe UI", 10), ("Segoe UI", 10, "bold"), ("Segoe UI", 13, "bold"), ("Consolas", 10)


# ------------------------------------------------------------------ state --
def load_state() -> dict:
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(st: dict):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.state_ = load_state()
        self.title("viztools · Sahne tarayıcı")
        self.geometry(self.state_.get("geometry", "1220x780"))
        self.minsize(960, 620)
        self.configure(bg=BG)
        self.model, self.last_md, self.last_source = None, None, None
        self._dir_index, self._con_index = {}, {}
        self._style()
        self._build()
        self.bind("<Control-f>", lambda e: (self.search_entry.focus_set(), self.search_entry.select_range(0, "end")))
        self.bind("<Escape>", lambda e: self.search.set(""))
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(300, self._check_engine_async)

    # ------------------------------------------------------------ style --
    def _style(self):
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure(".", background=BG, foreground=TEXT, font=FONT)
        st.configure("Card.TFrame", background=PANEL)
        st.configure("Card.TLabel", background=PANEL)
        st.configure("Muted.TLabel", foreground=MUTED, background=BG)
        st.configure("H.TLabel", font=FONT_H, background=BG)
        st.configure("TButton", padding=(10, 5))
        st.configure("Small.TButton", padding=(6, 2))
        st.configure("Primary.TButton", background=ACCENT, foreground="white", padding=(14, 7), font=FONT_B)
        st.map("Primary.TButton", background=[("active", "#1a5fd0"), ("disabled", "#9db7e6")])
        st.configure("Treeview", background=PANEL, fieldbackground=PANEL, rowheight=26, borderwidth=0, font=FONT)
        st.configure("Treeview.Heading", font=FONT_B, background="#eef0f3", relief="flat")
        st.configure("TNotebook", background=BG, borderwidth=0)
        st.configure("TNotebook.Tab", padding=(16, 8), font=FONT)
        st.map("TNotebook.Tab", background=[("selected", PANEL)])
        st.configure("TLabelframe", background=BG)
        st.configure("TLabelframe.Label", background=BG, foreground=MUTED)
        st.configure("Horizontal.TProgressbar", troughcolor="#e9ecef", background=ACCENT)

    # ------------------------------------------------------------ build --
    def _build(self):
        hdr = ttk.Frame(self, padding=(16, 12, 16, 6))
        hdr.pack(fill="x")
        ttk.Label(hdr, text="Sahne tarayıcı", style="H.TLabel").pack(side="left")
        ttk.Label(hdr, text="   salt okunur · yalnızca 127.0.0.1", style="Muted.TLabel").pack(side="left", pady=(4, 0))
        self.engine_dot = tk.Label(hdr, text="● engine", bg=BG, fg=MUTED, font=FONT)
        self.engine_dot.pack(side="right")

        bar = ttk.Frame(self, padding=(16, 0, 16, 6))
        bar.pack(fill="x")

        live = ttk.Labelframe(bar, text="Canlı engine (Artist açıkken)", padding=10)
        live.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.layer = tk.StringVar(value=self.state_.get("layer", "MAIN_SCENE"))
        ttk.Combobox(live, textvariable=self.layer, values=LAYERS, width=13, state="readonly").pack(side="left")
        self.details = tk.BooleanVar(value=self.state_.get("details", True))
        ttk.Checkbutton(live, text="Text ve aktiflik de oku", variable=self.details).pack(side="left", padx=10)
        self.btn_scan = ttk.Button(live, text="Sahneyi tara", style="Primary.TButton", command=self.on_scan)
        self.btn_scan.pack(side="left")

        via = ttk.Labelframe(bar, text=".via dosyası (engine kapalıyken)", padding=10)
        via.pack(side="left", fill="x", expand=True)
        ttk.Button(via, text=".via dosyası aç…", style="Primary.TButton", command=self.on_via).pack(side="left")
        self.recent_btn = ttk.Menubutton(via, text="Son açılanlar ▾")
        self.recent_btn.pack(side="left", padx=8)
        self._refresh_recent()

        srow = ttk.Frame(self, padding=(16, 0, 16, 0))
        srow.pack(fill="x")
        self.status = tk.StringVar(value="Hazır. Artist'te sahneyi açıp Stage/Tree dallarını açın, kaydedin, sonra 'Sahneyi tara'.")
        self.status_lbl = tk.Label(srow, textvariable=self.status, bg=BG, fg=MUTED, font=FONT, anchor="w")
        self.status_lbl.pack(side="left", fill="x", expand=True)
        self.progress = ttk.Progressbar(srow, length=160, mode="determinate")

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=16, pady=(6, 10))

        # ---- sol
        left = ttk.Frame(body)
        body.add(left, weight=3)
        srch = ttk.Frame(left)
        srch.pack(fill="x", pady=(0, 6))
        ttk.Label(srch, text="Ara").pack(side="left")
        self.search = tk.StringVar()
        self.search.trace_add("write", lambda *_: self._fill())
        self.search_entry = ttk.Entry(srch, textvariable=self.search)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(srch, text="Tümünü aç", style="Small.TButton", command=lambda: self._expand_all(True)).pack(side="left")
        ttk.Button(srch, text="Kapat", style="Small.TButton", command=lambda: self._expand_all(False)).pack(side="left", padx=(4, 0))

        self.nb = ttk.Notebook(left)
        self.nb.pack(fill="both", expand=True)
        self.tv_dir = self._tree(self.nb, ("Director", "Durum"), (260, 90))
        self.tv_con = self._tree(self.nb, ("Container", "Text / geometri"), (300, 220))
        self.nb.add(self.tv_dir.master, text="  Director'lar  ")
        self.nb.add(self.tv_con.master, text="  Container'lar  ")
        for tv, pick in ((self.tv_dir, self._on_pick_dir), (self.tv_con, self._on_pick_con)):
            tv.bind("<<TreeviewSelect>>", pick)
            tv.bind("<Double-1>", self._copy_selected_path)
            tv.bind("<Button-3>", self._context_menu)

        # ---- sag
        right = ttk.Frame(body, style="Card.TFrame", padding=14)
        body.add(right, weight=2)
        self.det_title = ttk.Label(right, text="Bir satır seçin", style="Card.TLabel", font=FONT_H)
        self.det_title.pack(anchor="w")
        self.det_sub = ttk.Label(right, text="Soldaki listeden bir director ya da container seçince komutları burada görürsünüz.\n"
                                             "Ctrl+F arama · çift tık yolu kopyalar · sağ tık komut menüsü",
                                 style="Card.TLabel", foreground=MUTED, wraplength=400, justify="left")
        self.det_sub.pack(anchor="w", pady=(2, 10))
        self.det_rows = ttk.Frame(right, style="Card.TFrame")
        self.det_rows.pack(fill="x")
        ttk.Separator(right).pack(fill="x", pady=10)
        ttk.Label(right, text="Komut gönder (yalnızca GET)", style="Card.TLabel", font=FONT_B).pack(anchor="w")
        row = ttk.Frame(right, style="Card.TFrame")
        row.pack(fill="x", pady=(4, 4))
        self.cmd = tk.StringVar(value="MAIN_SCENE*STAGE*DIRECTOR GET")
        ce = ttk.Entry(row, textvariable=self.cmd, font=MONO)
        ce.pack(side="left", fill="x", expand=True)
        ce.bind("<Return>", lambda e: self.on_send())
        ttk.Button(row, text="Gönder", command=self.on_send).pack(side="left", padx=(6, 0))
        self.out = tk.Text(right, height=6, wrap="word", font=MONO, bg="#f8f9fb", fg=TEXT, relief="flat",
                           highlightthickness=1, highlightbackground=LINE, padx=8, pady=6)
        self.out.pack(fill="both", expand=True)

        foot = ttk.Frame(right, style="Card.TFrame")
        foot.pack(fill="x", pady=(8, 0))
        self.btn_md = ttk.Button(foot, text="Şablon (.md)", command=self.on_open_md, state="disabled")
        self.btn_md.pack(side="left")
        self.btn_cs = ttk.Button(foot, text="C# sabitleri üret", command=self.on_csharp, state="disabled")
        self.btn_cs.pack(side="left", padx=6)
        self.btn_vs = ttk.Button(foot, text="VizScript kopyala", command=self.on_copy_vizscript, state="disabled")
        self.btn_vs.pack(side="left")
        self.btn_closed = ttk.Button(foot, text="Kapalı director'ları kopyala", command=self.on_copy_closed)
        ttk.Button(foot, text="scenes klasörü", command=lambda: self._open(SCENES_DIR)).pack(side="right")

        self.menu = tk.Menu(self, tearoff=0, font=FONT)

    def _tree(self, parent, cols, widths):
        frame = ttk.Frame(parent)
        tv = ttk.Treeview(frame, columns=("c1",), show="tree headings", selectmode="browse")
        tv.heading("#0", text=cols[0], anchor="w")
        tv.heading("c1", text=cols[1], anchor="w")
        tv.column("#0", width=widths[0], stretch=True)
        tv.column("c1", width=widths[1], stretch=True)
        vs = ttk.Scrollbar(frame, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=vs.set)
        tv.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")
        tv.tag_configure("closed", foreground=WARN)
        tv.tag_configure("muted", foreground=MUTED)
        return tv

    # ---------------------------------------------------------- helpers --
    def _client(self):
        return VizClient("127.0.0.1", 6100)

    def _open(self, path):
        os.makedirs(path, exist_ok=True)
        os.startfile(path)

    def _log(self, text):
        self.out.delete("1.0", "end")
        self.out.insert("1.0", text)

    def _set_status(self, text, color=MUTED):
        self.status.set(text)
        self.status_lbl.configure(fg=color)

    def _copy(self, text, what="Panoya kopyalandı"):
        self.clipboard_clear()
        self.clipboard_append(text)
        self._set_status(f"{what}: {text[:90]}" if len(text) < 200 else f"{what} ({len(text.splitlines())} satır)", OK)

    def _on_close(self):
        self.state_.update({"geometry": self.geometry(), "layer": self.layer.get(), "details": self.details.get()})
        save_state(self.state_)
        self.destroy()

    def _check_engine_async(self):
        def work():
            try:
                with self._client() as c:
                    name = c.try_send("MAIN_SCENE*NAME GET") or "(boş)"
                self.after(0, lambda: self.engine_dot.configure(fg=OK, text=f"● engine · {name}"))
            except OSError:
                self.after(0, lambda: self.engine_dot.configure(fg=MUTED, text="● engine kapalı"))
        threading.Thread(target=work, daemon=True).start()

    # ---------------------------------------------------------- recent --
    def _refresh_recent(self):
        m = tk.Menu(self.recent_btn, tearoff=0, font=FONT)
        recent = self.state_.get("recent", [])
        if not recent:
            m.add_command(label="(henüz yok)", state="disabled")
        for r in recent:
            label = f"{os.path.basename(r['path'])}  ›  {r['scene']}" if r.get("scene") else os.path.basename(r["path"])
            m.add_command(label=label, command=lambda r=r: self.on_via(r["path"], r.get("scene")))
        self.recent_btn.configure(menu=m)

    def _remember(self, path, scene):
        recent = [r for r in self.state_.get("recent", []) if not (r["path"] == path and r.get("scene") == scene)]
        recent.insert(0, {"path": path, "scene": scene})
        self.state_["recent"] = recent[:8]
        save_state(self.state_)
        self._refresh_recent()

    # ---------------------------------------------------------- detail --
    def _detail(self, title, sub, rows):
        self.det_title.configure(text=title)
        self.det_sub.configure(text=sub)
        for w in self.det_rows.winfo_children():
            w.destroy()
        for i, (lab, val) in enumerate(rows):
            ttk.Label(self.det_rows, text=lab, style="Card.TLabel", foreground=MUTED).grid(row=i, column=0, sticky="nw", pady=2)
            e = tk.Entry(self.det_rows, font=MONO, relief="flat", bg="#f8f9fb", fg=TEXT, readonlybackground="#f8f9fb")
            e.insert(0, val)
            e.configure(state="readonly")
            e.grid(row=i, column=1, sticky="ew", padx=8, pady=2)
            ttk.Button(self.det_rows, text="Kopyala", style="Small.TButton",
                       command=lambda v=val: self._copy(v)).grid(row=i, column=2, pady=2)
        self.det_rows.columnconfigure(1, weight=1)

    # ---------------------------------------------------------- actions --
    def on_send(self):
        try:
            with self._client() as c:
                self._log(c.send(self.cmd.get()) or "(boş cevap)")
        except VizCommandBlocked as e:
            self._log(f"REDDEDİLDİ: {e}")
        except VizError as e:
            self._log(f"ENGINE HATASI: {e}")
        except OSError as e:
            self._log(f"Bağlantı yok: {e}")

    def on_scan(self):
        self.btn_scan.configure(state="disabled")
        self._set_status("Taranıyor…")
        self.progress.configure(value=0, maximum=1)
        self.progress.pack(side="right")
        layer, details = self.layer.get(), self.details.get()

        def prog(i, n):
            self.after(0, lambda: (self.progress.configure(maximum=n, value=i),
                                   self._set_status(f"Detay okunuyor… {i}/{n} container")))

        def work():
            try:
                with self._client() as c:
                    model = build_scene_model(c, layer, details, progress=prog)
                jp, mp = write_outputs(model, SCENES_DIR)
                self.after(0, lambda: self._loaded(model, mp, "live"))
            except Exception as e:  # noqa
                self.after(0, lambda: self._fail(e))
        threading.Thread(target=work, daemon=True).start()

    def on_via(self, path=None, scene=None):
        path = path or filedialog.askopenfilename(title=".via dosyası seç",
                                                  initialdir=self.state_.get("via_dir", os.path.expanduser("~")),
                                                  filetypes=[("Viz arşivi", "*.via"), ("Tümü", "*.*")])
        if not path:
            return
        self.state_["via_dir"] = os.path.dirname(path)
        try:
            scenes = list_scenes(path)
            if len(scenes) > 1 and scene is None:
                scene = self._choose_scene(scenes, os.path.basename(path))
                if scene is None:
                    return
            model = read_via(path, scene)
        except (ViaError, OSError) as e:
            self._fail(e)
            return
        jp, mp = write_outputs(model, SCENES_DIR)
        self._remember(path, scene)
        self._loaded(model, mp, "via")

    def _choose_scene(self, scenes, title):
        dlg = tk.Toplevel(self)
        dlg.title(f"{title}: sahne seç ({len(scenes)})")
        dlg.configure(bg=BG)
        dlg.transient(self)
        dlg.grab_set()
        dlg.geometry("480x540")
        ttk.Label(dlg, text="Arşivdeki sahneler", style="H.TLabel").pack(anchor="w", padx=14, pady=(12, 4))
        flt = tk.StringVar()
        fe = ttk.Entry(dlg, textvariable=flt)
        fe.pack(fill="x", padx=14)
        frame = ttk.Frame(dlg)
        frame.pack(fill="both", expand=True, padx=14, pady=8)
        lb = tk.Listbox(frame, font=FONT, activestyle="none", selectbackground=ACCENT, relief="flat",
                        highlightthickness=1, highlightbackground=LINE)
        vs = ttk.Scrollbar(frame, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=vs.set)
        lb.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")

        def refill(*_):
            q = flt.get().lower()
            lb.delete(0, "end")
            for s in scenes:
                if q in s.lower():
                    lb.insert("end", s)
            if lb.size():
                lb.selection_set(0)
        flt.trace_add("write", refill)
        refill()
        result = {"scene": None}

        def ok(*_):
            sel = lb.curselection()
            if sel:
                result["scene"] = lb.get(sel[0])
            dlg.destroy()
        btns = ttk.Frame(dlg)
        btns.pack(fill="x", padx=14, pady=(0, 12))
        ttk.Button(btns, text="Aç", style="Primary.TButton", command=ok).pack(side="right")
        ttk.Button(btns, text="Vazgeç", command=dlg.destroy).pack(side="right", padx=8)
        lb.bind("<Double-1>", ok)
        for w in (lb, fe):
            w.bind("<Return>", ok)
        fe.focus_set()
        self.wait_window(dlg)
        return result["scene"]

    def _fail(self, e):
        self.btn_scan.configure(state="normal")
        self.progress.pack_forget()
        self._set_status(f"Başarısız: {e}", ERR)
        messagebox.showerror("Hata", str(e))

    def _loaded(self, model, mp, source):
        self.model, self.last_md, self.last_source = model, mp, source
        self.btn_scan.configure(state="normal")
        self.progress.pack_forget()
        for b in (self.btn_md, self.btn_cs, self.btn_vs):
            b.configure(state="normal")
        s = model["scene"]
        closed = [d for d in model["directors"] if d.get("open") is False]
        msg = f"{s['name']} · {s['container_count']} container, {s['director_count']} director · {os.path.basename(mp)}"
        color = OK
        if closed:
            msg += f" · {len(closed)} director KAPALI"
            color = WARN
            self.btn_closed.pack(side="left", padx=6)
        else:
            self.btn_closed.pack_forget()
        self._set_status(msg, color)
        self._log("\n".join(model["warnings"]) or "Uyarı yok.")
        self.search.set("")
        self._fill()
        self._detail(s["name"], f"{s['container_count']} container · {s['director_count']} director · kaynak: {s.get('source', 'canlı engine')}", [
            ("Sahne", s["name"]),
        ])

    def on_open_md(self):
        if self.last_md:
            os.startfile(self.last_md)

    def on_csharp(self):
        if not self.model:
            return
        p = write_csharp(self.model, SCENES_DIR)
        self._set_status(f"C# sabit dosyası yazıldı: {p}", OK)
        if messagebox.askyesno("C# sabitleri", f"Yazıldı:\n{p}\n\nDosyayı şimdi açmak ister misiniz?"):
            os.startfile(p)

    def on_copy_vizscript(self):
        if not self.model:
            return
        md = render_markdown(self.model)
        vb = md.split("```vb")[1].split("```")[0].strip() if "```vb" in md else ""
        self._copy(vb, "VizScript iskeleti kopyalandı")

    def on_copy_closed(self):
        if not self.model:
            return
        closed = [d["name_path"] for d in self.model["directors"] if d.get("open") is False]
        self._copy("\n".join(closed), "Kapalı director listesi kopyalandı")

    # ------------------------------------------------------------- fill --
    def _fill(self):
        for tv in (self.tv_dir, self.tv_con):
            tv.delete(*tv.get_children())
        self._dir_index, self._con_index = {}, {}
        if not self.model:
            return
        q = self.search.get().strip().lower()

        by_path = {}
        for d in self.model["directors"]:
            if q and q not in f"{d['name']} {d['name_path']}".lower():
                continue
            parent_path = d["name_path"].rsplit("$", 1)[0] if d["name_path"].count("$") > 1 else ""
            parent = by_path.get(parent_path, "")
            state = {True: "açık", False: "KAPALI", None: ""}[d.get("open")]
            tag = ("closed",) if d.get("open") is False else ()
            iid = self.tv_dir.insert(parent, "end", text=d["name"], values=(state,), open=True, tags=tag)
            by_path[d["name_path"]] = iid
            self._dir_index[iid] = d

        def matches(c):
            return q in f"{c['name']} {c['name_path']} {c.get('text', '')}".lower()

        def subtree_matches(nodes):
            return any(matches(c) or subtree_matches(c["children"]) for c in nodes)

        def walk(nodes, parent):
            for c in nodes:
                if q and not (matches(c) or subtree_matches(c["children"])):
                    continue
                tag = ("muted",) if c.get("active") is False else ()
                info = c.get("text") or ", ".join(c.get("plugins", [])[:3])
                iid = self.tv_con.insert(parent, "end", text=c["name"], values=(info,), open=bool(q), tags=tag)
                self._con_index[iid] = c
                walk(c["children"], iid)
        walk(self.model["tree"], "")

    def _expand_all(self, open_):
        tv = self.tv_dir if self.nb.index(self.nb.select()) == 0 else self.tv_con

        def rec(parent):
            for iid in tv.get_children(parent):
                tv.item(iid, open=open_)
                rec(iid)
        rec("")

    # ------------------------------------------------------------ picks --
    def _current(self):
        """(tur, kayit) : secili director veya container."""
        if self.nb.index(self.nb.select()) == 0:
            sel = self.tv_dir.selection()
            return ("dir", self._dir_index.get(sel[0])) if sel else (None, None)
        sel = self.tv_con.selection()
        return ("con", self._con_index.get(sel[0])) if sel else (None, None)

    def _cmds_for(self, kind, rec):
        L = self.layer.get()
        p = rec["name_path"]
        if kind == "dir":
            return [("Yol", p),
                    ("START", f"{L}*STAGE*DIRECTOR*{p} START"),
                    ("CONTINUE", f"{L}*STAGE*DIRECTOR*{p} CONTINUE"),
                    ("STOP", f"{L}*STAGE*DIRECTOR*{p} STOP"),
                    ("Başa sar", f"{L}*STAGE*DIRECTOR*{p}*GOTO_TRIO 0"),
                    ("VizScript", f'Stage.FindDirector("{p.lstrip("$").replace("$", "/")}").StartAnimation()')]
        return [("Yol", p),
                ("TEXT SET", f"{L}*TREE*{p}*GEOM*TEXT SET metin"),
                ("ACTIVE SET", f"{L}*TREE*{p}*ACTIVE SET 1"),
                ("POSITION", f"{L}*TREE*{p}*TRANSFORMATION*POSITION SET 0 0 0"),
                ("IMAGE SET", f"{L}*TREE*{p}*IMAGE SET IMAGE*/yol/resim"),
                ("VizScript", f'Scene.FindContainer("{rec["name"]}").Geometry.Text = "metin"')]

    def _on_pick_dir(self, _):
        kind, d = self._current()
        if not d:
            return
        anim = []
        for a in d["animated"]:
            if a["container"]:
                anim.append(f"{a['container']} ({'/'.join(a['channels'])})" if a["channels"] else a["container"])
            else:
                anim.append("/".join(a["channels"]))
        bits = []
        if d.get("sub_directors"):
            bits.append("alt director: " + ", ".join(d["sub_directors"]))
        if d.get("open") is False:
            bits.append("Artist'te KAPALI; içeriği okunamadı. Açıp kaydedin, tekrar tarayın.")
        else:
            bits.append("oynattığı: " + (", ".join(anim) if anim else "(bilgi yok)"))
        self._detail(d["name"], "\n".join(bits), self._cmds_for("dir", d))
        self.cmd.set(f"{self.layer.get()}*STAGE*DIRECTOR*{d['name_path']}*NAME GET")

    def _on_pick_con(self, _):
        kind, c = self._current()
        if not c:
            return
        bits = [f"#{c['id']}"]
        if c.get("active") is not None:
            bits.append("aktif" if c["active"] else "PASİF")
        if c.get("plugins"):
            bits.append("geometri/plugin: " + ", ".join(c["plugins"]))
        if c.get("text"):
            bits.append(f'text: "{c["text"]}"')
        n_kids = len(c.get("children", []))
        if n_kids:
            bits.append(f"{n_kids} alt container")
        self._detail(c["name"], " · ".join(bits), self._cmds_for("con", c))
        self.cmd.set(f"{self.layer.get()}*TREE*{c['name_path']}*GEOM*TEXT GET")

    def _copy_selected_path(self, _=None):
        kind, rec = self._current()
        if rec:
            self._copy(rec["name_path"], "Yol kopyalandı")

    def _context_menu(self, event):
        tv = event.widget
        iid = tv.identify_row(event.y)
        if not iid:
            return
        tv.selection_set(iid)
        tv.focus(iid)
        kind, rec = self._current()
        if not rec:
            return
        self.menu.delete(0, "end")
        for lab, val in self._cmds_for(kind, rec):
            self.menu.add_command(label=f"{lab} kopyala", command=lambda v=val: self._copy(v))
        self.menu.add_separator()
        self.menu.add_command(label="Adı kopyala", command=lambda: self._copy(rec["name"]))
        self.menu.tk_popup(event.x_root, event.y_root)


if __name__ == "__main__":
    App().mainloop()
