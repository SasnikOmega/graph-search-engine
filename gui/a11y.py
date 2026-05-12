"""Accessibility helpers: visible captions plus names/help on controls for screen readers."""

from __future__ import annotations

import wx


def announce(control: wx.Window, name: str, description: str = "") -> None:
    control.SetName(name)
    if description:
        control.SetHelpText(description)


def stack_labeled_control(
    parent: wx.Window,
    sizer: wx.Sizer,
    *,
    caption: str,
    body: str = "",
    control: wx.Window,
    control_proportion: int = 0,
) -> tuple[wx.StaticText, wx.StaticText | None]:
    """
    Place a caption (and optional explanatory text) *above* the control so reading
    order is obvious, and mirror the same text on the control's accessible name so
    focus announcements stay meaningful when the static line is not read with the field.
    """
    cap_plain = caption.replace("&", "").strip()
    lab = wx.StaticText(parent, label=caption)
    lab.SetName(f"{cap_plain} (heading)")
    lab.SetHelpText(body or cap_plain)
    sizer.Add(lab, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

    body_lab: wx.StaticText | None = None
    if body.strip():
        body_lab = wx.StaticText(parent, label=body)
        body_lab.SetName(body.strip())
        body_lab.Wrap(520)
        sizer.Add(body_lab, 0, wx.LEFT | wx.RIGHT, 6)

    spoken = f"{cap_plain}. {body}".strip() if body.strip() else cap_plain
    control.SetName(spoken)
    control.SetHelpText(body.strip() if body.strip() else cap_plain)
    sizer.Add(control, control_proportion, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    return lab, body_lab


def labeled_field(
    parent: wx.Window,
    sizer: wx.Sizer,
    label: str,
    widget: wx.Window,
    *,
    label_desc: str = "",
    field_desc: str = "",
) -> wx.StaticText:
    """Horizontal label + field (legacy); prefer stack_labeled_control for text entry."""
    lab = wx.StaticText(parent, label=label)
    clean = label.replace("&", "").strip()
    lab.SetName(clean + " label")
    if label_desc:
        lab.SetHelpText(label_desc)
    announce(widget, clean, field_desc or label_desc)
    sizer.Add(lab, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    sizer.Add(widget, 1, wx.EXPAND | wx.ALL, 4)
    return lab
