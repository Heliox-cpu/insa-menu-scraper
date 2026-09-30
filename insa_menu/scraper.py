"""
Scraper de haut niveau pour récupérer et synchroniser les menus de l'INSA Lyon.
"""

from __future__ import annotations
import datetime
import logging
from typing import List, Optional

from .client import InsaMenuClient
from .models import DayMenu, Meal, WeekMenu
from .parser import MenuParser

logger = logging.getLogger(__name__)


# Configuration des services connus de l'INSA Lyon
KNOWN_SERVICES = [
    {
        "restaurant_id": "4",
        "restaurant_name": "Le Restaurant INSA (RI)",
        "con_id": "1",
        "men_id": "32",
        "meal_type": "lunch",
        "meal_label": "Déjeuner",
    },
    {
        "restaurant_id": "4",
        "restaurant_name": "Le Restaurant INSA (RI)",
        "con_id": "1",
        "men_id": "38",
        "meal_type": "dinner",
        "meal_label": "Dîner",
    },
    {
        "restaurant_id": "4",
        "restaurant_name": "Le Restaurant INSA (RI)",
        "con_id": "1",
        "men_id": "123",
        "meal_type": "lunch",
        "meal_label": "Déjeuner Samedi",
    },
    {
        "restaurant_id": "4",
        "restaurant_name": "Le Restaurant INSA (RI)",
        "con_id": "1",
        "men_id": "125",
        "meal_type": "lunch",
        "meal_label": "Déjeuner Dimanche",
    },
    {
        "restaurant_id": "4",
        "restaurant_name": "Le Restaurant INSA (RI)",
        "con_id": "1",
        "men_id": "126",
        "meal_type": "dinner",
        "meal_label": "Dîner Dimanche",
    },
]


class InsaMenuScraper:
    """
    Orchestre la récupération des données via le client API et leur transformation
    en structures complètes DayMenu et WeekMenu.
    """

    def __init__(self, client: Optional[InsaMenuClient] = None):
        self.client = client or InsaMenuClient()

    def get_week_bounds(self, target_date: Optional[datetime.date] = None) -> tuple[str, str]:
        """
        Détermine la date de début (lundi) et de fin (dimanche) de la semaine.
        Tente d'abord de lire les paramètres officiels de l'API.
        """
        try:
            params = self.client.get_parameters()
            if params and isinstance(params, list) and len(params) > 0:
                p0 = params[0]
                if p0.get("DatDebOuv") and p0.get("DatFinOuv"):
                    return p0["DatDebOuv"], p0["DatFinOuv"]
        except Exception as e:
            logger.warning("Impossible de récupérer les paramètres de semaine: %s", e)

        # Calcul automatique par défaut
        d = target_date or datetime.date.today()
        start = d - datetime.timedelta(days=d.weekday())
        end = start + datetime.timedelta(days=6)
        return start.isoformat(), end.isoformat()

    def scrape_week(self, ref_date: Optional[str] = None) -> WeekMenu:
        """
        Scrape l'ensemble des repas de tous les restaurants pour la semaine.
        """
        if ref_date:
            d = datetime.date.fromisoformat(ref_date)
            start_date = (d - datetime.timedelta(days=d.weekday())).isoformat()
            end_date = (d + datetime.timedelta(days=6 - d.weekday())).isoformat()
        else:
            start_date, end_date = self.get_week_bounds()

        all_meals: List[Meal] = []

        for svc in KNOWN_SERVICES:
            try:
                raw_data = self.client.get_semaine(
                    eta_id=svc["restaurant_id"],
                    con_id=svc["con_id"],
                    men_id=svc["men_id"],
                    date_str=start_date,
                )
                meals = MenuParser.parse_menu_semaine(
                    raw_semaine=raw_data,
                    restaurant_id=svc["restaurant_id"],
                    restaurant_name=svc["restaurant_name"],
                    meal_type=svc["meal_type"],
                    meal_label=svc["meal_label"],
                )
                all_meals.extend(meals)
            except Exception as e:
                logger.error(
                    "Erreur lors de la récupération pour %s (%s): %s",
                    svc["restaurant_name"],
                    svc["meal_label"],
                    e,
                )

        # Enrichissement automatique des plats avec leurs allergènes officiels
        self._enrich_allergens(all_meals)

        return MenuParser.build_week_menu(all_meals, start_date, end_date)

    def _enrich_allergens(self, meals: List[Meal]) -> None:
        """Enrichit les plats avec leurs allergènes déclarés via l'API Plat/."""
        dish_ids = list({d.id for m in meals for d in m.dishes if d.id})
        if not dish_ids:
            return

        from concurrent.futures import ThreadPoolExecutor

        def _fetch_algs(did: str):
            try:
                detail = self.client.get_dish_detail(did)
                algs = [
                    a.get("LibAlg", "").strip()
                    for a in detail.get("Allergenes", [])
                    if a.get("LibAlg") and a.get("LibAlg").strip()
                ]
                return did, algs
            except Exception:
                return did, []

        allergens_map = {}
        try:
            with ThreadPoolExecutor(max_workers=10) as executor:
                for did, algs in executor.map(_fetch_algs, dish_ids):
                    if algs:
                        allergens_map[did] = algs
        except Exception as e:
            logger.warning("Erreur lors de la récupération groupée des allergènes: %s", e)

        for m in meals:
            for dish in m.dishes:
                if dish.id in allergens_map:
                    dish.allergens = allergens_map[dish.id]

    def scrape_today(self, target_date: Optional[str] = None) -> Optional[DayMenu]:
        """
        Récupère les menus de la journée spécifiée (ou aujourd'hui par défaut).
        """
        today_str = target_date or datetime.date.today().isoformat()
        week_menu = self.scrape_week(ref_date=today_str)
        return week_menu.get_day(today_str)
