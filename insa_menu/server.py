"""
Serveur Web autonome pour le tableau de bord des restaurants de l'INSA Lyon.
Fournit une interface web moderne aux couleurs officielles de l'INSA Lyon
et une API REST complète sans aucune dépendance externe.
"""

from __future__ import annotations
import datetime
import http.server
import json
import logging
import os
import socketserver
import sys
import urllib.parse
from typing import Optional

from .client import InsaMenuClient
from .exporter import MenuExporter
from .models import WeekMenu
from .scraper import InsaMenuScraper

logger = logging.getLogger(__name__)

INDEX_HTML_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public", "index.html")


def get_html_page() -> str:
    """Charge le template HTML de la page d'accueil depuis public/index.html."""
    if os.path.exists(INDEX_HTML_PATH):
        with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>INSA Lyon - Menus des Restaurants</h1><p>Erreur: Fichier public/index.html introuvable.</p>"


class InsaMenuWebHandler(http.server.SimpleHTTPRequestHandler):
    """Handler HTTP servant le site web réactif et l'API REST."""

    scraper = InsaMenuScraper()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. Page d'accueil Web (Dashboard interactif INSA Lyon)
        if path in ("/", "/index.html"):
            content = get_html_page().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        # 2. API: Menu du jour
        elif path == "/api/today":
            target_date = query.get("date", [None])[0]
            day_menu = self.scraper.scrape_today(target_date)
            data = day_menu.to_dict() if day_menu else {"error": "Aucun menu"}
            self._send_json(data)

        # 3. API: Menus de la semaine
        elif path == "/api/week":
            ref_date = query.get("ref_date", [None])[0]
            week_menu = self.scraper.scrape_week(ref_date=ref_date)
            self._send_json(week_menu.to_dict())

        # 4. API: Fiche technique d'un plat par ID
        elif path.startswith("/api/dish/"):
            dish_id = path.split("/")[-1]
            cached_dishes_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cached_dishes.json")
            if os.path.exists(cached_dishes_file):
                try:
                    with open(cached_dishes_file, "r", encoding="utf-8") as f:
                        dishes_cache = json.load(f)
                    if dish_id in dishes_cache:
                        self._send_json(dishes_cache[dish_id])
                        return
                except Exception:
                    pass

            try:
                client = InsaMenuClient()
                detail = client.get_dish_detail(dish_id)
                self._send_json(detail)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)

        # 5. API: Liste des allergènes
        elif path == "/api/allergens":
            try:
                client = InsaMenuClient()
                algs = client.get_allergens()
                self._send_json(algs)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)

        # 6. API: Exports (JSON, Markdown, CSV, iCal)
        elif path == "/api/export":
            fmt = query.get("format", ["json"])[0].lower()
            ref_date = query.get("ref_date", [None])[0]
            week_menu = self.scraper.scrape_week(ref_date=ref_date)

            if fmt == "md":
                content = MenuExporter.to_markdown(week_menu)
                mime = "text/markdown; charset=utf-8"
                ext = "md"
            elif fmt == "csv":
                content = MenuExporter.to_csv(week_menu)
                mime = "text/csv; charset=utf-8"
                ext = "csv"
            elif fmt == "ics":
                content = MenuExporter.to_ical(week_menu)
                mime = "text/calendar; charset=utf-8"
                ext = "ics"
            else:
                content = MenuExporter.to_json(week_menu)
                mime = "application/json; charset=utf-8"
                ext = "json"

            body = content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Disposition", f'attachment; filename="menus_insa.{ext}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        # 7. Flux iCalendar direct
        elif path in ("/menu.ics", "/api/calendar.ics"):
            week_menu = self.scraper.scrape_week()
            ics_content = MenuExporter.to_ical(week_menu).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/calendar; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="insa_menus.ics"')
            self.send_header("Content-Length", str(len(ics_content)))
            self.end_headers()
            self.wfile.write(ics_content)

        # 8. Santé
        elif path == "/health":
            self._send_json({
                "status": "healthy",
                "service": "insa-menu-scraper",
                "restaurant": "Le Restaurant INSA (RI)",
                "timestamp": datetime.datetime.now().isoformat()
            })

        else:
            self.send_error(404, "Page non trouvée")

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        sys.stderr.write(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {format % args}\n")


def start_server(port: int = 8080, host: str = "0.0.0.0") -> None:
    """Démarre le serveur web sur le port et l'adresse spécifiés."""
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((host, port), InsaMenuWebHandler) as httpd:
        print(f"🚀 [INSA Menu] Site self-hosted disponible sur http://localhost:{port}")
        print(f"   • Dashboard Web UI :     http://localhost:{port}")
        print(f"   • API Menu du jour :     http://localhost:{port}/api/today")
        print(f"   • API Semaine entière :  http://localhost:{port}/api/week")
        print(f"   • Flux calendrier iCal : http://localhost:{port}/menu.ics")
        print(f"   • Health check :         http://localhost:{port}/health")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nArrêt du serveur.")


if __name__ == "__main__":
    start_server()
