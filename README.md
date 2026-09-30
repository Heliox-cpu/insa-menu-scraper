# 🍽️ INSA Lyon Menu Scraper & API Client

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Zero-Dependencies](https://img.shields.io/badge/Dependencies-Standard%20Library%20Only-brightgreen.svg)](#caractéristiques)

Un scraper et client Python moderne, rapide et autonome pour récupérer en temps réel les menus des restaurants universitaires de l'**INSA Lyon** (**Le Restaurant INSA / RI**, **Le Pied du Saule**, **L'Olivier**...).

---

## ✨ Points Forts

- **🚀 100% Autonome (Zéro dépendance)** : Fonctionne nativement avec la bibliothèque standard Python (`urllib`, `dataclasses`, `json`). Aucune installation de paquet tiers requise !
- **⚡ API Officielle en direct** : Rétro-ingénierie de l'API REST officielle des restaurants (`menu-restaurants.insa-lyon.fr`) avec calcul dynamique de jeton temporel sécurisé (MD5 + Basic Auth).
- **🥗 Labels & Nutrition** : Détection automatique des plats végétariens (`🌱 VEG`), bio (`🌿 BIO`), fait maison (`👨‍🍳 FM`), viande française (`🇫🇷 VF`), calories (kcal) et grammages.
- **📅 Export Multi-formats** :
  - **JSON** structuré pour vos scripts et applications.
  - **Markdown** prêt pour Notion, GitHub ou un bot Discord.
  - **CSV** pour le suivi nutritionnel sous Excel / Google Sheets.
  - **iCalendar (.ics)** pour synchroniser les menus dans Google Calendar ou Apple Agenda.
- **💻 CLI Ergonomique** : Affichage coloré et structuré directement dans votre terminal.
- **🌐 Micro-serveur Web intégré** : Lancez `insa-menu serve` pour exposer instantanément une API REST locale et un flux `.ics`.

---

## 🏗️ Architecture du Projet

```text
fearless-faraday/
├── insa_menu/
│   ├── __init__.py      # Exports du package
│   ├── client.py        # Client HTTP avec authentification dynamique MD5 UTok
│   ├── models.py        # Modèles typés (Dish, Meal, DayMenu, WeekMenu, Restaurant)
│   ├── parser.py        # Parseur de tags (<BBC>, <VF>, <VEG>), nettoyage & calories
│   ├── scraper.py       # Orchestrateur de scraping des restaurants & services
│   ├── formatter.py     # Rendu console élégant avec couleurs ANSI
│   ├── exporter.py      # Export JSON, Markdown, CSV, iCalendar (.ics)
│   └── cli.py           # Interface CLI & micro-serveur HTTP
├── examples/
│   ├── quickstart.py        # Exemple simple d'intégration
│   └── export_calendar.py   # Exemple d'export iCal & Markdown
├── tests/
│   ├── test_client.py   # Tests de la signature et de l'API
│   └── test_parser.py   # Tests du parseur et des modèles
├── pyproject.toml       # Métadonnées de packaging
└── requirements.txt     # Fichier de dépendances (optionnelles)
```

---

## 🚀 Utilisation en Ligne de Commande (CLI)

Vous pouvez lancer le scraper directement via Python :

### 1. Afficher les menus du jour

```bash
python3 -m insa_menu.cli today
```

> **Exemple de sortie :**
> ```text
> ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
> 📅 Lundi 2026-09-28
> ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
> 
> 🍽️  Le Restaurant INSA (RI) - Déjeuner
> ======================================
>   ENTRÉES
>   • Céleri remoulade (62.0 kcal, 93.0 g)
>   • Melon et pastèque (21.4 kcal, 150.0 g)
>   • Salade multi-céréales (80.0 g)
> 
>   PLATS
>   • Nuggets végétal (110.0 g) 🌱 VEG
>   • Paupiette de veau grillée
> 
>   ACCOMPAGNEMENTS
>   • Sauce ail (329.8 kcal, 10.0 g) 👨‍🍳 Fait maison
>   • Pommes paillassons (200.0 g)
> ```

### 2. Afficher la semaine complète

```bash
python3 -m insa_menu.cli week
```

Pour une sortie au format JSON brut :
```bash
python3 -m insa_menu.cli today --json
```

### 3. Exporter les menus

```bash
# Export Markdown
python3 -m insa_menu.cli export -f md -o menu_semaine.md

# Export iCalendar (.ics pour votre agenda)
python3 -m insa_menu.cli export -f ics -o menus.ics

# Export CSV tabulaire
python3 -m insa_menu.cli export -f csv -o menus.csv

# Export JSON
python3 -m insa_menu.cli export -f json -o menus.json
```

### 4. Consulter la fiche technique complète d'un plat (ingrédients & allergènes)

```bash
python3 -m insa_menu.cli dish 8719
```

### 5. Démarrer le micro-serveur API REST local

```bash
python3 -m insa_menu.cli serve --port 8000
```
Le serveur expose instantanément :
- `GET http://localhost:8000/api/today` : Menu du jour au format JSON.
- `GET http://localhost:8000/api/week` : Menus de la semaine en JSON.
- `GET http://localhost:8000/menu.ics` : Flux calendrier synchronisable dans votre agenda.
- `GET http://localhost:8000/health` : Statut de santé.

---

## 🐍 Utilisation en Bibliothèque Python

```python
from insa_menu import InsaMenuScraper, InsaMenuClient, MenuExporter

scraper = InsaMenuScraper()

# 1. Récupérer le menu du jour
today = scraper.scrape_today()
print(f"Date : {today.date} ({today.day_name})")

for meal in today.meals:
    print(f"\nRestaurant : {meal.restaurant_name} - {meal.meal_label}")
    for dish in meal.mains:
        veg_tag = " [VEG]" if dish.is_vegetarian else ""
        print(f" - {dish.name} ({dish.calories or '?'} kcal){veg_tag}")

# 2. Récupérer la semaine complète
week = scraper.scrape_week()

# 3. Convertir en Markdown ou JSON
md_content = MenuExporter.to_markdown(week)
json_content = MenuExporter.to_json(week)
```

---

## 🧪 Lancer les Tests

Les tests unitaires vérifient la validité des modèles, le découpage des labels et la connexion à l'API :

```bash
python3 -m unittest discover tests
```

---

## 🔍 Comment fonctionne l'API sous le capot ?

L'INSA de Lyon utilise la solution de restauration **LiveSoft / Salamandre** hébergée sur `https://menu-restaurants.insa-lyon.fr`.

1. **Authentification dynamique :** L'API exige un en-tête `Authorization: Basic <token>` où `<token>` est le Base64 de :
   ```
   UTok:md5(YYYYMMDDHHmm + "85RrNDhZ9wz9")
   ```
   Ce jeton est automatiquement calculé à la minute près par le client `InsaMenuClient`.
2. **Endpoints principaux :**
   - `/API/public/v1/GroupeEtablissements` : Liste des pôles de restauration.
   - `/API/public/v1/Etablissements` : Restaurants actifs (RI, Pied du Saule...).
   - `/API/public/v1/Semaine/{eta_id}/{con_id}/{men_id}/{date}` : Données complètes de la semaine.
   - `/API/public/v1/Plat/{fit_id}/{con_id}` : Fiche recette (marchandises, allergènes, traçabilité).
   - `/API/public/v1/Pdf/{eta_id}/{con_id}/{men_id}/{date}/PDF` : Menu PDF officiel.

---

## 📜 Licence

Projet publié sous licence MIT.
