"""Neo4j database listing and creation."""

from __future__ import annotations

import wx

from gui import a11y
from gui.api_client import ApiClient, ApiError
from gui.errors import show_error


class CreateDatabaseDialog(wx.Dialog):
    """Define name and options for a new Neo4j database."""

    def __init__(self, parent: wx.Window) -> None:
        super().__init__(
            parent,
            title="Create new database",
            style=wx.DEFAULT_DIALOG_STYLE,
        )
        self._name = wx.TextCtrl(self, value="")
        self._wait = wx.CheckBox(self, label="Wait until the database is ready")
        self._wait.SetValue(True)

        sz = wx.BoxSizer(wx.VERTICAL)
        a11y.stack_labeled_control(
            self,
            sz,
            caption="New database name (edit field below)",
            body=(
                "Letters, digits, underscore, or hyphen; must start with a letter. "
                "Creating extra databases may require a suitable Neo4j edition."
            ),
            control=self._name,
        )
        wait_cap = wx.StaticText(
            self,
            label="Wait for database to finish starting (check box below)",
        )
        wait_cap.SetName("Wait for database to finish starting (heading)")
        wait_cap.SetHelpText(
            "When checked, the server waits for Neo4j to finish creating the database before returning."
        )
        sz.Add(wait_cap, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        sz.Add(self._wait, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        a11y.announce(
            self._wait,
            "Wait for database to finish starting. When checked, the server waits for Neo4j.",
            "Maps to the wait flag on the create-database API call.",
        )
        sz.Add(self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sz)
        self._name.SetFocus()

    def get_name(self) -> str:
        return self._name.GetValue().strip()

    def get_wait(self) -> bool:
        return self._wait.GetValue()


class DatabaseManagerDialog(wx.Dialog):
    """View server databases, create new ones, pick the active database."""

    def __init__(self, parent: wx.Window, client: ApiClient) -> None:
        super().__init__(
            parent,
            title="Databases on server",
            size=(640, 420),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._client = client
        self._selected_name: str | None = None

        self._list = wx.ListCtrl(
            self,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN,
        )
        a11y.announce(
            self._list,
            "Databases returned by the server (table below). Columns: name, status, default, type, address.",
            "Select one row, then use Use selected as active database.",
        )
        for i, (title, w) in enumerate(
            [
                ("Name", 160),
                ("Current status", 140),
                ("Default", 80),
                ("Type", 100),
                ("Address", 180),
            ]
        ):
            self._list.InsertColumn(i, title, width=w)

        btn_refresh = wx.Button(self, label="&Refresh list")
        a11y.announce(btn_refresh, "Refresh database list", "Reload databases from the server.")
        btn_create = wx.Button(self, label="&Create new database…")
        a11y.announce(btn_create, "Create new database", "Opens a dialog to define a new database.")
        btn_use = wx.Button(self, label="&Use selected as active database")
        a11y.announce(
            btn_use,
            "Use selected as active database",
            "Sets the active database for browsing nodes and relationships.",
        )
        btn_close = wx.Button(self, wx.ID_CLOSE, label="&Close")

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        for b in (btn_refresh, btn_create, btn_use, btn_close):
            btn_row.Add(b, 0, wx.ALL, 4)

        root = wx.BoxSizer(wx.VERTICAL)
        list_intro = wx.StaticText(
            self,
            label="Databases returned by the server (read-only table below)",
        )
        list_intro.SetName("Databases table introduction")
        list_intro.SetHelpText(
            "Each row is one database. Select a row before using Use selected as active database."
        )
        root.Add(list_intro, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 8)
        root.Add(btn_row, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 4)
        self.SetSizer(root)

        self.Bind(wx.EVT_BUTTON, self._on_refresh, btn_refresh)
        self.Bind(wx.EVT_BUTTON, self._on_create, btn_create)
        self.Bind(wx.EVT_BUTTON, self._on_use, btn_use)
        self.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_CLOSE), btn_close)

        self._on_refresh(None)

    def _on_refresh(self, _: wx.CommandEvent | None) -> None:
        try:
            rows = self._client.list_databases()
        except ApiError as e:
            show_error(self, "Could not list databases", e)
            return
        self._list.DeleteAllItems()
        for r in rows:
            name = str(r.get("name", ""))
            status = str(r.get("currentStatus", r.get("state", "")))
            default = str(r.get("default", r.get("isDefault", "")))
            typ = str(r.get("type", ""))
            addr = str(r.get("address", ""))
            idx = self._list.InsertItem(self._list.GetItemCount(), name)
            self._list.SetItem(idx, 1, status)
            self._list.SetItem(idx, 2, default)
            self._list.SetItem(idx, 3, typ)
            self._list.SetItem(idx, 4, addr)

    def _on_create(self, _: wx.CommandEvent) -> None:
        dlg = CreateDatabaseDialog(self)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        name = dlg.get_name()
        wait = dlg.get_wait()
        dlg.Destroy()
        if not name:
            wx.MessageBox("Enter a database name.", "Validation", wx.OK | wx.ICON_INFORMATION, self)
            return
        try:
            self._client.create_database(name, wait=wait)
        except ApiError as e:
            show_error(self, "Could not create database", e)
            return
        wx.MessageBox(
            f"Database {name!r} was created or already existed.",
            "Success",
            wx.OK | wx.ICON_INFORMATION,
            self,
        )
        self._on_refresh(None)

    def _on_use(self, _: wx.CommandEvent) -> None:
        idx = self._list.GetFirstSelected()
        if idx == -1:
            wx.MessageBox("Select a database in the list first.", "Nothing selected", wx.OK | wx.ICON_INFORMATION)
            return
        self._selected_name = self._list.GetItemText(idx, 0)
        self.EndModal(wx.ID_OK)

    def get_selected_database(self) -> str | None:
        return self._selected_name
