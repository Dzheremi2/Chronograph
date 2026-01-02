PRAGMA foreign_keys = ON;

-- Library media content
CREATE TABLE IF NOT EXISTS tracks (
  track_uuid   TEXT PRIMARY KEY,        -- Unique ID of the track
  imported_at  INTEGER NOT NULL,        -- Time, when track was imported
  format       TEXT NOT NULL,           -- Format of the media
  tags_json    JSON NOT NULL DEFAULT [] -- List of tags assigned to the track
);

-- Lyrics library, extendable when new formats added
CREATE TABLE IF NOT EXISTS lyrics (
  lyrics_uuid  TEXT PRIMARY KEY,         -- Unique ID of the lyric
  format       TEXT NOT NULL,            -- Lyric format (LRC, eLRC, TTML, SRT, ...)
  content      TEXT NOT NULL DEFAULT '', -- Lyric text
  created_at   INTEGER NOT NULL,         -- Creation time
  updated_at   INTEGER                   -- Last modified time
);

-- many-to-many binding of lyrics and tracks
CREATE TABLE IF NOT EXISTS track_lyrics (
  track_uuid   TEXT NOT NULL,            -- Unique ID of the track
  lyrics_uuid  TEXT NOT NULL,            -- Unique ID of the lyric
  PRIMARY KEY (track_uuid, lyrics_uuid), -- Unique ID of the binding
  -- Automatically detele binding if track or lyric was deleted
  FOREIGN KEY (track_uuid) REFERENCES tracks(track_uuid) ON DELETE CASCADE,
  FOREIGN KEY (lyrics_uuid) REFERENCES lyrics(lyrics_uuid) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_track_lyrics_track  ON track_lyrics(track_uuid);
CREATE INDEX IF NOT EXISTS idx_track_lyrics_lyrics ON track_lyrics(lyrics_uuid);
CREATE INDEX IF NOT EXISTS idx_lyrics_format       ON lyrics(format);

-- DB Metainfo
CREATE TABLE IF NOT EXISTS schema_info (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
