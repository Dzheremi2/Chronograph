import sys  # noqa: INP001

from chronograph.internal import Constants
from chronograph.main import main

if __name__ == "__main__":
  try:
    sys.exit(main(Constants.VERSION))
  except Exception:
    sys.exit(1)
