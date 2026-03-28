"""
config.py – Konfigurációs fájl betöltése és validálása.
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import List


@dataclass
class SerpApiConfig:
    base_url: str
    engine: str


@dataclass
class SearchConfig:
    currency: str
    language: str
    adults: int


@dataclass
class FlightLegConfig:
    origin: str
    destination: str
    date: str
    carrier_code: str
    target_departures: List[str]


@dataclass
class FlightsConfig:
    outbound: FlightLegConfig
    inbound: FlightLegConfig


@dataclass
class OutputConfig:
    csv_path: str
    timestamp_format: str


@dataclass
class AppConfig:
    serpapi: SerpApiConfig
    search: SearchConfig
    flights: FlightsConfig
    output: OutputConfig

    # Az API kulcs mindig környezeti változóból érkezik (soha nem a YAML-ból)
    @property
    def api_key(self) -> str:
        key = os.getenv("SERPAPI_KEY")
        if not key:
            raise EnvironmentError("A SERPAPI_KEY környezeti változó nincs beállítva.")
        return key


def load_config(path: str = "config.yaml") -> AppConfig:
    """Betölti és visszaadja a konfigurációt a megadott YAML fájlból."""
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    serpapi = SerpApiConfig(**raw["serpapi"])
    search = SearchConfig(**raw["search"])
    output = OutputConfig(**raw["output"])

    flights = FlightsConfig(
        outbound=FlightLegConfig(**raw["flights"]["outbound"]),
        inbound=FlightLegConfig(**raw["flights"]["inbound"]),
    )

    return AppConfig(
        serpapi=serpapi,
        search=search,
        flights=flights,
        output=output,
    )
