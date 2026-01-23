from __future__ import annotations

from threading import Lock
from typing import Callable, cast

from dgutils.exceptions import (
  BaseClassInstantiation,
  FinalClassInherited,
  SingletonInstantiation,
)


def errsingleton[T: type](cls: T) -> T:
  """Raises a `SingletonInstantiation` exception when trying to instantiate twice."""
  instance = None
  has_instance = False
  lock = Lock()

  def get_instance(*args, **kwargs):
    nonlocal instance, has_instance
    with lock:
      if has_instance:
        raise SingletonInstantiation(f"{cls.__name__} can only be instantiated once.")
      instance = cls(*args, **kwargs)
      has_instance = True
      return instance

  return get_instance()


def singleton[T: type](cls: T) -> T:
  """Returns an already created instance on second instantiation.

  Simple singleton realizations. Disables support for staticmethods and classmethods,
  since calling class only possible with using parenthesis.

  If your class has static or class methods, consider using `Singleton` metaclass, or
  `GSingleton` metaclass for GObject classes.
  """
  instances = {}
  lock = Lock()

  def get_instance(*args, **kwargs):
    with lock:
      if cls not in instances:
        instances[cls] = cls(*args, **kwargs)
      return instances[cls]

  return get_instance()


def final[T: type](cls: T) -> T:
  """Raises a `FinalClassInherited` exception when trying to subclass decorated class"""

  def fail_on_inherit(_subclass, **_kwargs):
    raise FinalClassInherited(f"Cannot subclass final class {cls.__name__}")

  cls.__init_subclass__ = classmethod(fail_on_inherit)  # ty:ignore[invalid-assignment]
  return cls


def baseclass[T: type](cls: T) -> T:
  """Raises a `BaseClassInstantiation` exception when trying to instantiate decorated class"""
  original_init = cls.__init__

  def __init__(self: object, *args, **kwargs):  # noqa: N807
    if self.__class__ is cls:
      raise BaseClassInstantiation(
        f"{cls.__name__} is a base class and cannot be instantiated directly"
      )
    cast("Callable[..., None]", original_init)(self, *args, **kwargs)

  cls.__init__ = __init__  # ty:ignore[invalid-assignment]
  return cls
