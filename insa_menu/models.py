"""
Modèles de données pour les menus et plats de l'INSA Lyon.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


@dataclass
class Label:
    """Label de qualité ou provenance (ex: Bio, Fait maison, Viande française)."""
    tag: str
    name: str
    id: Optional[str] = None


KNOWN_LABELS: Dict[str, str] = {
    "BBC": "Bleu Blanc Cœur",
    "VF": "Viande française",
    "FLF": "Fruits et légumes de France",
    "FM": "Fait maison",
    "VEG": "Végétarien",
    "HVE": "Haute valeur environnementale",
    "BIO": "Bio",
}


@dataclass
class Dish:
    """Représente un plat ou aliment servi au restaurant."""
    id: str
    name: str
    category: str  # ENTREE, PLAT, GARNITURE, SAUCE, FROMAGE, DESSERT, DIVERS
    calories: Optional[float] = None
    net_weight: Optional[float] = None  # en grammes ou kg
    labels: List[str] = field(default_factory=list)
    label_names: List[str] = field(default_factory=list)
    is_vegetarian: bool = False
    is_bio: bool = False
    is_french_meat: bool = False
    is_homemade: bool = False
    allergens: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("raw_data", None)
        return d


@dataclass
class Meal:
    """Représente un service (déjeuner ou dîner) pour un restaurant et un jour donné."""
    restaurant_id: str
    restaurant_name: str
    date: str  # Format YYYY-MM-DD
    meal_type: str  # 'lunch' ou 'dinner'
    meal_label: str  # 'Déjeuner' ou 'Dîner'
    dishes: List[Dish] = field(default_factory=list)

    @property
    def entries(self) -> List[Dish]:
        return [d for d in self.dishes if d.category == "ENTREE"]

    @property
    def mains(self) -> List[Dish]:
        return [d for d in self.dishes if d.category == "PLAT"]

    @property
    def sides(self) -> List[Dish]:
        return [d for d in self.dishes if d.category in ("GARNITURE", "SAUCE")]

    @property
    def cheeses(self) -> List[Dish]:
        return [d for d in self.dishes if d.category == "FROMAGE"]

    @property
    def desserts(self) -> List[Dish]:
        return [d for d in self.dishes if d.category == "DESSERT"]

    @property
    def is_empty(self) -> bool:
        return len(self.dishes) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "restaurant_id": self.restaurant_id,
            "restaurant_name": self.restaurant_name,
            "date": self.date,
            "meal_type": self.meal_type,
            "meal_label": self.meal_label,
            "is_empty": self.is_empty,
            "dishes": [d.to_dict() for d in self.dishes],
            "categories": {
                "entrees": [d.to_dict() for d in self.entries],
                "plats": [d.to_dict() for d in self.mains],
                "accompagnements": [d.to_dict() for d in self.sides],
                "fromages": [d.to_dict() for d in self.cheeses],
                "desserts": [d.to_dict() for d in self.desserts],
            }
        }


@dataclass
class DayMenu:
    """Ensemble des repas d'une journée pour tous les restaurants."""
    date: str  # YYYY-MM-DD
    day_name: str  # Lundi, Mardi, etc.
    meals: List[Meal] = field(default_factory=list)

    def get_meals_by_restaurant(self, restaurant_id: str) -> List[Meal]:
        return [m for m in self.meals if str(m.restaurant_id) == str(restaurant_id)]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "day_name": self.day_name,
            "meals": [m.to_dict() for m in self.meals]
        }


@dataclass
class WeekMenu:
    """Menus complets d'une semaine."""
    start_date: str
    end_date: str
    days: List[DayMenu] = field(default_factory=list)

    def get_day(self, date_str: str) -> Optional[DayMenu]:
        for d in self.days:
            if d.date == date_str:
                return d
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "days": [d.to_dict() for d in self.days]
        }


@dataclass
class Restaurant:
    """Informations sur un restaurant."""
    id: str
    name: str
    group_id: Optional[str] = None
    group_name: Optional[str] = None
    is_active: bool = True
