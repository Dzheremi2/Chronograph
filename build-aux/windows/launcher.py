import sys  # noqa: INP001

from ...chronograph.internal import Constants  # noqa: TID252
from ...chronograph.main import main  # noqa: TID252

if __name__ == "__main__":
  try:
    sys.exit(main(Constants.VERSION))
  except Exception:
    sys.exit(1)
