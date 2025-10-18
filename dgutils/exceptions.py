class SingletonInstantiation(Exception):
  """Raised when a second instance of a singleton class is created."""



class FinalClassInherited(Exception):
  """Raised on subclassing a `@final` decorated class"""



class BaseClassInstantiation(Exception):
  """Raised on instantiation of a `@baseclass` decorated class"""
