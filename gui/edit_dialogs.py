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
        title = "Добавить вершину" if is_new else f"Изменить вершину {element_id}"
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
        self._replace = wx.CheckBox(
            self, label="Полностью заменить свойства (не объединять с существующими)"
        )
        a11y.announce(
            self._replace,
            "Полная замена свойств",
            "Если отмечено, при сохранении старые свойства вершины будут заменены.",
        )
        if is_new:
            self._replace.Hide()
        else:
            self._labels.Enable(False)
            self._labels.SetHelpText(
                "Метки здесь только для просмотра; при редактировании меняются свойства."
            )

        sz = wx.BoxSizer(wx.VERTICAL)
        a11y.stack_labeled_control(
            self,
            sz,
            caption="Метки вершины (однострочное поле ниже)",
            body=(
                "Через запятую, например Person, Student. "
                "Имя метки начинается с буквы; допустимы буквы, цифры и подчёркивание."
            ),
            control=self._labels,
            control_proportion=0,
        )
        a11y.stack_labeled_control(
            self,
            sz,
            caption="Свойства вершины в формате JSON (многострочное поле ниже)",
            body="Один объект JSON: пары «ключ — значение» в соответствии с правилами Neo4j.",
            control=self._props,
            control_proportion=1,
        )
        sz.Add(self._replace, 0, wx.ALL, 6)
        sz.Add(self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sz)
        if not is_new:
            self._labels.SetName(self._labels.GetName() + " Поле только для чтения.")

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
        super().__init__(parent, title="Создать связь", style=wx.DEFAULT_DIALOG_STYLE)
        self._start = wx.TextCtrl(self, value="")
        self._end = wx.TextCtrl(self, value="")
        self._rtype = wx.TextCtrl(self, value="RELATED_TO")
        self._props = wx.TextCtrl(self, value="{}", style=wx.TE_MULTILINE, size=(380, 120))

        sz = wx.BoxSizer(wx.VERTICAL)
        a11y.stack_labeled_control(
            self,
            sz,
            caption="Идентификатор начальной вершины (поле ниже)",
            body="elementId вершины, из которой исходит связь.",
            control=self._start,
        )
        a11y.stack_labeled_control(
            self,
            sz,
            caption="Идентификатор конечной вершины (поле ниже)",
            body="elementId вершины, в которую входит связь.",
            control=self._end,
        )
        a11y.stack_labeled_control(
            self,
            sz,
            caption="Тип связи (поле ниже)",
            body="Одно имя типа, например KNOWS или DEPENDS_ON.",
            control=self._rtype,
        )
        a11y.stack_labeled_control(
            self,
            sz,
            caption="Свойства связи в JSON (многострочное поле ниже)",
            body="Обычно пустой объект {}. Иначе — один объект JSON.",
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
