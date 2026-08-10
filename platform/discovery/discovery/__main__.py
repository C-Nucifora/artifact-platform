"""Entry point: python -m discovery"""

import logging
import os
import sys

from discovery.config import Config
from discovery.service import run_service


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("DISCOVERY_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    run_service(Config.from_env(os.environ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
