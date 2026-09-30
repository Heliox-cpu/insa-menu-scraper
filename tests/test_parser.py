"""
Tests unitaires pour le parser et les modèles de données de insa_menu.
"""

import unittest
from insa_menu.models import Dish, Meal, DayMenu, WeekMenu
from insa_menu.parser import MenuParser
from insa_menu.exporter import MenuExporter


class TestMenuParser(unittest.TestCase):
    def test_extract_labels(self):
        clean_name, tags, label_names = MenuParser.extract_labels("Steak haché <VF><BBC>")
        self.assertEqual(clean_name, "Steak haché")
        self.assertIn("VF", tags)
        self.assertIn("BBC", tags)
        self.assertIn("Viande française", label_names)
        self.assertIn("Bleu Blanc Cœur", label_names)

    def test_parse_dish_vegetarian(self):
        raw = {
            "Fit_id": "1234",
            "LibFit": "Nuggets végétal <VEG>",
            "LibCatFit": "PLAT",
            "KilCal": "150.5",
            "PdsNet": "0.120",
        }
        dish = MenuParser.parse_dish(raw)
        self.assertEqual(dish.id, "1234")
        self.assertEqual(dish.name, "Nuggets végétal")
        self.assertEqual(dish.category, "PLAT")
        self.assertEqual(dish.calories, 150.5)
        self.assertEqual(dish.net_weight, 120.0)
        self.assertTrue(dish.is_vegetarian)
        self.assertFalse(dish.is_french_meat)

    def test_meal_categorization(self):
        d1 = Dish(id="1", name="Salade", category="ENTREE")
        d2 = Dish(id="2", name="Pâtes", category="PLAT")
        d3 = Dish(id="3", name="Haricots", category="GARNITURE")
        d4 = Dish(id="4", name="Yaourt", category="FROMAGE")
        d5 = Dish(id="5", name="Pomme", category="DESSERT")

        meal = Meal(
            restaurant_id="4",
            restaurant_name="RI",
            date="2026-09-28",
            meal_type="lunch",
            meal_label="Déjeuner",
            dishes=[d1, d2, d3, d4, d5],
        )

        self.assertEqual(len(meal.entries), 1)
        self.assertEqual(len(meal.mains), 1)
        self.assertEqual(len(meal.sides), 1)
        self.assertEqual(len(meal.cheeses), 1)
        self.assertEqual(len(meal.desserts), 1)
        self.assertFalse(meal.is_empty)

    def test_export_formats(self):
        d1 = Dish(id="1", name="Pâtes bio <BIO>", category="PLAT", is_bio=True)
        meal = Meal(
            restaurant_id="4",
            restaurant_name="RI",
            date="2026-09-28",
            meal_type="lunch",
            meal_label="Déjeuner",
            dishes=[d1],
        )
        day = DayMenu(date="2026-09-28", day_name="Lundi", meals=[meal])
        week = WeekMenu(start_date="2026-09-28", end_date="2026-10-04", days=[day])

        # Test JSON
        json_out = MenuExporter.to_json(week)
        self.assertIn("Pâtes bio", json_out)

        # Test Markdown
        md_out = MenuExporter.to_markdown(week)
        self.assertIn("# 🍽️ Menus des Restaurants - INSA Lyon", md_out)
        self.assertIn("Pâtes bio", md_out)

        # Test CSV
        csv_out = MenuExporter.to_csv(week)
        self.assertIn("Pâtes bio", csv_out)
        self.assertIn("PLAT", csv_out)

        # Test ICS
        ics_out = MenuExporter.to_ical(week)
        self.assertIn("BEGIN:VCALENDAR", ics_out)
        self.assertIn("Pâtes bio", ics_out)


if __name__ == "__main__":
    unittest.main()
