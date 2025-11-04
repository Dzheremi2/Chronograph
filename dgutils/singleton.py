from typing import TypeVar, cast

import gi

T = TypeVar("T", bound=object)


class GSingleton(gi.types.GObjectMeta):
  """A metaclass used to create singleton objects for GObjects, saving support for
  staticmethods and classmethods
  """  # noqa: D205

  _instances = {}

  def __call__(cls: type[T], *args, **kwargs) -> T:  # noqa: D102, N805
    if cls not in GSingleton._instances:
      instance = super().__call__(*args, **kwargs)
      GSingleton._instances[cls] = instance
    return cast("T", GSingleton._instances[cls])


class Singleton(type):
  """A metaclass used to create singleton objects, saving support for staticmethods
  and classmethods
  """  # noqa: D205

  _instances = {}

  def __call__(cls: type[T], *args, **kwargs) -> T:  # noqa: D102
    if cls not in Singleton._instances:
      instance = super().__call__(*args, **kwargs)
      Singleton._instances[cls] = instance
    return Singleton._instances[cls]
