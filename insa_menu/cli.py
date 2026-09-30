"""
Interface en ligne de commande (CLI) pour insa-menu.
"""

from __future__ import annotations
import argparse
import datetime
import http.server
import json
import socketserver
import sys
from typing import Optional

from .client import InsaMenuClient
from .exporter import MenuExporter
from .formatter import format_day, format_week
from .models import DayMenu, WeekMenu
from .scraper import InsaMenuScraper


def run_server(port: int = 8080, host: str = "0.0.0.0"):
    """Lance le serveur Web et API REST complet."""
    from .server import start_server
    start_server(port=port, host=host)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="insa-menu",
        description="Scraper et explorateur des menus des restaurants de l'INSA Lyon (RI, Pied du Saule, etc.)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Commandes disponibles")

    # Commande: today
    p_today = subparsers.add_parser("today", help="Affiche les menus du jour")
    p_today.add_argument("--date", "-d", help="Date cible au format YYYY-MM-DD (défaut: aujourd'hui)")
    p_today.add_argument("--json", action="store_true", help="Afficher au format JSON")

    # Commande: week
    p_week = subparsers.add_parser("week", help="Affiche les menus de toute la semaine")
    p_week.add_argument("--ref-date", "-d", help="Date de référence au format YYYY-MM-DD")
    p_week.add_argument("--json", action="store_true", help="Afficher au format JSON")

    # Commande: export
    p_export = subparsers.add_parser("export", help="Exporte les menus vers un fichier (json, md, csv, ics)")
    p_export.add_argument("--format", "-f", choices=["json", "md", "csv", "ics"], default="json")
    p_export.add_argument("--output", "-o", required=True, help="Chemin du fichier de sortie")
    p_export.add_argument("--ref-date", "-d", help="Date de référence au format YYYY-MM-DD")

    # Commande: dish
    p_dish = subparsers.add_parser("dish", help="Consulte la fiche détaillée d'un plat (ingrédients, origines)")
    p_dish.add_argument("dish_id", help="Identifiant du plat (Fit_id)")

    # Commande: allergens
    subparsers.add_parser("allergens", help="Liste les allergènes répertoriés")

    # Commande: serve
    p_serve = subparsers.add_parser("serve", help="Lance un serveur HTTP REST local pour exposer les menus")
    p_serve.add_argument("--port", "-p", type=int, default=8080, help="Port d'écoute (défaut: 8080)")
    p_serve.add_argument("--host", default="0.0.0.0", help="Adresse d'écoute")

    args = parser.parse_args(argv)

    if not args.command or args.command == "today":
        scraper = InsaMenuScraper()
        target_date = getattr(args, "date", None)
        day_menu = scraper.scrape_today(target_date)
        if not day_menu:
            print("Aucun menu trouvé pour cette date.")
            return 1

        if getattr(args, "json", False):
            print(json.dumps(day_menu.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(format_day(day_menu))
        return 0

    elif args.command == "week":
        scraper = InsaMenuScraper()
        week_menu = scraper.scrape_week(ref_date=args.ref_date)
        if args.json:
            print(MenuExporter.to_json(week_menu))
        else:
            print(format_week(week_menu))
        return 0

    elif args.command == "export":
        scraper = InsaMenuScraper()
        week_menu = scraper.scrape_week(ref_date=args.ref_date)
        fmt = args.format.lower()
        if fmt == "json":
            content = MenuExporter.to_json(week_menu)
        elif fmt == "md":
            content = MenuExporter.to_markdown(week_menu)
        elif fmt == "csv":
            content = MenuExporter.to_csv(week_menu)
        elif fmt == "ics":
            content = MenuExporter.to_ical(week_menu)
        else:
            print(f"Format inconnu: {fmt}")
            return 1

        with open(args.output, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Export réussi dans {args.output} ({fmt.upper()})")
        return 0

    elif args.command == "dish":
        client = InsaMenuClient()
        try:
            detail = client.get_dish_detail(args.dish_id)
            print(json.dumps(detail, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Erreur lors de la récupération de la fiche {args.dish_id}: {e}")
            return 1
        return 0

    elif args.command == "allergens":
        client = InsaMenuClient()
        try:
            algs = client.get_allergens()
            print("🏷️  ALLERGÈNES OFFICIELS INSA LYON :")
            for a in algs:
                print(f"  [{a.get('Alg_id')}] {a.get('LibAlg')}")
        except Exception as e:
            print(f"Erreur: {e}")
            return 1
        return 0

    elif args.command == "serve":
        run_server(port=args.port, host=args.host)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
