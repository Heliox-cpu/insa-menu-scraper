"""
Module de parsing et nettoyage des menus et plats de l'INSA Lyon.
"""

from __future__ import annotations
import datetime
import re
from typing import Any, Dict, List, Optional, Tuple

from .models import Dish, Meal, DayMenu, WeekMenu, KNOWN_LABELS

LABEL_REGEX = re.compile(r"<([A-Z0-9_]+)>", re.IGNORECASE)

CATEGORY_NORMALIZE = {
    "ENTREE": "ENTREE",
    "PLAT": "PLAT",
    "GARNITURE": "GARNITURE",
    "SAUCE": "SAUCE",
    "FROMAGE": "FROMAGE",
    "DESSERT": "DESSERT",
}

FRENCH_DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]


class MenuParser:
    """Parse et structure les données brutes issues de l'API de l'INSA Lyon."""

    @staticmethod
    def extract_labels(raw_name: str) -> Tuple[str, List[str], List[str]]:
        """
        Extrait les balises de labels comme <BBC>, <VF>, <FM>, <VEG> du nom du plat.
        Retourne (nom_nettoyé, tags, noms_labels).
        """
        tags = [m.upper() for m in LABEL_REGEX.findall(raw_name)]
        clean_name = LABEL_REGEX.sub("", raw_name).strip()
        # Nettoyer les espaces multiples
        clean_name = re.sub(r"\s+", " ", clean_name)
        label_names = [KNOWN_LABELS.get(t, t) for t in tags]
        return clean_name, tags, label_names

    @classmethod
    def parse_dish(cls, raw: Dict[str, Any]) -> Dish:
        """Parse un plat brut en objet Dish structuré."""
        raw_name = raw.get("LibFit", "") or raw.get("name", "")
        clean_name, tags, label_names = cls.extract_labels(raw_name)

        category = (raw.get("LibCatFit") or raw.get("category") or "DIVERS").upper()
        category = CATEGORY_NORMALIZE.get(category, category)

        # Calories
        calories: Optional[float] = None
        if raw.get("KilCal") is not None:
            try:
                calories = round(float(raw["KilCal"]), 1)
            except (ValueError, TypeError):
                pass

        # Poids net
        net_weight: Optional[float] = None
        if raw.get("PdsNet") is not None:
            try:
                # Convertir kg en grammes si < 1.0 (ex: 0.150 kg -> 150 g)
                val = float(raw["PdsNet"])
                net_weight = round(val * 1000, 1) if val < 2.0 else round(val, 1)
            except (ValueError, TypeError):
                pass

        is_veg = "VEG" in tags or "végétarien" in clean_name.lower() or "vegetarien" in clean_name.lower()
        is_bio = "BIO" in tags or "bio" in clean_name.lower().split()
        is_french_meat = "VF" in tags
        is_homemade = "FM" in tags

        allergens = []
        if raw.get("ListeAllergenes"):
            allergens = [a.strip() for a in str(raw["ListeAllergenes"]).split(",") if a.strip()]

        return Dish(
            id=str(raw.get("Fit_id", "")),
            name=clean_name,
            category=category,
            calories=calories,
            net_weight=net_weight,
            labels=tags,
            label_names=label_names,
            is_vegetarian=is_veg,
            is_bio=is_bio,
            is_french_meat=is_french_meat,
            is_homemade=is_homemade,
            allergens=allergens,
            raw_data=raw,
        )

    @classmethod
    def parse_menu_semaine(
        cls,
        raw_semaine: Dict[str, Any],
        restaurant_id: str,
        restaurant_name: str,
        meal_type: str,
        meal_label: str,
    ) -> List[Meal]:
        """
        Parse la réponse de l'endpoint Semaine/... en une liste d'objets Meal (un par jour).
        """
        menu_items = raw_semaine.get("MenuSemaine", []) or []
        items_by_date: Dict[str, List[Dish]] = {}

        for item in menu_items:
            date_str = item.get("DatPlaMen")
            if not date_str:
                continue
            if date_str not in items_by_date:
                items_by_date[date_str] = []
            dish = cls.parse_dish(item)
            items_by_date[date_str].append(dish)

        meals = []
        for date_str, dishes in sorted(items_by_date.items()):
            meal = Meal(
                restaurant_id=restaurant_id,
                restaurant_name=restaurant_name,
                date=date_str,
                meal_type=meal_type,
                meal_label=meal_label,
                dishes=dishes,
            )
            meals.append(meal)
        return meals

    @classmethod
    def build_week_menu(
        cls,
        all_meals: List[Meal],
        start_date: str,
        end_date: str,
    ) -> WeekMenu:
        """
        Regroupe tous les repas de plusieurs restaurants par date sous un WeekMenu complet.
        """
        meals_by_date: Dict[str, List[Meal]] = {}
        for m in all_meals:
            meals_by_date.setdefault(m.date, []).append(m)

        # Générer tous les jours entre start_date et end_date
        d_start = datetime.date.fromisoformat(start_date)
        d_end = datetime.date.fromisoformat(end_date)
        current = d_start

        days: List[DayMenu] = []
        while current <= d_end:
            curr_str = current.isoformat()
            day_name = FRENCH_DAYS[current.weekday()]
            day_meals = meals_by_date.get(curr_str, [])
            days.append(DayMenu(
                date=curr_str,
                day_name=day_name,
                meals=day_meals,
            ))
            current += datetime.timedelta(days=1)

        return WeekMenu(
            start_date=start_date,
            end_date=end_date,
            days=days,
        )
