"""
Exemple d'export des menus de la semaine au format iCalendar (.ics) et Markdown (.md).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from insa_menu import InsaMenuScraper, MenuExporter


def main():
    scraper = InsaMenuScraper()
    print("Récupération des menus de la semaine...")
    week_menu = scraper.scrape_week()

    # Export iCalendar
    ics_data = MenuExporter.to_ical(week_menu)
    ics_path = Path(__file__).parent / "insa_menus.ics"
    with open(ics_path, "w", encoding="utf-8") as f:
        f.write(ics_data)
    print(f"✅ Calendrier exporté : {ics_path}")

    # Export Markdown
    md_data = MenuExporter.to_markdown(week_menu)
    md_path = Path(__file__).parent / "insa_menus.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_data)
    print(f"✅ Menu Markdown exporté : {md_path}")


if __name__ == "__main__":
    main()
