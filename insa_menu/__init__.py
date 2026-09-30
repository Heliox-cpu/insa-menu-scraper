"""
INSA Menu Scraper & API Client
Scraper et client Python pour les menus des restaurants universitaires de l'INSA Lyon.
"""

from .client import InsaMenuClient
from .scraper import InsaMenuScraper
from .models import Dish, Meal, DayMenu, WeekMenu, Restaurant
from .parser import MenuParser
from .exporter import MenuExporter
from .formatter import format_day, format_week

__version__ = "1.0.0"
__all__ = [
    "InsaMenuClient",
    "InsaMenuScraper",
    "Dish",
    "Meal",
    "DayMenu",
    "WeekMenu",
    "Restaurant",
    "MenuParser",
    "MenuExporter",
    "format_day",
    "format_week",
]
