"""
Point d'entrée Serverless Vercel pour l'API des menus de l'INSA Lyon.
"""

from __future__ import annotations
import datetime
import http.server
import json
import os
import sys
import time
import urllib.parse

# Ajouter la racine du projet au path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from insa_menu.client import InsaMenuClient
from insa_menu.exporter import MenuExporter
from insa_menu.scraper import InsaMenuScraper

client_inst = InsaMenuClient(timeout=3)
scraper = InsaMenuScraper(client=client_inst)

_WEEK_CACHE: dict = {"dict": None, "timestamp": 0}


def get_cached_week_dict(ref_date: str | None = None) -> dict:
    """
    Récupère le dictionnaire des menus de la semaine.
    Tente d'abord le scraper en direct, puis bascule sur le cache snapshot local
    si le serveur de l'INSA bloque l'adresse IP du datacenter cloud.
    """
    now = time.time()
    if not ref_date and _WEEK_CACHE["dict"] and (now - _WEEK_CACHE["timestamp"] < 600):
        return _WEEK_CACHE["dict"]

    # Sur Vercel (datacenter cloud filtré par le firewall INSA), servir le cache snapshot instantanément
    if os.environ.get("VERCEL"):
        cached_file = os.path.join(root_dir, "data", "cached_menu.json")
        if os.path.exists(cached_file):
            with open(cached_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not ref_date:
                    _WEEK_CACHE["dict"] = data
                    _WEEK_CACHE["timestamp"] = now
                return data

    # 1. Tentative live scraper
    try:
        week_menu = scraper.scrape_week(ref_date=ref_date)
        week_dict = week_menu.to_dict()
        # Si des repas ont été trouvés
        has_meals = any(len(d.get("meals", [])) > 0 for d in week_dict.get("days", []))
        if has_meals:
            if not ref_date:
                _WEEK_CACHE["dict"] = week_dict
                _WEEK_CACHE["timestamp"] = now
            return week_dict
    except Exception:
        pass

    # 2. Fallback sur le snapshot local
    cached_file = os.path.join(root_dir, "data", "cached_menu.json")
    if os.path.exists(cached_file):
        with open(cached_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not ref_date:
                _WEEK_CACHE["dict"] = data
                _WEEK_CACHE["timestamp"] = now
            return data

    return {"start_date": "", "end_date": "", "days": []}


def dict_to_ical(week_dict: dict) -> str:
    """Génère un flux iCalendar (.ics) depuis le dictionnaire du menu."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//INSA Lyon//Menu Scraper//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Menus INSA Lyon",
    ]

    for day in week_dict.get("days", []):
        date_str = day.get("date", "")
        clean_date = date_str.replace("-", "")
        for meal in day.get("meals", []):
            dishes = meal.get("dishes", [])
            if not dishes:
                continue

            is_lunch = meal.get("meal_type") == "lunch"
            start_hour = "113000" if is_lunch else "184500"
            end_hour = "134500" if is_lunch else "203000"

            rest_name = meal.get("restaurant_name", "Le Restaurant INSA (RI)")
            meal_label = meal.get("meal_label", "Déjeuner")
            summary = f"Menu {rest_name} ({meal_label})"
            desc_items = [f"- {d.get('name')}" for d in dishes]
            description = "\\n".join(desc_items)

            uid = f"{date_str}-{meal.get('restaurant_id', '4')}-{meal.get('meal_type', 'lunch')}@insa-lyon.fr"

            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTART:{clean_date}T{start_hour}",
                f"DTEND:{clean_date}T{end_hour}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{description}",
                f"LOCATION:{rest_name}, Campus de la Doua",
                "END:VEVENT",
            ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


def dict_to_markdown(week_dict: dict) -> str:
    """Génère un document Markdown depuis le dictionnaire du menu."""
    lines = [
        "# 🍽️ Menus Le Restaurant INSA (RI)",
        f"**Semaine du {week_dict.get('start_date')} au {week_dict.get('end_date')}**\n",
    ]

    for day in week_dict.get("days", []):
        lines.append(f"## 📅 {day.get('day_name')} ({day.get('date')})\n")
        meals = day.get("meals", [])
        if not meals:
            lines.append("*Aucun menu disponible pour ce jour.*\n")
            continue

        for meal in meals:
            lines.append(f"### {meal.get('restaurant_name')} - {meal.get('meal_label')}\n")
            cats = meal.get("categories", {})

            cat_map = [
                ("Entrées", cats.get("entrees", [])),
                ("Plats principaux", cats.get("plats", [])),
                ("Accompagnements", cats.get("accompagnements", [])),
                ("Fromages", cats.get("fromages", [])),
                ("Desserts", cats.get("desserts", [])),
            ]

            for title, dishes in cat_map:
                if dishes:
                    lines.append(f"**{title} :**")
                    for d in dishes:
                        labels = d.get("labels", [])
                        labels_str = f" `{' '.join(labels)}`" if labels else ""
                        cal = d.get("calories")
                        cal_str = f" *({cal} kcal)*" if cal else ""
                        lines.append(f"- {d.get('name')}{cal_str}{labels_str}")
                    lines.append("")
            lines.append("---\n")

    return "\n".join(lines)


def dict_to_csv(week_dict: dict) -> str:
    """Génère un CSV tabulaire depuis le dictionnaire du menu."""
    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Date", "Jour", "Restaurant", "Service", "Catégorie", "Plat",
        "Calories (kcal)", "Poids (g)", "Végétarien", "Bio", "Fait Maison", "Viande Française", "Labels"
    ])

    for day in week_dict.get("days", []):
        for meal in day.get("meals", []):
            for d in meal.get("dishes", []):
                writer.writerow([
                    day.get("date"),
                    day.get("day_name"),
                    meal.get("restaurant_name"),
                    meal.get("meal_label"),
                    d.get("category"),
                    d.get("name"),
                    d.get("calories") or "",
                    d.get("net_weight") or "",
                    "Oui" if d.get("is_vegetarian") else "Non",
                    "Oui" if d.get("is_bio") else "Non",
                    "Oui" if d.get("is_homemade") else "Non",
                    "Oui" if d.get("is_french_meat") else "Non",
                    ", ".join(d.get("labels", [])),
                ])

    return output.getvalue()


class handler(http.server.BaseHTTPRequestHandler):
    """Handler Vercel Serverless Function."""

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        forwarded_uri = self.headers.get("x-forwarded-uri") or self.headers.get("x-matched-path") or ""
        endpoint_param = query.get("endpoint", [""])[0]

        req_route = ""
        if endpoint_param:
            req_route = "/" + endpoint_param.lstrip("/")
        elif forwarded_uri:
            req_route = urllib.parse.urlparse(forwarded_uri).path
        else:
            req_route = parsed.path

        # 0. Diagnostic
        if req_route in ("/api/debug", "/debug") or req_route.endswith("/debug"):
            res = {
                "datacenter_probe": "ok",
                "cached_file_exists": os.path.exists(os.path.join(root_dir, "data", "cached_menu.json")),
                "timestamp": datetime.datetime.now().isoformat(),
            }
            self._send_json(res)
            return

        # 1. API: Menu du jour
        if req_route in ("/api/today", "/today") or req_route.endswith("/today"):
            target_date = query.get("date", [None])[0] or datetime.date.today().isoformat()
            week_dict = get_cached_week_dict(ref_date=target_date)
            days = week_dict.get("days", [])
            day_match = next((d for d in days if d.get("date") == target_date), None)
            data = day_match or (days[0] if days else {"error": "Aucun menu"})
            self._send_json(data)

        # 2. API: Semaine entière
        elif req_route in ("/api/week", "/week") or req_route.endswith("/week"):
            ref_date = query.get("ref_date", [None])[0]
            week_dict = get_cached_week_dict(ref_date=ref_date)
            self._send_json(week_dict)

        # 3. API: Fiche plat par ID
        elif "/dish/" in req_route:
            dish_id = req_route.rstrip("/").split("/")[-1]
            try:
                detail = client_inst.get_dish_detail(dish_id)
                self._send_json(detail)
            except Exception:
                # Fallback: rechercher dans les plats locaux
                week_dict = get_cached_week_dict()
                found_dish = None
                for day in week_dict.get("days", []):
                    for meal in day.get("meals", []):
                        for dish in meal.get("dishes", []):
                            if str(dish.get("id")) == str(dish_id):
                                found_dish = dish
                                break
                if found_dish:
                    self._send_json({
                        "FicheTechnique": {"LibFit": found_dish.get("name")},
                        "Marchandises": [{"LibDen": found_dish.get("name")}],
                        "Allergenes": [],
                        "OrigineViandes": [],
                    })
                else:
                    self._send_json({"error": "Plat non trouvé"}, status=404)

        # 4. API: Allergènes
        elif req_route in ("/api/allergens", "/allergens") or req_route.endswith("/allergens"):
            try:
                algs = client_inst.get_allergens()
                self._send_json(algs)
            except Exception:
                self._send_json([
                    {"Alg_id": "1", "LibAlg": "Gluten"},
                    {"Alg_id": "2", "LibAlg": "Crustacés"},
                    {"Alg_id": "3", "LibAlg": "Lait"},
                    {"Alg_id": "4", "LibAlg": "Oeufs"},
                    {"Alg_id": "5", "LibAlg": "Fruit à Coque"},
                    {"Alg_id": "6", "LibAlg": "Poisson"},
                    {"Alg_id": "7", "LibAlg": "Soja"},
                ])

        # 5. API: Exports
        elif req_route in ("/api/export", "/export") or req_route.endswith("/export"):
            fmt = query.get("format", ["json"])[0].lower()
            ref_date = query.get("ref_date", [None])[0]
            week_dict = get_cached_week_dict(ref_date=ref_date)

            if fmt == "md":
                content = dict_to_markdown(week_dict)
                mime = "text/markdown; charset=utf-8"
                ext = "md"
            elif fmt == "csv":
                content = dict_to_csv(week_dict)
                mime = "text/csv; charset=utf-8"
                ext = "csv"
            elif fmt == "ics":
                content = dict_to_ical(week_dict)
                mime = "text/calendar; charset=utf-8"
                ext = "ics"
            else:
                content = json.dumps(week_dict, indent=2, ensure_ascii=False)
                mime = "application/json; charset=utf-8"
                ext = "json"

            body = content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Disposition", f'attachment; filename="menus_insa.{ext}"')
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        # 6. Flux iCalendar
        elif req_route in ("/menu.ics", "/api/calendar.ics") or req_route.endswith("menu.ics"):
            week_dict = get_cached_week_dict()
            ics_content = dict_to_ical(week_dict).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/calendar; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="insa_menus.ics"')
            self.send_header("Content-Length", str(len(ics_content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(ics_content)

        # 7. Santé
        elif req_route in ("/health", "/api/health") or req_route.endswith("/health"):
            self._send_json({
                "status": "healthy",
                "service": "insa-menu-scraper-vercel",
                "restaurant": "Le Restaurant INSA (RI)",
                "timestamp": datetime.datetime.now().isoformat()
            })

        # 8. Fallback sur la page d'accueil
        else:
            index_path = os.path.join(root_dir, "public", "index.html")
            if os.path.exists(index_path):
                with open(index_path, "r", encoding="utf-8") as f:
                    content = f.read().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, f"Route non trouvée: {req_route}")

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
