import json
from typing import Callable, Optional

from gi.repository import Adw, Gtk

from chronograph.backend.db.models import SchemaInfo
from chronograph.internal import Constants


class TagRegistrationDialog(Adw.AlertDialog):
  __gtype_name__ = "TagRegistrationDialog"

  def __init__(self, on_registered: Optional[Callable[[str], None]] = None) -> None:
    super().__init__(
      heading=_("Add New Tag"),
      default_response="cancel",
      close_response="cancel",
    )
    self._on_registered = on_registered
    self._entry = Gtk.Entry(placeholder_text=_("Tag name…"))
    self.set_extra_child(self._entry)
    self.add_response("cancel", _("Cancel"))
    self.add_response("add", _("Add"))
    self.set_response_appearance("add", Adw.ResponseAppearance.SUGGESTED)
    self._entry.connect("activate", lambda *__: self.emit("response", "add"))
    self.connect("response", self._on_response)

  def present(self, parent: Gtk.Widget) -> None:
    """Present the dialog and focus the entry.

    Parameters
    ----------
    parent : Gtk.Widget
      Parent widget for modal presentation.
    """
    super().present(parent)
    self._entry.grab_focus()

  def _on_response(self, _alert: Adw.AlertDialog, response: str) -> None:
    if response != "add":
      return
    tag = self._entry.get_text().strip()
    if not tag:
      return
    registered_tags = self._get_registered_tags()
    if tag in registered_tags:
      return
    registered_tags.append(tag)
    self._set_registered_tags(registered_tags)
    if self._on_registered is not None:
      self._on_registered(tag)
    if self.is_visible():
      self.close()

  @staticmethod
  def _get_registered_tags() -> list[str]:
    try:
      raw = SchemaInfo.get_by_id("tags").value
    except SchemaInfo.DoesNotExist:
      return []
    try:
      tags = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
      return []
    return tags if isinstance(tags, list) else []

  @staticmethod
  def _set_registered_tags(tags: list[str]) -> None:
    SchemaInfo.insert(
      key="tags", value=json.dumps(tags)
    ).on_conflict_replace().execute()
    Constants.WIN.build_sidebar()
