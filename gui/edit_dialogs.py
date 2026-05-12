"""Dialogs for editing node labels/properties and creating relationships."""

from __future__ import annotations

import json
from typing import Any

import wx

from gui import a11y


class NodeEditDialog(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        *,
        element_id: str | None,
        labels: list[str],
        properties: dict[str, Any],
        is_new: bool,
    ) -> None:
        title = "Add node" if is_new else f"Edit node {element_id}"
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._is_new = is_new
        self._element_id = element_id

        self._labels = wx.TextCtrl(self, value=", ".join(labels))
        self._props = wx.TextCtrl(
            self,
            value=json.dumps(properties, indent=2, ensure_ascii=False),
            style=wx.TE_MULTILINE,
            size=(420, 220),
        )
        self._replace = wx.CheckBox(self, label="Replace properties entirely (instead of merging)")
        a11y.announce(
            self._replace,
            "Replace all properties",
            "When editing, if checked, PATCH uses replace mode.",
        )
        if is_new:
            self._replace.Hide()
        else:
            self._labels.Enable(False)
            self._labels.SetHelpText(
                "Labels are read-only here; the API updates properties only on existing nodes."
            )

        sz = wx.BoxSizer(wx.VERTICAL)
        a11y.stack_labeled_control(
            self,
            sz,
            caption="Node labels (single-line edit field below)",
            body=(
                "Comma-separated Neo4j labels for this node, for example Person, Student. "
                "Each label must start with a letter and use only letters, digits, and underscores."
            ),
            control=self._labels,
            control_proportion=0,
        )
        a11y.stack_labeled_control(
            self,
            sz,
            caption="Node properties as JSON (multi-line edit field below)",
            body=(
                "One JSON object with string keys and JSON-serializable values. "
                "Property names must follow Neo4j rules."
            ),
            control=self._props,
            control_proportion=1,
        )
        sz.Add(self._replace, 0, wx.ALL, 6)
        sz.Add(self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sz)
        if not is_new:
            self._labels.SetName(self._labels.GetName() + " This field is read-only.")

    def get_labels(self) -> list[str]:
        raw = self._labels.GetValue().replace(";", ",")
        parts = [p.strip() for p in raw.split(",")]
        return [p for p in parts if p]

    def get_properties(self) -> dict[str, Any]:
        text = self._props.GetValue().strip()
        if not text:
            return {}
        return json.loads(text)

    def get_replace(self) -> bool:
        return self._replace.IsShown() and self._replace.GetValue()


class RelCreateDialog(wx.Dialog):
    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent, title="Create relationship", style=wx.DEFAULT_DIALOG_STYLE)
        self._start = wx.TextCtrl(self, value="")
        self._end = wx.TextCtrl(self, value="")
        self._rtype = wx.TextCtrl(self, value="RELATED_TO")
        self._props = wx.TextCtrl(self, value="{}", style=wx.TE_MULTILINE, size=(380, 120))

        sz = wx.BoxSizer(wx.VERTICAL)
        a11y.stack_labeled_control(
            self,
            sz,
            caption="Start node element ID (edit field below)",
            body="Paste the Neo4j element ID of the node where the relationship begins (tail).",
            control=self._start,
        )
        a11y.stack_labeled_control(
            self,
            sz,
            caption="End node element ID (edit field below)",
            body="Paste the Neo4j element ID of the node where the relationship ends (head).",
            control=self._end,
        )
        a11y.stack_labeled_control(
            self,
            sz,
            caption="Relationship type (edit field below)",
            body="One relationship type name, for example KNOWS or DEPENDS_ON.",
            control=self._rtype,
        )
        a11y.stack_labeled_control(
            self,
            sz,
            caption="Relationship properties as JSON (multi-line edit field below)",
            body="Usually an empty object {}. Otherwise one JSON object of relationship properties.",
            control=self._props,
            control_proportion=1,
        )
        sz.Add(self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sz)

    def get_start(self) -> str:
        return self._start.GetValue().strip()

    def get_end(self) -> str:
        return self._end.GetValue().strip()

    def get_type(self) -> str:
        return self._rtype.GetValue().strip()

    def get_properties(self) -> dict[str, Any]:
        return json.loads(self._props.GetValue().strip() or "{}")
