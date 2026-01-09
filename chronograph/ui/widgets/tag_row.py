import json

from gi.repository import Adw, Gio, GObject, Gtk

from chronograph.backend.db.models import SchemaInfo, Track
from chronograph.internal import Constants

gtc = Gtk.Template.Child


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/widgets/TagRow.ui")
class TagRow(Gtk.Box):
  __gtype_name__ = "TagRow"

  title: Gtk.Label = gtc()

  def __init__(self, tag: str) -> None:
    self._tag = ""
    super().__init__()
    self._tag = tag
    self.title.set_label(tag)
    self._setup_menu_popover()

  @GObject.Property(type=str, default="")
  def tag(self) -> str:
    return self._tag

  def _setup_menu_popover(self) -> None:
    action_group = Gio.SimpleActionGroup()
    rename_action = Gio.SimpleAction.new("rename", None)
    rename_action.connect("activate", self._on_rename_action)
    action_group.add_action(rename_action)
    delete_action = Gio.SimpleAction.new("delete", None)
    delete_action.connect("activate", self._on_delete_action)
    action_group.add_action(delete_action)
    self.insert_action_group("tag", action_group)

    self.rmb_gesture = Gtk.GestureClick(button=3)
    self.long_press_gesture = Gtk.GestureLongPress()
    self.add_controller(self.rmb_gesture)
    self.add_controller(self.long_press_gesture)

    menu = Gio.Menu()
    menu.append(_("Rename"), "tag.rename")
    menu.append(_("Delete"), "tag.delete")

    self._menu_popover = Gtk.PopoverMenu.new_from_model(menu)
    self._menu_popover.set_parent(self)
    self.rmb_gesture.connect("released", lambda *__: self._menu_popover.popup())

  def _on_rename_action(self, *_args) -> None:
    if self._menu_popover is not None:
      self._menu_popover.popdown()
    entry = Gtk.Entry(text=self._tag)
    alert = Adw.AlertDialog(
      heading=_("Rename Tag"),
      default_response="cancel",
      close_response="cancel",
    )
    alert.add_response("cancel", _("Cancel"))
    alert.add_response("rename", _("Rename"))
    alert.set_response_appearance("rename", Adw.ResponseAppearance.SUGGESTED)
    alert.set_extra_child(entry)
    entry.connect("activate", lambda *__: alert.emit("response", "rename"))

    def on_response(alert: Adw.AlertDialog, response: str) -> None:
      if response != "rename":
        return
      new_tag = entry.get_text().strip()
      if not new_tag or new_tag == self._tag:
        return
      if self._rename_tag(new_tag) and alert.is_visible():
        alert.close()

    alert.connect("response", on_response)
    alert.present(Constants.WIN)
    entry.grab_focus()

  def _on_delete_action(self, *_args) -> None:
    if self._menu_popover is not None:
      self._menu_popover.popdown()
    alert = Adw.AlertDialog(
      heading=_("Delete Tag?"),
      default_response="cancel",
      close_response="cancel",
    )
    alert.add_response("cancel", _("Cancel"))
    alert.add_response("delete", _("Delete"))
    alert.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

    def on_response(alert: Adw.AlertDialog, response: str) -> None:
      if response != "delete":
        return
      if self._delete_tag() and alert.is_visible():
        alert.close()

    alert.connect("response", on_response)
    alert.present(Constants.WIN)

  def _rename_tag(self, new_tag: str) -> bool:
    old_tag = self._tag.strip()
    new_tag = new_tag.strip()
    if not old_tag or not new_tag or old_tag == new_tag:
      return False

    registered_tags = self._get_registered_tags()
    if old_tag not in registered_tags:
      return False

    already_registered = new_tag in registered_tags
    if already_registered:
      registered_tags = [tag for tag in registered_tags if tag != old_tag]
    else:
      registered_tags = [new_tag if tag == old_tag else tag for tag in registered_tags]
    self._set_registered_tags(registered_tags)

    for track in Track.select(Track.track_uuid, Track.tags_json):
      if not track.tags_json or old_tag not in track.tags_json:
        continue
      updated = [new_tag if val == old_tag else val for val in track.tags_json]
      track.tags_json = self._dedupe(updated)
      track.save()

    cards_model = Constants.WIN.library.cards_model
    for index in range(cards_model.get_n_items()):
      card = cards_model.get_item(index)
      if card is None:
        continue
      if old_tag not in card.tags:
        continue
      updated = [new_tag if val == old_tag else val for val in card.tags]
      card.tags = self._dedupe(updated)

    if Constants.WIN.active_tag_filter == old_tag:
      Constants.WIN.active_tag_filter = new_tag
    Constants.WIN.library.filter.changed(Gtk.FilterChange.DIFFERENT)
    self._tag = new_tag
    return True

  def _delete_tag(self) -> bool:
    tag = self._tag.strip()
    if not tag:
      return False
    registered_tags = self._get_registered_tags()
    if tag not in registered_tags:
      return False
    registered_tags.remove(tag)
    self._set_registered_tags(registered_tags)

    for track in Track.select(Track.track_uuid, Track.tags_json):
      if not track.tags_json or tag not in track.tags_json:
        continue
      updated = [val for val in track.tags_json if val != tag]
      track.tags_json = updated
      track.save()

    cards_model = Constants.WIN.library.cards_model
    for index in range(cards_model.get_n_items()):
      card = cards_model.get_item(index)
      if card is None:
        continue
      if tag not in card.tags:
        continue
      updated = [val for val in card.tags if val != tag]
      card.tags = updated

    if Constants.WIN.active_tag_filter == tag:
      Constants.WIN.active_tag_filter = None
    Constants.WIN.library.filter.changed(Gtk.FilterChange.DIFFERENT)
    return True

  @staticmethod
  def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for val in values:
      if val not in deduped:
        deduped.append(val)
    return deduped

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
