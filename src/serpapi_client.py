"""
serpapi_client.py – SerpApi HTTP kommunikáció.
Nincs szükség OAuth2 tokenre – egyetlen API kulcs elegendő.
"""

import logging
from typing import Any, Dict

import requests

from src.config import AppConfig

logger = logging.getLogger(__name__)


class SerpApiRequestError(Exception):
    """API hívási hiba."""


class SerpApiClient:
    """
    Kezeli a SerpApi Google Flights engine-nel való kommunikációt.
    Minden kérésnél a konfigurációból és a környezeti változóból
    olvassa be az API kulcsot – nem tárolja el belső állapotban.
    """

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._session = requests.Session()

    def search_flights(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Meghívja a SerpApi Google Flights végpontot.
        Az api_key és engine paramétert automatikusan hozzáadja.
        """
        full_params = {
            "engine": self._config.serpapi.engine,
            "api_key": self._config.api_key,
            **params,
        }

        logger.debug("SerpApi kérés paraméterek: %s", {
            k: v for k, v in full_params.items() if k != "api_key"  # kulcsot nem logoljuk
        })

        response = self._session.get(
            self._config.serpapi.base_url,
            params=full_params,
            timeout=30,
        )

        if response.status_code != 200:
            raise SerpApiRequestError(
                f"SerpApi kérés sikertelen: {response.status_code} – {response.text}"
            )

        data = response.json()

        # SerpApi API szintű hibák a válasz törzsében
        if "error" in data:
            raise SerpApiRequestError(f"SerpApi hiba: {data['error']}")

        return data
