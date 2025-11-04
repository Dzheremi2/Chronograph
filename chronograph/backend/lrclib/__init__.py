"""LRClib utilities: parsers, objects, models"""

from chronograph.internal import Constants

# LRClib API asks for adding a User-Agent with application signature to the API requests
APP_SIGNATURE_HEADER: str = (
  f"Chronograph v{Constants.VERSION} (https://github.com/Dzheremi2/Chronograph)"
)
