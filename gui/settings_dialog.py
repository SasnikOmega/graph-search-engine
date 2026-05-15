"""Connection settings (base URL, timeout)."""

from __future__ import annotations

import wx

from gui import a11y


class SettingsDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, *, base_url: str, timeout: float) -> None:
        super().__init__(parent, title="Параметры подключения", style=wx.DEFAULT_DIALOG_STYLE)
        self._url = wx.TextCtrl(self, value=base_url)
        self._timeout = wx.SpinCtrlDouble(
            self,
            min=5.0,
            max=600.0,
            inc=5.0,
            initial=float(timeout),
        )

        sz = wx.BoxSizer(wx.VERTICAL)
        a11y.stack_labeled_control(
            self,
            sz,
            caption="Базовый URL API (поле ввода ниже)",
            body=(
                "Полный адрес REST API, включая протокол и порт, "
                "например http://127.0.0.1:8000"
            ),
            control=self._url,
            control_proportion=0,
        )
        a11y.stack_labeled_control(
            self,
            sz,
            caption="Таймаут запроса в секундах (поле ниже)",
            body=(
                "Сколько секунд ждать ответ сервера. На медленной сети значение можно увеличить."
            ),
            control=self._timeout,
            control_proportion=0,
        )

        btns = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
        sz.Add(btns, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sz)
        self._url.SetFocus()

    def get_values(self) -> tuple[str, float]:
        return self._url.GetValue().strip(), float(self._timeout.GetValue())
