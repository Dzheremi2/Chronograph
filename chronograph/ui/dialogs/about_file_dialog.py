import json

from gi.repository import Adw, GObject, Gtk

from chronograph.backend.db.models import SchemaInfo, Track, TrackLyric
from chronograph.backend.file.library_manager import LibraryManager
from chronograph.backend.file.song_card_model import SongCardModel
from chronograph.internal import Constants
from chronograph.ui.dialogs.tag_registration_dialog import TagRegistrationDialog
from chronograph.ui.widgets.lyric_row import LyricRow
from dgutils import Linker

gtc = Gtk.Template.Child


@Gtk.Template(resource_path=Constants.PREFIX + "/gtk/ui/dialogs/AboutFileDialog.ui")
class AboutFileDialog(Adw.Dialog, Linker):
  __gtype_name__ = "AboutFileDialog"

  nav_view: Adw.NavigationView = gtc()
  main_nav_page: Adw.NavigationPage = gtc()
  lyr_nav_page: Adw.NavigationPage = gtc()

  cover_image: Gtk.Image = gtc()
  title_info_row: Adw.ActionRow = gtc()
  artist_info_row: Adw.ActionRow = gtc()
  album_info_row: Adw.ActionRow = gtc()
  tags_wrap_box: Adw.WrapBox = gtc()
  import_info_row: Adw.ActionRow = gtc()
  modified_info_row: Adw.ActionRow = gtc()
  available_lyrics_button: Adw.ActionRow = gtc()

  available_lyrics_group: Adw.PreferencesGroup = gtc()

  def __init__(self, model: SongCardModel) -> None:
    super().__init__()
    Linker.__init__(self)
    self._model = model
    self._tags_add_button = Gtk.Button(
      icon_name="add-line-symbolic",
      valign=Gtk.Align.CENTER,
      css_classes=["pill", "small"],
      tooltip_text=_("Assign tag"),
    )
    self._tags_add_button.connect("clicked", self._on_tags_add_button_clicked)
    self.available_lyrics_button.connect(
      "activated", self._on_available_lyrics_button_clicked
    )

    self.new_binding(
      self._model.bind_property(
        "cover", self.cover_image, "paintable", GObject.BindingFlags.SYNC_CREATE
      )
    )
    self.new_binding(
      self._model.bind_property(
        "title_display",
        self.title_info_row,
        "subtitle",
        GObject.BindingFlags.SYNC_CREATE,
      )
    )
    self.new_binding(
      self._model.bind_property(
        "artist_display",
        self.artist_info_row,
        "subtitle",
        GObject.BindingFlags.SYNC_CREATE,
      )
    )
    self.new_binding(
      self._model.bind_property(
        "album_display",
        self.album_info_row,
        "subtitle",
        GObject.BindingFlags.SYNC_CREATE,
      )
    )
    self.new_binding(
      self._model.bind_property(
        "imported_at",
        self.import_info_row,
        "subtitle",
        GObject.BindingFlags.SYNC_CREATE,
      )
    )
    self.new_binding(
      self._model.bind_property(
        "last_modified",
        self.modified_info_row,
        "subtitle",
        GObject.BindingFlags.SYNC_CREATE,
      )
    )
    self._populate_tags()
    self._populate_available_lyrics()

  def close(self) -> bool:
    self.unbind_all()
    self._model = None
    super().close()

  def _on_available_lyrics_button_clicked(self, *_args) -> None:
    self.nav_view.push(self.lyr_nav_page)

  def _populate_available_lyrics(self) -> None:
    is_any = False
    for track_lyric in TrackLyric.select(TrackLyric.lyric).where(
      TrackLyric.track == self._model.uuid
    ):
      is_any = True
      self.available_lyrics_group.add(LyricRow(track_lyric.lyric))
    if not is_any:
      self.available_lyrics_button.set_sensitive(False)
      self.available_lyrics_button.set_title(_("No Lyrics Available"))

  def _populate_tags(self) -> None:
    track_tags = self._get_track_tags()
    registered_tags = set(self._get_registered_tags())
    self._clear_wrap_box(self.tags_wrap_box)
    for tag in track_tags:
      if registered_tags and tag not in registered_tags:
        continue
      self.tags_wrap_box.append(self._build_tag_button(tag))
    self.tags_wrap_box.append(self._tags_add_button)

  def _on_tags_add_button_clicked(self, *_args) -> None:
    dialog = Adw.Dialog(content_height=400, content_width=500)
    dialog.set_title(_("Select Tag"))

    track_tags = set(self._get_track_tags())
    available_tags = [
      tag for tag in self._get_registered_tags() if tag not in track_tags
    ]

    box = Gtk.Box(
      orientation=Gtk.Orientation.VERTICAL,
      spacing=12,
      margin_top=16,
      margin_bottom=16,
      margin_start=16,
      margin_end=16,
    )
    self._tag_dialog_box = box
    self._tag_dialog_group = Adw.PreferencesGroup()
    self._tag_dialog_scrolled = Gtk.ScrolledWindow(
      vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER
    )
    self._tag_dialog_scrolled.set_child(self._tag_dialog_group)
    self._tag_dialog_status_page = Adw.StatusPage(
      title=_("No Tags Available"),
      description=_("There's no tags registered yet or all tags were assigned"),
      vexpand=True,
    )

    for tag in available_tags:
      self._tag_dialog_group.add(self._build_tag_row(tag, dialog))

    if available_tags:
      self._show_tag_group()
    else:
      self._show_tag_status_page()

    add_button_box = Gtk.Box(halign=Gtk.Align.CENTER)
    add_button = Gtk.Button(
      label=_("Add New Tag"), css_classes=["pill", "suggested-action"]
    )
    add_button.connect("clicked", self._on_register_tag_clicked, dialog)
    add_button_box.append(add_button)
    box.append(add_button_box)

    clamp = Adw.Clamp(maximum_size=480, tightening_threshold=480)
    clamp.set_child(box)

    view = Adw.ToolbarView()
    view.add_top_bar(Adw.HeaderBar())
    view.set_content(clamp)

    dialog.set_child(view)
    dialog.connect("closed", self._clear_tag_dialog_refs)
    dialog.present(self)

  def _on_register_tag_clicked(self, _btn, parent: Adw.Dialog) -> None:
    def on_registered(tag: str) -> None:
      if tag in set(self._get_track_tags()):
        return
      self._show_tag_group()
      if self._tag_dialog_group is not None:
        self._tag_dialog_group.add(self._build_tag_row(tag, parent))

    TagRegistrationDialog(on_registered=on_registered).present(parent)

  def _build_tag_row(self, tag: str, dialog: Adw.Dialog) -> Adw.ActionRow:
    row = Adw.ActionRow(title=tag, activatable=True, selectable=False, use_markup=False)
    row.connect("activated", self._on_tag_row_activated, tag, dialog)
    delete_button = Gtk.Button(
      icon_name="clean-files-symbolic",
      css_classes=["destructive-action"],
      valign=Gtk.Align.CENTER,
    )
    delete_button.connect("clicked", self._delete_tag, tag, row)
    row.add_suffix(delete_button)
    return row

  def _on_tag_row_activated(self, _row, tag: str, dialog: Adw.Dialog) -> None:
    self._assign_tag(tag)
    dialog.close()

  def _delete_tag(
    self,
    _btn,
    tag: str,
    row: Adw.ActionRow,
  ) -> None:
    tag = tag.strip()
    if not tag:
      return
    registered_tags = self._get_registered_tags()
    if tag not in registered_tags:
      return
    registered_tags.remove(tag)
    self._set_registered_tags(registered_tags)
    for track in Track.select(Track.track_uuid, Track.tags_json):
      if not track.tags_json or tag not in track.tags_json:
        continue
      updated = [val for val in track.tags_json if val != tag]
      Track.update(tags_json=updated).where(
        Track.track_uuid == track.track_uuid
      ).execute()
    current_tags = list(self._model.tags or [])
    if tag in current_tags:
      current_tags = [val for val in current_tags if val != tag]
      self._model.tags = current_tags
    if row.get_parent() is not None and self._tag_dialog_group is not None:
      self._tag_dialog_group.remove(row)
    if self._tag_dialog_group is not None and self._tag_dialog_group.get_row(0) is None:
      self._show_tag_status_page()
    self._populate_tags()
    self._refresh_library_filter()

  def _show_tag_group(self) -> None:
    if (
      self._tag_dialog_box is None
      or self._tag_dialog_group is None
      or self._tag_dialog_scrolled is None
    ):
      return
    if (
      self._tag_dialog_status_page is not None
      and self._tag_dialog_status_page.get_parent() is not None
    ):
      self._tag_dialog_box.remove(self._tag_dialog_status_page)
    if self._tag_dialog_scrolled.get_parent() is None:
      self._tag_dialog_box.prepend(self._tag_dialog_scrolled)

  def _show_tag_status_page(self) -> None:
    if (
      self._tag_dialog_box is None
      or self._tag_dialog_status_page is None
      or self._tag_dialog_scrolled is None
    ):
      return
    if (
      self._tag_dialog_scrolled is not None
      and self._tag_dialog_scrolled.get_parent() is not None
    ):
      self._tag_dialog_box.remove(self._tag_dialog_scrolled)
    if self._tag_dialog_status_page.get_parent() is None:
      self._tag_dialog_box.prepend(self._tag_dialog_status_page)

  def _clear_tag_dialog_refs(self, *_args) -> None:
    self._tag_dialog_box = None
    self._tag_dialog_group = None
    self._tag_dialog_status_page = None
    self._tag_dialog_scrolled = None

  def _assign_tag(self, tag: str) -> None:
    tag = tag.strip()
    if not tag:
      return
    track_tags = list(self._model.tags or [])
    if tag in track_tags:
      return
    track_tags.append(tag)
    self._model.tags = track_tags
    self._populate_tags()
    self._refresh_library_filter()

  def _build_tag_button(self, tag: str) -> Gtk.Button:
    button = Gtk.Button(
      label=tag,
      valign=Gtk.Align.CENTER,
      css_classes=["pill", "small"],
    )
    button.set_tooltip_text(_("Click to unassign"))
    button.connect("clicked", self._unassign_tag, tag)
    return button

  def _unassign_tag(self, _btn, tag: str) -> None:
    tag = tag.strip()
    if not tag:
      return
    track_tags = list(self._model.tags or [])
    if tag not in track_tags:
      return
    track_tags.remove(tag)
    self._model.tags = track_tags
    self._populate_tags()
    self._refresh_library_filter()

  def _get_track_tags(self) -> list[str]:
    return list(self._model.tags or [])

  def _refresh_library_filter(self) -> None:
    Constants.WIN.library.filter.changed(Gtk.FilterChange.DIFFERENT)

  def _get_registered_tags(self) -> list[str]:
    try:
      raw = SchemaInfo.get_by_id("tags").value
    except SchemaInfo.DoesNotExist:
      return []
    try:
      tags = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
      return []
    return tags if isinstance(tags, list) else []

  def _set_registered_tags(self, tags: list[str]) -> None:
    SchemaInfo.insert(
      key="tags", value=json.dumps(tags)
    ).on_conflict_replace().execute()
    Constants.WIN.build_sidebar()

  def _clear_wrap_box(self, box: Adw.WrapBox) -> None:
    child = box.get_first_child()
    while child is not None:
      next_child = child.get_next_sibling()
      box.remove(child)
      child = next_child

  @Gtk.Template.Callback()
  def _on_delete_file_button_clicked(self, *_args) -> None:
    track_uuid: str = self._model.uuid
    title: str = self._model.title_display
    artist: str = self._model.artist_display

    LibraryManager.delete_files([track_uuid])

    cards_model = Constants.WIN.library.cards_model
    for index in range(cards_model.get_n_items()):
      card: SongCardModel = cards_model.get_item(index)
      if card is not None and card.uuid == track_uuid:
        cards_model.remove(index)
        break

    Constants.WIN.library.card_filter_model.notify("n-items")
    Constants.WIN.show_toast(
      _('File "{title} — {artist}" was deleted').format(title=title, artist=artist), 2
    )
    self.close()
