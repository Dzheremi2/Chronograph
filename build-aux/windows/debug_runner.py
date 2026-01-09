import sys  # noqa: INP001
import traceback

from chronograph.internal import Constants
from chronograph.main import main

if __name__ == "__main__":
  try:
    sys.exit(main(Constants.VERSION))
  except Exception:
    traceback.print_exc()
    sys.exit(1)
