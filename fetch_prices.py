"""
fetch_prices.py – Belépési pont. Ezt futtatja a GitHub Actions.
"""

import logging
import sys

from src.config import load_config
from src.tracker import PriceTracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

if __name__ == "__main__":
    config = load_config("config.yaml")
    tracker = PriceTracker(config)
    tracker.run()
