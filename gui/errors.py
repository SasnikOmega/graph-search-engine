"""User-visible error reporting for API and client failures."""

from __future__ import annotations

import sys
import traceback

import wx


def show_error(parent: wx.Window | None, title: str, err: BaseException) -> None:
    """Show a modal error dialog with a short message and optional traceback."""
    msg = (str(err) or "").strip() or err.__class__.__name__
    tb = "".join(traceback.format_exception(type(err), err, err.__traceback__))
    if len(tb) > 3500:
        tb = tb[:3500] + "\n… (traceback truncated)"
    dlg = wx.MessageDialog(
        parent,
        f"{msg}\n\nSee extended information for technical details.",
        title,
        wx.OK | wx.ICON_ERROR,
    )
    dlg.SetExtendedMessage(tb)
    dlg.ShowModal()
    dlg.Destroy()


def install_global_excepthook() -> None:
    """Route uncaught exceptions to a wx dialog when the main loop is running."""

    def hook(exc_type: type, exc: BaseException, tb) -> None:
        if exc_type is KeyboardInterrupt:
            sys.__excepthook__(exc_type, exc, tb)
            return
        text = str(exc) if exc else exc_type.__name__
        stack = "".join(traceback.format_exception(exc_type, exc, tb))
        if wx.GetApp() and wx.GetApp().IsMainLoopRunning():
            wx.CallAfter(_show_uncaught, text, stack)
        else:
            sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = hook


def _show_uncaught(text: str, stack: str) -> None:
    dlg = wx.MessageDialog(
        None,
        f"{text}\n\nSee extended information for the traceback.",
        "Unexpected error",
        wx.OK | wx.ICON_ERROR,
    )
    dlg.SetExtendedMessage(stack[-4000:])
    dlg.ShowModal()
    dlg.Destroy()
