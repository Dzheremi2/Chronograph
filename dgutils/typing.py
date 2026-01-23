from typing import Any, Callable, Optional


def unwrap[T](obj: Optional[T]) -> T:
  """Unwraps the given object and returns it if it's not None, else raises TypeError.

  Use this function for results that are Optional[T]

  Parameters
  ----------
  obj : Optional[T]
    An object which should be unwrapped

  Returns
  -------
  T
    Given object if not None

  Raises
  ------
  TypeError
    Raised if given object is None
  """
  if obj is None:
    raise TypeError("Unwrap used on an object that is None")
  return obj


def unwrap_or[T](obj: Optional[T], default: T) -> T:
  """Unwraps the given object and returns it if it's not None, else returns the default or calls the default if it's a callable.

  Parameters
  ----------
  obj : Optional[T]
    An object which should be unwrapped
  default : T
    A default value

  Returns
  -------
  T
    Given object if not None, else the default value
  """
  if obj is None:
    return default
  return obj


def unwrap_or_call[T](
  obj: Optional[T], default: Callable[[Any], T], *args, **kwargs
) -> T:
  """Unwraps the given object and returns it if it's not None, else calls the default callable to get the value.

  Parameters
  ----------
  obj : Optional[T]
    An object which should be unwrapped
  default : Callable[[], T]
    A callable that returns a default value

  Returns
  -------
  T
    Given object if not None, else the result of calling the default callable
  """
  if obj is None:
    return default(*args, **kwargs)
  return obj


def unwrap_or_execute[T](
  obj: Optional[T], call: Callable[[Any], Any], *args, **kwargs
) -> Optional[T]:
  """Unwraps the given object and returns it if it's not None, else calls the provided callable with provided args and kwargs

  Returns
  -------
  T
    Given object if not None
  """
  if obj is None:
    call(*args, **kwargs)
  return obj
