import asyncio
import threading
from typing import Coroutine

from gi.repository import GLib, GObject


class AsyncTask(GObject.Object):
  """An async task wrapper for async function with return value.

  Supports passing a `self.set_progress` function to the coroutine to change the progress
  Progress is a float number between 0.0 and 1.0

  Parameters
  ----------
  coroutine : Coroutine
    A target async function
  do_use_progress : bool, default `False`
    If target coroutine support progress, it should be added with this set to True.
    If set, will pass `self.set_propgress` to the coroutine for an `on_progress`
    keyword argument
  do_use_cancellable : bool, default `True`
    If set, will pass `threading.Event` to coroutine for `cancellable` keyword.
    Coroutine can rely on this flag to support cancellation on `self.cancel()` call

  Properties
  ----------
  progress : float\\
    A GObject property with fractional value from 0.0 to 1.0, representing a coroutine
    progress

  Emits
  -----
  task-started -> Emited on coroutine started

  task-done(object) -> Emited on coroutine done executing. Passes the coroutine result

  error(Exception) -> Emited on any exception occured. Passes the excpetion

  cancelled -> Emited on `self.cancel()` call. Tells that coroutine was cancelled
  """  # noqa: D301

  __gsignals__ = {
    "task-started": (GObject.SignalFlags.RUN_FIRST, None, ()),
    "task-done": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    "error": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    "cancelled": (GObject.SignalFlags.RUN_FIRST, None, ()),
  }

  progress: float = GObject.Property(
    type=float, minimum=0.0, maximum=1.0000001, default=0.0
  )

  def __init__(
    self,
    coroutine: Coroutine,
    *args,
    do_use_progress: bool = False,
    do_use_cancellable: bool = False,
    **kwargs,
  ) -> None:
    super().__init__()
    self._coroutine = coroutine
    self._do_use_progress = do_use_progress
    self._do_use_cancellable = do_use_cancellable
    if args:
      self._args = args
    else:
      self._args = []
    if kwargs:
      self._kwargs = kwargs
    else:
      self._kwargs = {}
    self._thread = None
    self._cancel_event = threading.Event()

  def start(self) -> None:
    """Starts the execution of the coroutine in separate thread

    Raises
    ------
    RuntimeError
      Raised if task is already running
    """
    if self._thread and self._thread.is_alive():
      raise RuntimeError("Task is already running")
    self._thread = threading.Thread(target=self._run, daemon=True)
    self._thread.start()

  def _run(self) -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
      GLib.idle_add(self.emit, "task-started")
      if self._do_use_progress:
        self._kwargs["on_progress"] = self.set_progress
      if self._do_use_cancellable:
        self._kwargs["cancellable"] = self._cancel_event
      result = loop.run_until_complete(self._coroutine(*self._args, **self._kwargs))
    except Exception as e:
      GLib.idle_add(self.emit, "error", e)
    else:
      GLib.idle_add(self.emit, "task-done", result)
    finally:
      loop.close()

  def set_progress(self, progress: float) -> None:
    """Passed to the coroutine to support reflecting progress with the coroutine

    Parameters
    ----------
    progress : float
        Progress value from the coroutine
    """
    progress = max(0.0, min(1.0, progress))
    self.props.progress = progress

  def cancel(self) -> None:
    """Cancels the running coroutine if it support cancellable"""
    self._cancel_event.set()
    self.emit("cancelled")
