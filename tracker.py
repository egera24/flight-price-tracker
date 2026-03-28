"""
tracker.py – A fő orchestrátor, amely összefonja az összes modult.
"""

import logging

from src.serpapi_client import SerpApiClient
from src.config import AppConfig
from src.flight_search import FlightSearcher
from src.price_storage import PriceStorage

logger = logging.getLogger(__name__)


class PriceTracker:
    """
    Összefogja a teljes folyamatot:
      1. Lekéri a jegyárakat az Amadeus API-n keresztül.
      2. Menti az eredményeket a CSV fájlba.
    """

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._client = SerpApiClient(config)
        self._searcher = FlightSearcher(self._client, config)
        self._storage = PriceStorage(
            csv_path=config.output.csv_path,
            timestamp_format=config.output.timestamp_format,
        )

    def run(self) -> None:
        """Egyetlen futási ciklus végrehajtása."""
        logger.info("=== Price Tracker futás kezdete ===")

        try:
            offers = self._searcher.fetch_all()

            if not offers:
                logger.warning("Nem érkezett vissza egyetlen ajánlat sem.")
                return

            self._storage.save(offers)
            self._log_summary(offers)

        except Exception as e:
            logger.error("Hiba a futás során: %s", e, exc_info=True)
            raise

        logger.info("=== Price Tracker futás befejezve ===")

    def _log_summary(self, offers) -> None:
        """Rövid összefoglaló a konzolra az aktuális legolcsóbb árakról."""
        logger.info("--- Aktuális legolcsóbb ajánlatok ---")
        for search_type in ("outbound", "inbound", "roundtrip"):
            relevant = [o for o in offers if o.search_type == search_type]
            if relevant:
                cheapest = min(relevant, key=lambda o: o.price)
                if search_type == "roundtrip":
                    logger.info(
                        "%-10s | oda: %s, vissza: %s | %.2f %s",
                        search_type,
                        cheapest.departure_time,
                        cheapest.return_departure_time or "–",
                        cheapest.price,
                        cheapest.currency,
                    )
                else:
                    logger.info(
                        "%-10s | %s | %.2f %s",
                        search_type,
                        cheapest.departure_time,
                        cheapest.price,
                        cheapest.currency,
                    )
