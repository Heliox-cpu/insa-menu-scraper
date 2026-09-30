"""
Exemple rapide d'utilisation du scraper de menu INSA Lyon.
"""

import sys
from pathlib import Path

# Permet d'exécuter l'exemple sans avoir installé le paquet
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from insa_menu import InsaMenuClient, InsaMenuScraper


def main():
    print("=== 1. Exploration de l'API officielle INSA Lyon ===")
    client = InsaMenuClient()

    # Liste des restaurants
    groups = client.get_groups()
    print("Groupes de restauration trouvés :")
    for g in groups:
        print(f" • [{g['GrpEta_id']}] {g['NomGrpEta']}")

    print("\n=== 2. Récupération des repas du jour ===")
    scraper = InsaMenuScraper(client)

    today = scraper.scrape_today()
    if today:
        print(f"Menu pour {today.day_name} {today.date} :")
        for meal in today.meals:
            if not meal.is_empty:
                print(f"\n👉 {meal.restaurant_name} ({meal.meal_label}) :")
                print(f"   Plats principaux : {', '.join(d.name for d in meal.mains)}")
                vegs = [d.name for d in meal.dishes if d.is_vegetarian]
                if vegs:
                    print(f"   🌱 Options végétariennes : {', '.join(vegs)}")


if __name__ == "__main__":
    main()
