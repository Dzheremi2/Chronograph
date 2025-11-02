from gi.repository import GObject


class ReqType(GObject.GEnum):
  GET = 0
  GET_CACHED = 1
  GET_ID = 2
  SEARCH = 3
  PUBLISH = 4
  REQUEST_CHALLENGE = 5


class ReqResultCode(GObject.GEnum):
  ERROR = -1
  OK = 200
  PUBLISH_SUCCESS = 201
  FAILURE = 400
  NOT_FOUND = 404
