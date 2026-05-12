"""wxPython application entry."""

from __future__ import annotations

import wx

from gui.errors import install_global_excepthook
from gui.main_frame import MainFrame


def main() -> None:
    app = wx.App(False)
    install_global_excepthook()
    frame = MainFrame()
    frame.Show()
    app.MainLoop()
