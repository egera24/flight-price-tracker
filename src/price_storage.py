"""
price_storage.py – Jegyárak mentése és olvasása CSV fájlból.
"""

import csv
import logging
import os
from datetime import datetime
from typing import List

from src.flight_search import FlightOffer

logger = logging.getLogger(__name__)

CSV_HEADERS = [
    "timestamp",
    "search_type",
    "origin",
    "destination",
    "departure_date",
    "departure_time",
    "return_departure_time",
    "carrier",
    "price",
    "currency",
]


class PriceStorage:
    """
    Felelős a repülőjegy-árak CSV fájlba írásáért és az előzmények olvasásáért.
    Minden futás az aktuális időbélyeggel hozzáfűz a meglévő fájlhoz,
    így teljes ártörténet épül fel.
    """

    def __init__(self, csv_path: str, timestamp_format: str) -> None:
        self._csv_path = csv_path
        self._timestamp_format = timestamp_format
        self._ensure_directory()

    # ------------------------------------------------------------------
    # Publikus metódusok
    # ------------------------------------------------------------------

    def save(self, offers: List[FlightOffer]) -> None:
        """Menti az ajánlatokat a CSV fájlba. Ha a fájl még nem létezik, fejlécet ír."""
        timestamp = datetime.utcnow().strftime(self._timestamp_format)
        file_exists = os.path.isfile(self._csv_path)

        with open(self._csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)

            if not file_exists:
                writer.writeheader()
                logger.info("Új CSV fájl létrehozva: %s", self._csv_path)

            rows_written = 0
            for offer in offers:
                writer.writerow(self._offer_to_row(offer, timestamp))
                rows_written += 1

        logger.info("%d sor mentve a CSV-be (%s).", rows_written, self._csv_path)

    def load_all(self) -> List[dict]:
        """Visszaadja az összes eddig mentett sort szótárak listájaként."""
        if not os.path.isfile(self._csv_path):
            return []

        with open(self._csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    # ------------------------------------------------------------------
    # Belső segédmetódusok
    # ------------------------------------------------------------------

    def _offer_to_row(self, offer: FlightOffer, timestamp: str) -> dict:
        return {
            "timestamp": timestamp,
            "search_type": offer.search_type,
            "origin": offer.origin,
            "destination": offer.destination,
            "departure_date": offer.departure_date,
            "departure_time": offer.departure_time,
            "return_departure_time": offer.return_departure_time or "",
            "carrier": offer.carrier,
            "price": offer.price,
            "currency": offer.currency,
        }

    def _ensure_directory(self) -> None:
        """Létrehozza a szülőkönyvtárat, ha még nem létezik."""
        directory = os.path.dirname(self._csv_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
