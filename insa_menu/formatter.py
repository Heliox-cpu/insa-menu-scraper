"""
Formattage console élégant pour l'affichage des menus dans le terminal.
"""

from __future__ import annotations
import sys
from typing import List

from .models import DayMenu, Dish, Meal, WeekMenu

# Codes ANSI pour un affichage soigné
COLOR_RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
RED = "\033[31m"


def _supports_color() -> bool:
    return sys.stdout.isatty()


def c(text: str, color_code: str) -> str:
    if not _supports_color():
        return text
    return f"{color_code}{text}{COLOR_RESET}"


def format_dish(dish: Dish) -> str:
    """Formate une ligne de plat avec labels et informations nutritionnelles."""
    badges = []
    if dish.is_vegetarian:
        badges.append(c("🌱 VEG", GREEN))
    if dish.is_bio:
        badges.append(c("🌿 BIO", GREEN))
    if dish.is_french_meat:
        badges.append(c("🇫🇷 VF", BLUE))
    if dish.is_homemade:
        badges.append(c("👨‍🍳 Fait maison", YELLOW))

    for tag in dish.labels:
        if tag not in ("VEG", "BIO", "VF", "FM"):
            badges.append(c(f"[{tag}]", MAGENTA))

    info = []
    if dish.calories:
        info.append(f"{dish.calories} kcal")
    if dish.net_weight:
        info.append(f"{dish.net_weight} g")

    info_str = f" ({', '.join(info)})" if info else ""
    badge_str = f" {' '.join(badges)}" if badges else ""
    return f"  • {c(dish.name, BOLD)}{info_str}{badge_str}"


def format_category(title: str, dishes: List[Dish]) -> str:
    """Formate un groupe de plats d'une catégorie donnée."""
    if not dishes:
        return ""
    lines = [f"\n  {c(title.upper(), CYAN + BOLD)}"]
    for d in dishes:
        lines.append(format_dish(d))
    return "\n".join(lines)


def format_meal(meal: Meal) -> str:
    """Formate un repas (déjeuner ou dîner d'un restaurant)."""
    if meal.is_empty:
        return f"{c('— ' + meal.restaurant_name + ' (' + meal.meal_label + ') : Aucun menu publié', DIM)}"

    header = f"🍽️  {c(meal.restaurant_name, BOLD)} - {c(meal.meal_label, YELLOW + BOLD)}"
    parts = [header, "=" * len(f"🍽️  {meal.restaurant_name} - {meal.meal_label}")]

    cat_map = [
        ("Entrées", meal.entries),
        ("Plats", meal.mains),
        ("Accompagnements", meal.sides),
        ("Fromages", meal.cheeses),
        ("Desserts", meal.desserts),
    ]

    for title, dishes in cat_map:
        cat_str = format_category(title, dishes)
        if cat_str:
            parts.append(cat_str)

    return "\n".join(parts)


def format_day(day_menu: DayMenu) -> str:
    """Formate la journée complète."""
    date_header = f"📅 {day_menu.day_name} {day_menu.date}"
    sep = "━" * 50
    lines = [
        "",
        c(sep, BLUE),
        c(date_header, BOLD + BLUE),
        c(sep, BLUE),
        "",
    ]
    if not day_menu.meals:
        lines.append(c("Aucun repas disponible pour ce jour.", DIM))
        return "\n".join(lines)

    meal_blocks = []
    for m in day_menu.meals:
        if not m.is_empty:
            meal_blocks.append(format_meal(m))

    if not meal_blocks:
        lines.append(c("Aucun repas programmé pour ce jour.", DIM))
    else:
        lines.append("\n\n".join(meal_blocks))

    return "\n".join(lines)


def format_week(week_menu: WeekMenu) -> str:
    """Formate la semaine complète."""
    title = f"✨ MENUS INSA LYON - SEMAINE DU {week_menu.start_date} AU {week_menu.end_date} ✨"
    banner = "╔" + "═" * (len(title) + 2) + "╗"
    banner_end = "╚" + "═" * (len(title) + 2) + "╝"
    lines = [
        "",
        c(banner, GREEN + BOLD),
        c(f"║ {title} ║", GREEN + BOLD),
        c(banner_end, GREEN + BOLD),
    ]
    for day in week_menu.days:
        lines.append(format_day(day))
    return "\n".join(lines)
