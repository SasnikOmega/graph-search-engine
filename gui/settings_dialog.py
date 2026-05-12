"""Connection settings (base URL, timeout)."""

from __future__ import annotations

import wx

from gui import a11y


class SettingsDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, *, base_url: str, timeout: float) -> None:
        super().__init__(parent, title="Connection settings", style=wx.DEFAULT_DIALOG_STYLE)
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
            caption="API base URL (edit field below)",
            body=(
                "Enter the full root URL of the graph engine REST API, "
                "including protocol and port, for example http://127.0.0.1:8000"
            ),
            control=self._url,
            control_proportion=0,
        )
        a11y.stack_labeled_control(
            self,
            sz,
            caption="Request timeout in seconds (spin box below)",
            body=(
                "Maximum time to wait for each HTTP request before the client reports a timeout. "
                "Increase this value on slow networks."
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
