"""
flight_search.py – Járatkeresés, ajánlatok elemzése és időpontra szűrés.
A SerpApi Google Flights engine válaszformátumát dolgozza fel.

SerpApi válasz struktúra (releváns mezők):
  best_flights[]:
    flights[]:
      departure_airport: { id, name, time }   # time: "YYYY-MM-DD HH:MM"
      arrival_airport:   { id, name, time }
      airline: "Turkish Airlines"
      flight_number: "TK123"
    price: 189
    type: "One way" | "Round trip"

  other_flights[]:                             # Ugyanolyan struktúra
    ...
"""

import logging
from dataclasses import dataclass
from typing import List, Optional

from src.config import AppConfig, FlightLegConfig
from src.serpapi_client import SerpApiClient

logger = logging.getLogger(__name__)

TYPE_ONE_WAY   = 2
TYPE_ROUNDTRIP = 1


@dataclass
class FlightOffer:
    """Egyetlen járatajánlatot reprezentál."""
    search_type: str
    departure_time: str
    departure_date: str
    origin: str
    destination: str
    price: float
    currency: str
    carrier: str
    return_departure_time: Optional[str] = None
    return_departure_date: Optional[str] = None


class FlightSearcher:
    """
    Elvégzi az összes szükséges keresést a SerpApi-n keresztül,
    majd az eredményeket FlightOffer objektumok listájaként adja vissza.
    """

    def __init__(self, client: SerpApiClient, config: AppConfig) -> None:
        self._client = client
        self._config = config

    def fetch_all(self) -> List[FlightOffer]:
        results: List[FlightOffer] = []
        results.extend(self._search_one_way(self._config.flights.outbound, "outbound"))
        results.extend(self._search_one_way(self._config.flights.inbound, "inbound"))
        results.extend(self._search_roundtrip())
        logger.info("Összesen %d releváns ajánlat találva.", len(results))
        return results

    # ------------------------------------------------------------------
    # Keresési metódusok
    # ------------------------------------------------------------------

    def _search_one_way(self, leg: FlightLegConfig, search_type: str) -> List[FlightOffer]:
        params = self._build_params(
            origin=leg.origin,
            destination=leg.destination,
            outbound_date=leg.date,
            flight_type=TYPE_ONE_WAY,
        )
        logger.info("%s keresés: %s → %s, %s", search_type, leg.origin, leg.destination, leg.date)
        raw = self._client.search_flights(params)
        offers = self._parse_offers(raw, search_type)
        filtered = self._filter_by_departure_and_carrier(offers, leg.target_departures, leg.carrier_code)
        logger.info("%s: %d releváns ajánlat a szűrés után.", search_type, len(filtered))
        return filtered

    def _search_roundtrip(self) -> List[FlightOffer]:
        out = self._config.flights.outbound
        inb = self._config.flights.inbound
        params = self._build_params(
            origin=out.origin,
            destination=out.destination,
            outbound_date=out.date,
            flight_type=TYPE_ROUNDTRIP,
            return_date=inb.date,
        )
        logger.info(
            "Roundtrip keresés: %s → %s, oda: %s, vissza: %s",
            out.origin, out.destination, out.date, inb.date,
        )
        raw = self._client.search_flights(params)
        offers = self._parse_roundtrip_offers(raw)
        filtered = self._filter_by_departure_and_carrier(offers, out.target_departures, out.carrier_code)
        logger.info("Roundtrip: %d releváns ajánlat a szűrés után.", len(filtered))
        return filtered

    # ------------------------------------------------------------------
    # Paraméterek
    # ------------------------------------------------------------------

    def _build_params(
        self,
        origin: str,
        destination: str,
        outbound_date: str,
        flight_type: int,
        return_date: Optional[str] = None,
    ) -> dict:
        params = {
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": outbound_date,
            "type": flight_type,
            "currency": self._config.search.currency,
            "hl": self._config.search.language,
            "adults": self._config.search.adults,
        }
        if return_date:
            params["return_date"] = return_date
        return params

    # ------------------------------------------------------------------
    # Válasz feldolgozása
    # ------------------------------------------------------------------

    def _parse_offers(self, raw: dict, search_type: str) -> List[FlightOffer]:
        all_items = raw.get("best_flights", []) + raw.get("other_flights", [])
        offers = []
        for item in all_items:
            try:
                segments = item.get("flights", [])
                if not segments:
                    continue
                first_seg = segments[0]
                dep_full = first_seg["departure_airport"]["time"]  # "2025-08-10 09:00"
                dep_date, dep_time = dep_full[:10], dep_full[11:16]
                offers.append(FlightOffer(
                    search_type=search_type,
                    departure_time=dep_time,
                    departure_date=dep_date,
                    origin=first_seg["departure_airport"]["id"],
                    destination=segments[-1]["arrival_airport"]["id"],
                    price=float(item["price"]),
                    currency=self._config.search.currency,
                    carrier=first_seg.get("airline", ""),
                ))
            except (KeyError, ValueError, IndexError) as e:
                logger.warning("Ajánlat feldolgozási hiba: %s", e)
        return offers

    def _parse_roundtrip_offers(self, raw: dict) -> List[FlightOffer]:
        all_items = raw.get("best_flights", []) + raw.get("other_flights", [])
        offers = []
        for item in all_items:
            try:
                out_segs = item.get("flights", [])
                ret_flights = item.get("return_flights", [])
                if not out_segs:
                    continue

                first_out = out_segs[0]
                out_dep_full = first_out["departure_airport"]["time"]
                out_dep_date, out_dep_time = out_dep_full[:10], out_dep_full[11:16]

                ret_dep_time: Optional[str] = None
                ret_dep_date: Optional[str] = None
                if ret_flights:
                    ret_segs = ret_flights[0].get("flights", [{}])
                    if ret_segs:
                        ret_dep_full = ret_segs[0].get("departure_airport", {}).get("time", "")
                        if ret_dep_full:
                            ret_dep_date = ret_dep_full[:10]
                            ret_dep_time = ret_dep_full[11:16]

                offers.append(FlightOffer(
                    search_type="roundtrip",
                    departure_time=out_dep_time,
                    departure_date=out_dep_date,
                    origin=first_out["departure_airport"]["id"],
                    destination=out_segs[-1]["arrival_airport"]["id"],
                    price=float(item["price"]),
                    currency=self._config.search.currency,
                    carrier=first_out.get("airline", ""),
                    return_departure_time=ret_dep_time,
                    return_departure_date=ret_dep_date,
                ))
            except (KeyError, ValueError, IndexError) as e:
                logger.warning("Roundtrip feldolgozási hiba: %s", e)
        return offers

    # ------------------------------------------------------------------
    # Szűrés
    # ------------------------------------------------------------------

    @staticmethod
    def _filter_by_departure_and_carrier(
        offers: List[FlightOffer],
        target_times: List[str],
        carrier_code: str,
    ) -> List[FlightOffer]:
        """
        Szűrés indulási idő és légitársaság szerint.
        A SerpApi teljes nevet ad vissza (pl. "Turkish Airlines"),
        ezért a carrier_code-t (pl. "TK") részleges névegyezéssel is ellenőrizzük.
        """
        carrier_map = {"TK": "turkish"}

        carrier_keyword = carrier_map.get(carrier_code, carrier_code.lower())

        return [
            o for o in offers
            if o.departure_time in target_times
            and carrier_keyword in o.carrier.lower()
        ]
