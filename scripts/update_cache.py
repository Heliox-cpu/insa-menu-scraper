"""
Script de mise à jour automatique du cache des menus et plats de l'INSA Lyon.
Utilisé par le workflow GitHub Actions et exécutable manuellement.
"""

from __future__ import annotations
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor

# Ajouter la racine au path si exécuté directement
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from insa_menu.client import InsaMenuClient
from insa_menu.exporter import MenuExporter
from insa_menu.scraper import InsaMenuScraper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("update_cache")


def main() -> None:
    data_dir = os.path.join(root_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    menu_file = os.path.join(data_dir, "cached_menu.json")
    dishes_file = os.path.join(data_dir, "cached_dishes.json")

    # 1. Test rapide de connectivité vers l'API INSA (timeout 5s)
    probe_client = InsaMenuClient(timeout=5)
    try:
        logger.info("Test de connectivité vers le serveur officiel de l'INSA Lyon...")
        probe_client.get_parameters()
        logger.info("Connexion établie avec succès avec le serveur INSA.")
    except Exception as e:
        logger.warning(
            "Le serveur officiel INSA est inaccessible actuellement (%s). Conservation du cache existant sans erreur.",
            e,
        )
        sys.exit(0)

    # 2. Récupération des menus de la semaine
    logger.info("Récupération des menus de la semaine...")
    scraper = InsaMenuScraper()
    try:
        week = scraper.scrape_week()
    except Exception as e:
        logger.warning("Échec de la récupération des menus (%s). Conservation du cache existant.", e)
        sys.exit(0)

    total_meals = sum(len(m.meals) for m in week.days)
    logger.info("Repas récupérés: %d à travers %d jours.", total_meals, len(week.days))

    if total_meals == 0:
        logger.warning(
            "Aucun repas renvoyé par l'INSA (semaine vide ou indisponible). Conservation du cache existant."
        )
        sys.exit(0)

    # 3. Sauvegarder cached_menu.json
    with open(menu_file, "w", encoding="utf-8") as f:
        f.write(MenuExporter.to_json(week))
    logger.info("Fichier %s mis à jour avec succès.", menu_file)

    # 4. Pré-mettre en cache les fiches techniques des plats
    unique_ids = list({d.id for m in week.days for meal in m.meals for d in meal.dishes if d.id})
    logger.info("Mise en cache des fiches techniques pour %d plats...", len(unique_ids))
    client = InsaMenuClient(timeout=10)
    dishes_cache = {}

    # Charger le cache existant pour préserver les fiches déjà récupérées
    if os.path.exists(dishes_file):
        try:
            with open(dishes_file, "r", encoding="utf-8") as f:
                dishes_cache = json.load(f)
        except Exception:
            dishes_cache = {}

    def fetch_one(did: str):
        try:
            return did, client.get_dish_detail(did)
        except Exception:
            return did, None

    with ThreadPoolExecutor(max_workers=10) as executor:
        for did, res in executor.map(fetch_one, unique_ids):
            if res:
                dishes_cache[did] = res

    if dishes_cache:
        with open(dishes_file, "w", encoding="utf-8") as f:
            json.dump(dishes_cache, f, indent=2, ensure_ascii=False)
        logger.info("Fichier %s mis à jour (%d fiches sauvegardées).", dishes_file, len(dishes_cache))

    logger.info("Mise à jour terminée avec succès !")


if __name__ == "__main__":
    main()
