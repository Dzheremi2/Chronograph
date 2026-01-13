import sys  # noqa: INP001
import traceback

from ...chronograph.internal import Constants  # noqa: TID252
from ...chronograph.main import main  # noqa: TID252

if __name__ == "__main__":
  try:
    sys.exit(main(Constants.VERSION))
  except Exception:
    traceback.print_exc()
    sys.exit(1)
