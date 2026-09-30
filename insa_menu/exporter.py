"""
Exportateurs de menus vers différents formats : JSON, Markdown, CSV et iCalendar (.ics).
"""

from __future__ import annotations
import csv
import io
import json
from typing import List

from .models import DayMenu, Dish, Meal, WeekMenu


class MenuExporter:
    """Exportation des données de menus dans plusieurs formats standards."""

    @staticmethod
    def to_json(week_menu: WeekMenu, indent: int = 2) -> str:
        """Exporte le menu de la semaine en chaîne JSON formatée."""
        return json.dumps(week_menu.to_dict(), indent=indent, ensure_ascii=False)

    @staticmethod
    def to_markdown(week_menu: WeekMenu) -> str:
        """Génère un document Markdown complet de la semaine."""
        lines = [
            f"# 🍽️ Menus des Restaurants - INSA Lyon",
            f"**Semaine du {week_menu.start_date} au {week_menu.end_date}**\n",
        ]

        for day in week_menu.days:
            lines.append(f"## 📅 {day.day_name} ({day.date})\n")
            if not day.meals:
                lines.append("*Aucun menu disponible pour ce jour.*\n")
                continue

            for meal in day.meals:
                if meal.is_empty:
                    continue
                lines.append(f"### {meal.restaurant_name} - {meal.meal_label}\n")

                cat_map = [
                    ("Entrées", meal.entries),
                    ("Plats principaux", meal.mains),
                    ("Accompagnements", meal.sides),
                    ("Fromages", meal.cheeses),
                    ("Desserts", meal.desserts),
                ]

                for title, dishes in cat_map:
                    if dishes:
                        lines.append(f"**{title} :**")
                        for d in dishes:
                            labels_str = f" `{' '.join(d.labels)}`" if d.labels else ""
                            cal_str = f" *({d.calories} kcal)*" if d.calories else ""
                            alg_str = f" *(Allergènes: {', '.join(d.allergens)})*" if d.allergens else ""
                            lines.append(f"- {d.name}{cal_str}{labels_str}{alg_str}")
                        lines.append("")
                lines.append("---\n")

        return "\n".join(lines)

    @staticmethod
    def to_csv(week_menu: WeekMenu) -> str:
        """Exporte tous les plats sous forme tabulaire CSV."""
        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")
        writer.writerow([
            "Date",
            "Jour",
            "Restaurant",
            "Service",
            "Catégorie",
            "Plat",
            "Calories (kcal)",
            "Poids (g)",
            "Végétarien",
            "Bio",
            "Fait Maison",
            "Viande Française",
            "Labels",
            "Allergènes",
        ])

        for day in week_menu.days:
            for meal in day.meals:
                for dish in meal.dishes:
                    writer.writerow([
                        day.date,
                        day.day_name,
                        meal.restaurant_name,
                        meal.meal_label,
                        dish.category,
                        dish.name,
                        dish.calories or "",
                        dish.net_weight or "",
                        "Oui" if dish.is_vegetarian else "Non",
                        "Oui" if dish.is_bio else "Non",
                        "Oui" if dish.is_homemade else "Non",
                        "Oui" if dish.is_french_meat else "Non",
                        ", ".join(dish.labels),
                        ", ".join(dish.allergens),
                    ])

        return output.getvalue()

    @staticmethod
    def to_ical(week_menu: WeekMenu) -> str:
        """
        Génère un fichier de calendrier iCalendar (.ics) pour ajouter
        les déjeuners et dîners dans un agenda (Google Calendar, Apple, etc.).
        """
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//INSA Lyon//Menu Scraper//FR",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "X-WR-CALNAME:Menus INSA Lyon",
        ]

        for day in week_menu.days:
            clean_date = day.date.replace("-", "")
            for meal in day.meals:
                if meal.is_empty:
                    continue

                is_lunch = meal.meal_type == "lunch"
                start_hour = "113000" if is_lunch else "184500"
                end_hour = "134500" if is_lunch else "203000"

                summary = f"Menu {meal.restaurant_name} ({meal.meal_label})"
                desc_items = []
                for d in meal.dishes:
                    desc_items.append(f"- {d.name}")
                description = "\\n".join(desc_items)

                uid = f"{day.date}-{meal.restaurant_id}-{meal.meal_type}@insa-lyon.fr"

                lines.extend([
                    "BEGIN:VEVENT",
                    f"UID:{uid}",
                    f"DTSTART:{clean_date}T{start_hour}",
                    f"DTEND:{clean_date}T{end_hour}",
                    f"SUMMARY:{summary}",
                    f"DESCRIPTION:{description}",
                    f"LOCATION:{meal.restaurant_name}, Campus de la Doua",
                    "END:VEVENT",
                ])

        lines.append("END:VCALENDAR")
        return "\r\n".join(lines)
