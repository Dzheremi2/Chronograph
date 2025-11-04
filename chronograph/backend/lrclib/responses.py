from dataclasses import dataclass


@dataclass
class LRClibEntry:
  """A single LRClib track data class

  Params
  ------
  id : int
    ID of the track on LRClib
  track_name : str
    Title of the track
  artist_name : str
    Artist of the track
  album_name : str
    Album of the name
  duration : int
    Duration of the track
  plain_lyrics : str
    Plain lyrics of the track, default to ""
  synced_lyrics : str
    Synced lyrics of the track, default to ""
  """

  id: int
  track_name: str
  artist_name: str
  album_name: str
  duration: int
  instrumental: bool
  plain_lyrics: str = ""
  synced_lyrics: str = ""


@dataclass
class LRClibChallenge:
  """Cryptographic challenge data

  Parameters
  ----------
  prefix : str
    Challenge prefix
  target : str
    Challenge target hex
  """

  prefix: str
  target: str
