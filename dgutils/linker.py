import weakref
from typing import Callable

from gi.repository import GObject, Gtk


class Linker:
  """Class interface for GObject bindings and signals managing

  Use it as a subclass of your GObject-based class to support managing.

  Add `Linker.__init__(self)` call to subclass `__init__` method.
  """

  def __init__(self) -> None:
    self._linker_bindings: list[GObject.Binding] = []
    self._linker_connections: weakref.WeakKeyDictionary[GObject.Object, list[int]] = (
      weakref.WeakKeyDictionary()
    )

  def new_binding(self, binding: GObject.Binding) -> None:
    """Assigns provided Binding to `self` for future unbinding.

    Use as::

      self.new_binding(self.bind_property("path", target, "label"))

    This saves the result of property binding to `self` and now it can be unbound by
    calling `self.unbind_all()` or `self.link_teardown()`

    Parameters
    ----------
    binding : GObject.Binding
      The `Binding` instace returned by GTK backend when bound successfully
    """
    self._linker_bindings.append(binding)

  def new_connection(
    self, gobject: GObject.Object, signal: str, callback: Callable, *args
  ) -> None:
    """Connects the provided object's signal to callback with `*args` if passed and saves the returned handler id to `self`

    Use as::

      self.new_connection(button, "clicked", on_button_clicked, new_label) # or lambda

    This will proceed connection and save handler id in mapping with the object for
    further disconnection

    Parameters
    ----------
    gobject : GObject.Object
      Target GObject.Object
    signal : str
      The connected signal name
    callback : Callable
      Callback called on signal emission
    *args
      User data to pass to `GObject.Object.connect()` method
    """

    def on_gobject_destroyed(gobject: GObject.Object) -> None:
      handlers = self._linker_connections.pop(gobject, [])
      for handler_id in handlers:
        if gobject.handler_is_connected(handler_id):
          gobject.disconnect(handler_id)

    if gobject not in self._linker_connections:
      self._linker_connections[gobject] = []
      if isinstance(gobject, Gtk.Widget):
        gobject.connect("destroy", on_gobject_destroyed)

    handler = gobject.connect(signal, callback, *args)
    self._linker_connections[gobject].append(handler)

  def unbind_all(self) -> None:
    """Unbinds all bindings"""
    for binding in self._linker_bindings:
      binding.unbind()
    self._linker_bindings.clear()

  def disconnect_all(self) -> None:
    """Disconnects all connections"""
    for gobject, handlers in list(self._linker_connections.items()):
      for handler_id in handlers:
        if gobject.handler_is_connected(handler_id):
          gobject.disconnect(handler_id)
    self._linker_connections.clear()

  def link_teardown(self) -> None:
    """Both unbinds all bindings and disconnect all connections"""
    self.unbind_all()
    self.disconnect_all()
