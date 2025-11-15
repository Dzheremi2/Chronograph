from gi.repository import GObject, Gtk


class ChrMenuButton(Gtk.ToggleButton):
  __gtype_name__ = "ChrMenuButton"

  def __init__(self) -> None:
    super().__init__()
    self._popover = None

  @GObject.Property(type=Gtk.Popover)
  def popover(self) -> Gtk.Popover:
    return self._popover

  @popover.setter
  def popover(self, popover: Gtk.Popover) -> None:
    if self._popover:
      self._popover.unparent()
    self._popover = popover
    self.bind_property(
      "active", self.popover, "visible", GObject.BindingFlags.BIDIRECTIONAL
    )
    self._popover.set_parent(self)

  @GObject.Property(type=Gtk.Widget)
  def child(self) -> Gtk.Widget:
    return self.get_child()

  @child.setter
  def child(self, child: Gtk.Widget) -> None:
    return self.set_child(child)
