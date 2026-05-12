"""Primary window: browse nodes and relationships, manage databases, open graph view."""

from __future__ import annotations

import json
import threading
import webbrowser
from pathlib import Path
from typing import Any, Callable

import wx

from gui import a11y
from gui.api_client import ApiClient, ApiError
from gui.database_dialog import DatabaseManagerDialog
from gui.edit_dialogs import NodeEditDialog, RelCreateDialog
from gui.errors import show_error
from gui.graph_window import GraphPreviewFrame
from gui.persist import load_config, save_config
from gui.settings_dialog import SettingsDialog


class MainFrame(wx.Frame):
    def __init__(self) -> None:
        super().__init__(
            None,
            title="Graph engine — desktop client",
            size=(980, 640),
            style=wx.DEFAULT_FRAME_STYLE,
        )
        cfg = load_config()
        self._base_url = str(cfg["base_url"])
        self._timeout = float(cfg["timeout"])
        self._client = ApiClient(
            self._base_url,
            database=str(cfg["database"]),
            timeout=self._timeout,
        )

        self.CreateStatusBar(2)
        self.SetStatusWidths([-2, -1])
        self.SetStatusText("Ready.", 0)
        self.SetStatusText("", 1)

        self._build_menu()
        self._build_body()

        self.Bind(wx.EVT_CLOSE, self._on_close)
        self._async(self._bootstrap, self._after_bootstrap, "Could not reach server")

    def _build_menu(self) -> None:
        bar = wx.MenuBar()
        file_m = wx.Menu()
        mi_settings = file_m.Append(wx.ID_ANY, "Connection &settings…\tCtrl+,")
        file_m.AppendSeparator()
        mi_exit = file_m.Append(wx.ID_EXIT, "E&xit\tAlt+F4")
        bar.Append(file_m, "&File")

        db_m = wx.Menu()
        mi_db = db_m.Append(wx.ID_ANY, "&Manage databases…")
        mi_refresh = db_m.Append(wx.ID_ANY, "&Refresh data\tCtrl+R")
        bar.Append(db_m, "&Database")

        graph_m = wx.Menu()
        mi_graph_sum = graph_m.Append(wx.ID_ANY, "Visualize graph (&with summary)…")
        mi_graph_min = graph_m.Append(wx.ID_ANY, "Visualize graph (&minimal fullscreen)…")
        graph_m.AppendSeparator()
        mi_imp = graph_m.Append(wx.ID_ANY, "&Import graph from file…")
        mi_exp = graph_m.Append(wx.ID_ANY, "&Export graph to file…")
        bar.Append(graph_m, "&Graph")

        help_m = wx.Menu()
        mi_docs = help_m.Append(wx.ID_ANY, "&API docs in browser")
        mi_about = help_m.Append(wx.ID_ABOUT, "&About")
        bar.Append(help_m, "&Help")
        self.SetMenuBar(bar)

        self.Bind(wx.EVT_MENU, self._on_settings, mi_settings)
        self.Bind(wx.EVT_MENU, lambda e: self.Close(), mi_exit)
        self.Bind(wx.EVT_MENU, self._on_manage_db, mi_db)
        self.Bind(wx.EVT_MENU, self._on_refresh_all, mi_refresh)
        self.Bind(wx.EVT_MENU, lambda e: self._start_visualize(False), mi_graph_sum)
        self.Bind(wx.EVT_MENU, lambda e: self._start_visualize(True), mi_graph_min)
        self.Bind(wx.EVT_MENU, self._on_import_graph_file, mi_imp)
        self.Bind(wx.EVT_MENU, self._on_export_graph_file, mi_exp)
        self.Bind(wx.EVT_MENU, self._on_open_docs, mi_docs)
        self.Bind(wx.EVT_MENU, self._on_about, mi_about)

        accel = wx.AcceleratorTable(
            [
                (wx.ACCEL_CTRL, ord(","), mi_settings.GetId()),
                (wx.ACCEL_CTRL, ord("R"), mi_refresh.GetId()),
            ]
        )
        self.SetAcceleratorTable(accel)

    def _build_body(self) -> None:
        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)

        self._url_display = wx.TextCtrl(
            panel,
            value=self._base_url,
            style=wx.TE_READONLY | wx.BORDER_SUNKEN,
        )
        url_outer = wx.BoxSizer(wx.HORIZONTAL)
        url_col = wx.BoxSizer(wx.VERTICAL)
        a11y.stack_labeled_control(
            panel,
            url_col,
            caption="Current API base URL (read-only field below)",
            body=(
                "This mirrors the address used for REST calls. "
                "To change it, use the Settings button or File → Connection settings."
            ),
            control=self._url_display,
            control_proportion=0,
        )
        url_outer.Add(url_col, 1, wx.EXPAND)
        btn_settings = wx.Button(panel, label="Settings…")
        a11y.announce(btn_settings, "Open connection settings", "Change base URL and timeout.")
        url_outer.Add(btn_settings, 0, wx.ALIGN_BOTTOM | wx.LEFT, 8)
        root.Add(url_outer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.Bind(wx.EVT_BUTTON, self._on_settings, btn_settings)

        db_heading = wx.StaticText(
            panel,
            label="Active Neo4j database (drop-down list below)",
        )
        db_heading.SetName("Active Neo4j database (heading)")
        db_heading.SetHelpText(
            "Choose which database on the server receives all node and relationship requests."
        )
        root.Add(db_heading, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        db_hint = wx.StaticText(
            panel,
            label="Use Manage to list or create databases, then pick one here.",
        )
        db_hint.Wrap(600)
        root.Add(db_hint, 0, wx.LEFT | wx.RIGHT, 8)

        row2 = wx.BoxSizer(wx.HORIZONTAL)
        self._db_choice = wx.ComboBox(
            panel,
            style=wx.CB_READONLY,
            choices=[],
        )
        a11y.announce(
            self._db_choice,
            "Active Neo4j database. Use Manage to list or create databases, then pick one here.",
            "Drop-down list of database names returned by the server.",
        )
        row2.Add(self._db_choice, 1, wx.EXPAND)
        btn_db = wx.Button(panel, label="Manage…")
        a11y.announce(btn_db, "Manage databases", "List, create, or pick the active database.")
        row2.Add(btn_db, 0, wx.LEFT, 6)
        btn_refresh = wx.Button(panel, label="Refresh")
        a11y.announce(btn_refresh, "Refresh lists", "Reload nodes and relationships from the server.")
        row2.Add(btn_refresh, 0, wx.LEFT, 6)
        root.Add(row2, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self.Bind(wx.EVT_BUTTON, self._on_manage_db, btn_db)
        self.Bind(wx.EVT_BUTTON, self._on_refresh_all, btn_refresh)
        self.Bind(wx.EVT_COMBOBOX, self._on_db_changed, self._db_choice)

        nb = wx.Notebook(panel)
        a11y.announce(nb, "Data tabs", "Switch between nodes, relationships, and server status.")
        self._nodes_lc = wx.ListCtrl(nb, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        for i, (title, w) in enumerate(
            [("Element ID", 240), ("Labels", 160), ("Properties", 520)]
        ):
            self._nodes_lc.InsertColumn(i, title, width=w)
        a11y.announce(self._nodes_lc, "Nodes table", "Select a node to edit or delete.")

        self._rels_lc = wx.ListCtrl(nb, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        for i, (title, w) in enumerate(
            [
                ("Relationship ID", 220),
                ("Type", 100),
                ("Start node", 200),
                ("End node", 200),
                ("Properties", 360),
            ]
        ):
            self._rels_lc.InsertColumn(i, title, width=w)
        a11y.announce(self._rels_lc, "Relationships table", "Select a relationship to delete.")

        status_panel = wx.Panel(nb)
        sp = wx.BoxSizer(wx.VERTICAL)
        self._health_text = wx.TextCtrl(
            status_panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
        )
        a11y.stack_labeled_control(
            status_panel,
            sp,
            caption="Health check response (read-only text area below)",
            body="JSON returned by GET /health after the last check. Use the button to run a new check.",
            control=self._health_text,
            control_proportion=1,
        )
        btn_h = wx.Button(status_panel, label="Run health check now")
        a11y.announce(btn_h, "Run health check", "Calls GET /health on the API.")
        sp.Add(btn_h, 0, wx.ALL, 6)
        status_panel.SetSizer(sp)
        self.Bind(wx.EVT_BUTTON, self._on_health, btn_h)

        nb.AddPage(self._nodes_lc, "Nodes", select=True)
        nb.AddPage(self._rels_lc, "Relationships")
        nb.AddPage(status_panel, "Server status")
        root.Add(nb, 1, wx.EXPAND | wx.ALL, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in (
            ("Add node…", self._on_add_node),
            ("Edit selected node…", self._on_edit_node),
            ("Delete selected node…", self._on_delete_node),
            ("Add relationship…", self._on_add_rel),
            ("Delete selected relationship…", self._on_delete_rel),
        ):
            b = wx.Button(panel, label=label)
            btn_row.Add(b, 0, wx.ALL, 4)
            self.Bind(wx.EVT_BUTTON, handler, b)
        root.Add(btn_row, 0, wx.ALIGN_LEFT | wx.LEFT, 4)

        self._detach_delete = wx.CheckBox(panel, label="When deleting a node, detach (remove) connected relationships first")
        a11y.announce(
            self._detach_delete,
            "Detach relationships when deleting node",
            "Maps to the API detach query parameter on node delete.",
        )
        self._detach_delete.SetValue(True)
        root.Add(self._detach_delete, 0, wx.ALL, 8)

        panel.SetSizer(root)

    def _on_close(self, evt: wx.CloseEvent) -> None:
        self._client.close()
        evt.Skip()

    def _on_db_changed(self, _: wx.CommandEvent) -> None:
        name = self._db_choice.GetStringSelection()
        if name:
            self._client.set_database(name)
            save_config(
                {
                    "base_url": self._base_url,
                    "database": name,
                    "timeout": self._timeout,
                }
            )
            self._on_refresh_all(None)

    def _on_settings(self, _: wx.CommandEvent | None) -> None:
        dlg = SettingsDialog(self, base_url=self._base_url, timeout=self._timeout)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        url, timeout = dlg.get_values()
        dlg.Destroy()
        if not url.startswith("http://") and not url.startswith("https://"):
            wx.MessageBox(
                "Base URL should start with http:// or https://",
                "Validation",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            return
        self._base_url = url
        self._timeout = timeout
        self._url_display.SetValue(url)
        db = self._db_choice.GetStringSelection() or self._client.database
        self._client.close()
        self._client = ApiClient(url, database=db, timeout=timeout)
        save_config({"base_url": url, "database": db, "timeout": timeout})
        self._async(self._bootstrap, self._after_bootstrap, "Could not reach server")

    def _on_manage_db(self, _: wx.CommandEvent | None) -> None:
        dlg = DatabaseManagerDialog(self, self._client)
        rc = dlg.ShowModal()
        name = dlg.get_selected_database()
        dlg.Destroy()
        if rc == wx.ID_OK and name:
            self._client.set_database(name)
            save_config(
                {
                    "base_url": self._base_url,
                    "database": name,
                    "timeout": self._timeout,
                }
            )
        self._async(self._load_db_names, self._apply_db_names, "Could not list databases")

    def _on_refresh_all(self, _: wx.CommandEvent | None) -> None:
        self._async(self._load_lists, self._apply_lists, "Could not load graph data")

    def _on_health(self, _: wx.CommandEvent | None) -> None:
        self._async(lambda: self._client.health(), self._apply_health, "Health check failed")

    def _start_visualize(self, minimal: bool) -> None:
        def loaded(data: dict[str, Any]) -> None:
            self._open_graph_window(data, minimal=minimal)

        self._async(
            lambda: self._client.graph_export(),
            loaded,
            "Could not export graph",
        )

    def _open_graph_window(
        self,
        data: dict[str, Any],
        *,
        minimal: bool = False,
    ) -> None:
        title = "Graph" if minimal else "Graph visualization"
        win = GraphPreviewFrame(self, title, data, minimal=minimal)
        win.Show()

    def _show_import_ok(self, stats: dict[str, Any]) -> None:
        n = stats.get("nodes_created", "?")
        m = stats.get("edges_created", "?")
        dlg = wx.MessageDialog(
            self,
            f"Nodes processed: {n}\nEdges processed: {m}",
            "Import succeeded",
            wx.OK | wx.ICON_INFORMATION,
        )
        dlg.ShowModal()
        dlg.Destroy()

    def _show_import_failed(self, err: Exception) -> None:
        dlg = wx.MessageDialog(
            self,
            str(err) or err.__class__.__name__,
            "Import failed",
            wx.OK | wx.ICON_ERROR,
        )
        body = getattr(err, "body", None)
        if body:
            dlg.SetExtendedMessage(str(body)[:4000])
        dlg.ShowModal()
        dlg.Destroy()

    def _on_import_graph_file(self, _: wx.CommandEvent) -> None:
        fd = wx.FileDialog(
            self,
            "Import graph file",
            wildcard="JSON graph (*.json)|*.json|GraphML (*.graphml;*.xml)|*.graphml;*.xml|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        if fd.ShowModal() != wx.ID_OK:
            fd.Destroy()
            return
        path = Path(fd.GetPath())
        fd.Destroy()

        mode_dlg = wx.SingleChoiceDialog(
            self,
            "Choose how the imported data is merged into the active database.",
            "Import mode",
            [
                "Append: keep existing nodes and relationships, add new ones",
                "Replace: delete all nodes and relationships in this database, then import",
            ],
            0,
        )
        if mode_dlg.ShowModal() != wx.ID_OK:
            mode_dlg.Destroy()
            return
        mode = "replace" if mode_dlg.GetSelection() == 1 else "append"
        mode_dlg.Destroy()

        def worker() -> tuple[dict[str, Any] | None, Exception | None]:
            try:
                ext = path.suffix.lower()
                if ext == ".json":
                    doc = json.loads(path.read_text(encoding="utf-8"))
                    if not isinstance(doc, dict) or "nodes" not in doc or "edges" not in doc:
                        return None, ValueError("JSON must be an object with 'nodes' and 'edges' arrays.")
                    return self._client.graph_import_json(doc, mode=mode), None
                if ext in (".graphml", ".xml"):
                    xml = path.read_text(encoding="utf-8")
                    return self._client.graph_import_graphml(xml, mode=mode), None
                return None, ValueError("Unsupported file type. Use .json or .graphml (or .xml GraphML).")
            except Exception as e:
                return None, e

        def done(pack: tuple[dict[str, Any] | None, Exception | None]) -> None:
            stats, err = pack
            if err is not None:
                self._show_import_failed(err)
                return
            if stats is not None:
                self._show_import_ok(stats)
            self._on_refresh_all(None)

        self._async(worker, done, "Import failed")

    def _on_export_graph_file(self, _: wx.CommandEvent) -> None:
        fd = wx.FileDialog(
            self,
            "Export graph to file",
            wildcard="JSON (*.json)|*.json|GraphML (*.graphml)|*.graphml|GEXF (*.gexf)|*.gexf",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        if fd.ShowModal() != wx.ID_OK:
            fd.Destroy()
            return
        out_path = Path(fd.GetPath())
        fd.Destroy()

        name = out_path.name.lower()
        if name.endswith(".json"):
            fmt = "json"
        elif name.endswith(".graphml"):
            fmt = "graphml"
        elif name.endswith(".gexf"):
            fmt = "gexf"
        else:
            wx.MessageBox(
                "The file name must end with .json, .graphml, or .gexf.",
                "Export",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            return

        def worker() -> tuple[bytes, Exception | None]:
            try:
                return self._client.graph_export_bytes(fmt), None
            except Exception as e:
                return b"", e

        def done(pack: tuple[bytes, Exception | None]) -> None:
            blob, err = pack
            if err is not None:
                self._show_import_failed(err)
                return
            try:
                out_path.write_bytes(blob)
            except OSError as e:
                self._show_import_failed(e)
                return
            wx.MessageBox(
                f"Graph saved to:\n{out_path}",
                "Export succeeded",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )

        self._async(worker, done, "Export failed")

    def _on_open_docs(self, _: wx.CommandEvent) -> None:
        url = self._base_url.rstrip("/") + "/docs"
        webbrowser.open(url)

    def _on_about(self, _: wx.CommandEvent) -> None:
        wx.MessageBox(
            "Graph engine desktop client.\n\n"
            "Talks to the FastAPI backend over HTTP. "
            "Connection settings are stored in the file .graph_engine_gui.json in your user profile folder.\n\n"
            "Shortcuts: Ctrl+comma opens connection settings; Ctrl+R refreshes node and relationship lists.",
            "About",
            wx.OK | wx.ICON_INFORMATION,
            self,
        )

    def _on_add_node(self, _: wx.CommandEvent) -> None:
        dlg = NodeEditDialog(self, element_id=None, labels=["GraphNode"], properties={}, is_new=True)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        try:
            labels = dlg.get_labels()
            props = dlg.get_properties()
        except json.JSONDecodeError as e:
            dlg.Destroy()
            show_error(self, "Invalid JSON", e)
            return
        dlg.Destroy()
        if not labels:
            wx.MessageBox("Enter at least one label.", "Validation", wx.OK | wx.ICON_INFORMATION, self)
            return
        self._async(
            lambda: self._client.node_create(labels, props),
            lambda _: self._on_refresh_all(None),
            "Could not create node",
        )

    def _on_edit_node(self, _: wx.CommandEvent) -> None:
        idx = self._nodes_lc.GetFirstSelected()
        if idx < 0:
            wx.MessageBox("Select a node first.", "Nodes", wx.OK | wx.ICON_INFORMATION, self)
            return
        eid = self._nodes_lc.GetItemText(idx, 0)

        def open_editor(data: dict[str, Any]) -> None:
            dlg = NodeEditDialog(
                self,
                element_id=data.get("element_id"),
                labels=list(data.get("labels") or []),
                properties=dict(data.get("properties") or {}),
                is_new=False,
            )
            if dlg.ShowModal() != wx.ID_OK:
                dlg.Destroy()
                return
            try:
                new_props = dlg.get_properties()
                replace = dlg.get_replace()
            except json.JSONDecodeError as e:
                dlg.Destroy()
                show_error(self, "Invalid JSON", e)
                return
            dlg.Destroy()
            self._async(
                lambda: self._client.node_update(eid, new_props, replace=replace),
                lambda _: self._on_refresh_all(None),
                "Could not update node",
            )

        self._async(
            lambda: self._client.node_get(eid),
            open_editor,
            "Could not load node",
        )

    def _on_delete_node(self, _: wx.CommandEvent) -> None:
        idx = self._nodes_lc.GetFirstSelected()
        if idx < 0:
            wx.MessageBox("Select a node first.", "Nodes", wx.OK | wx.ICON_INFORMATION, self)
            return
        eid = self._nodes_lc.GetItemText(idx, 0)
        if (
            wx.MessageBox(
                f"Delete node {eid!r}?",
                "Confirm delete",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
                self,
            )
            != wx.YES
        ):
            return
        detach = self._detach_delete.GetValue()

        def do():
            self._client.node_delete(eid, detach=detach)

        self._async(do, lambda _: self._on_refresh_all(None), "Could not delete node")

    def _on_add_rel(self, _: wx.CommandEvent) -> None:
        dlg = RelCreateDialog(self)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        try:
            props = dlg.get_properties()
        except json.JSONDecodeError as e:
            dlg.Destroy()
            show_error(self, "Invalid JSON", e)
            return
        start, end, typ = dlg.get_start(), dlg.get_end(), dlg.get_type()
        dlg.Destroy()
        if not start or not end or not typ:
            wx.MessageBox("Fill in start, end, and type.", "Validation", wx.OK | wx.ICON_INFORMATION, self)
            return
        self._async(
            lambda: self._client.rel_create(start, end, typ, props),
            lambda _: self._on_refresh_all(None),
            "Could not create relationship",
        )

    def _on_delete_rel(self, _: wx.CommandEvent) -> None:
        idx = self._rels_lc.GetFirstSelected()
        if idx < 0:
            wx.MessageBox("Select a relationship first.", "Relationships", wx.OK | wx.ICON_INFORMATION, self)
            return
        rid = self._rels_lc.GetItemText(idx, 0)
        if (
            wx.MessageBox(
                f"Delete relationship {rid!r}?",
                "Confirm delete",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
                self,
            )
            != wx.YES
        ):
            return

        def do():
            self._client.rel_delete(rid)

        self._async(do, lambda _: self._on_refresh_all(None), "Could not delete relationship")

    # --- async helpers ---

    def _async(
        self,
        fn: Callable[[], Any],
        on_ok: Callable[[Any], None],
        err_title: str,
    ) -> None:
        def worker() -> None:
            try:
                result = fn()
            except Exception as e:
                wx.CallAfter(show_error, self, err_title, e)
            else:
                wx.CallAfter(on_ok, result)

        threading.Thread(target=worker, daemon=True).start()

    def _bootstrap(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        health = self._client.health()
        try:
            dbs = self._client.list_databases()
        except ApiError:
            dbs = []
        return dbs, health

    def _after_bootstrap(self, pack: tuple[list[dict[str, Any]], dict[str, Any]]) -> None:
        dbs, health = pack
        self._apply_db_names(dbs)
        self._apply_health(health)
        self._on_refresh_all(None)

    def _load_db_names(self) -> list[dict[str, Any]]:
        return self._client.list_databases()

    def _apply_db_names(self, rows: list[dict[str, Any]]) -> None:
        names = sorted({str(r.get("name", "")) for r in rows if r.get("name")})
        self._db_choice.Clear()
        if names:
            self._db_choice.AppendItems(names)
        else:
            self._db_choice.Append(self._client.database)
        cur = self._client.database
        if cur in names:
            self._db_choice.SetStringSelection(cur)
        elif names:
            self._db_choice.SetSelection(0)
            self._client.set_database(self._db_choice.GetStringSelection())
        self.SetStatusText(f"{len(names)} database(s) on server.", 1)

    def _load_lists(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        nodes = self._client.nodes_list(skip=0, limit=500)
        rels = self._client.rels_list(skip=0, limit=500)
        return nodes, rels

    def _apply_lists(self, pack: tuple[list[dict[str, Any]], list[dict[str, Any]]]) -> None:
        nodes, rels = pack
        self._nodes_lc.DeleteAllItems()
        for n in nodes:
            eid = str(n.get("element_id", ""))
            labels = ",".join(n.get("labels") or [])
            props = json.dumps(n.get("properties") or {}, ensure_ascii=False)
            if len(props) > 800:
                props = props[:800] + "…"
            idx = self._nodes_lc.InsertItem(self._nodes_lc.GetItemCount(), eid)
            self._nodes_lc.SetItem(idx, 1, labels)
            self._nodes_lc.SetItem(idx, 2, props)

        self._rels_lc.DeleteAllItems()
        for r in rels:
            rid = str(r.get("element_id", ""))
            idx = self._rels_lc.InsertItem(self._rels_lc.GetItemCount(), rid)
            self._rels_lc.SetItem(idx, 1, str(r.get("type", "")))
            self._rels_lc.SetItem(idx, 2, str(r.get("start_node_element_id", "")))
            self._rels_lc.SetItem(idx, 3, str(r.get("end_node_element_id", "")))
            pr = json.dumps(r.get("properties") or {}, ensure_ascii=False)
            if len(pr) > 400:
                pr = pr[:400] + "…"
            self._rels_lc.SetItem(idx, 4, pr)

        self.SetStatusText(
            f"Loaded {len(nodes)} node(s), {len(rels)} relationship(s).",
            0,
        )

    def _apply_health(self, data: dict[str, Any]) -> None:
        self._health_text.SetValue(json.dumps(data, indent=2))
