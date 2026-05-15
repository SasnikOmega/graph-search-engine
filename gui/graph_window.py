"""Matplotlib graph preview of exported graph data."""

from __future__ import annotations

from typing import Any

import networkx as nx
import wx
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.figure import Figure

from gui import a11y


class GraphPreviewFrame(wx.Frame):
    """Separate window: optional summary strip, or full-screen plot only."""

    MAX_NODES = 500

    def __init__(
        self,
        parent: wx.Window | None,
        title: str,
        export_data: dict[str, Any],
        *,
        minimal: bool = False,
    ) -> None:
        self._minimal = minimal
        if minimal:
            super().__init__(parent, title="Граф", size=(960, 720), style=wx.DEFAULT_FRAME_STYLE)
        else:
            super().__init__(parent, title=title, size=(960, 720), style=wx.DEFAULT_FRAME_STYLE)

        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)

        self._info: wx.StaticText | None = None
        if not minimal:
            self._info = wx.StaticText(panel, label="")
            a11y.announce(
                self._info,
                "Сводка по графу",
                "Сколько вершин и рёбер отображено.",
            )
            root.Add(self._info, 0, wx.EXPAND | wx.ALL, 6)

        self.figure = Figure(figsize=(7, 6), dpi=100)
        self.canvas = FigureCanvas(panel, wx.ID_ANY, self.figure)
        a11y.announce(
            self.canvas,
            "Область рисования графа",
            "Схема вершин и направленных рёбер. Escape — закрыть окно.",
        )
        root.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 4)

        panel.SetSizer(root)
        self._build_graph(export_data)

        self.canvas.SetFocus()
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        if minimal:
            self.Bind(wx.EVT_CLOSE, self._on_close_minimal)
            wx.CallAfter(self._enter_fullscreen)

    def _enter_fullscreen(self) -> None:
        try:
            self.ShowFullScreen(
                True,
                wx.FULLSCREEN_NOSTATUSBAR
                | wx.FULLSCREEN_NOTOOLBAR
                | wx.FULLSCREEN_NOBORDER,
            )
        except Exception:
            self.Maximize(True)

    def _on_close_minimal(self, evt: wx.CloseEvent) -> None:
        if self.IsFullScreen():
            self.ShowFullScreen(False)
        evt.Skip()

    def _on_char_hook(self, evt: wx.KeyEvent) -> None:
        if evt.GetKeyCode() == wx.WXK_ESCAPE:
            self.Close()
            return
        evt.Skip()

    def _build_graph(self, data: dict[str, Any]) -> None:
        nodes = data.get("nodes") or []
        edges = data.get("edges") or []
        n = len(nodes)
        if n > self.MAX_NODES:
            nodes = nodes[: self.MAX_NODES]
            shown_ids = {
                str(x.get("id") or x.get("element_id") or "") for x in nodes
            }
            edges = [
                e
                for e in edges
                if str(e.get("source")) in shown_ids and str(e.get("target")) in shown_ids
            ]
            msg = (
                f"Показаны первые {self.MAX_NODES} из {n} вершин "
                f"(и соответствующие рёбра) — для ускорения отображения."
            )
        else:
            msg = f"Вершин: {n}, рёбер: {len(edges)}."

        if self._info is not None:
            self._info.SetLabel(msg)

        G = nx.DiGraph()
        for node in nodes:
            nid = str(node.get("id") or node.get("element_id") or "")
            if not nid:
                continue
            labels = node.get("labels") or []
            props = node.get("properties") or {}
            name = props.get("name") or props.get("title") or (labels[0] if labels else nid)
            short = str(name)[:18] + ("…" if len(str(name)) > 18 else "")
            G.add_node(nid, label=short)

        for e in edges:
            s, t = str(e.get("source", "")), str(e.get("target", ""))
            typ = str(e.get("type", "REL"))
            if s in G and t in G:
                G.add_edge(s, t, label=typ[:8])

        ax = self.figure.subplots()
        ax.set_axis_off()
        if G.number_of_nodes() == 0:
            ax.text(
                0.5,
                0.5,
                "Нет вершин для отображения",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )
            self.canvas.draw()
            return

        pos = nx.spring_layout(G, seed=42, k=0.8 / max(1, (G.number_of_nodes() ** 0.5)))
        nx.draw_networkx_nodes(G, pos, ax=ax, node_size=500, node_color="#4a90d9")
        nx.draw_networkx_edges(
            G,
            pos,
            ax=ax,
            arrows=True,
            arrowsize=12,
            width=1.0,
            edge_color="#333333",
        )
        labels = {nid: d.get("label", nid) for nid, d in G.nodes(data=True)}
        nx.draw_networkx_labels(G, pos, labels=labels, font_size=8, ax=ax)
        edge_labels = {(u, v): d.get("label", "") for u, v, d in G.edges(data=True)}
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=6, ax=ax)
        self.canvas.draw()
