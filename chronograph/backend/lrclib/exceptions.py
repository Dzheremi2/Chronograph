class LRClibException(Exception):
  pass


class APIRequestError(LRClibException):
  pass


class TrackNotFound(LRClibException):
  pass


class SearchEmptyReturn(LRClibException):
  pass


class IncorrectPublishToken(LRClibException):
  pass


class LRClibUnknownError(LRClibException):
  pass


class PublishAlreadyRunning(LRClibException):
  pass
