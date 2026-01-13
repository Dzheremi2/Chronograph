import sys
import traceback

from chronograph.internal import Constants
from chronograph.main import main

if __name__ == "__main__":
  if Constants.PREFIX.endswith("Devel"):
    try:
      sys.exit(main(Constants.VERSION))
    except Exception:
      traceback.print_exc()
      sys.exit(1)
  else:
    try:
      sys.exit(main(Constants.VERSION))
    except Exception:
      sys.exit(1)
