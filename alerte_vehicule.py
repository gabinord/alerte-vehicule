"""
🚗 SCRIPT D'ALERTES VÉHICULES - TELEGRAM
==========================================
Sites surveillés : LeBonCoin, AutoScout24, La Centrale, ParuVendu, Occasion.fr
Zones géographiques : 100 km autour de Châtellerault + 100 km autour de Saumur

AVANT DE LANCER :
    pip install requests beautifulsoup4 schedule

CONFIGURATION :
    1. Crée un bot Telegram (voir README en bas du fichier)
    2. Remplis TELEGRAM_BOT_TOKEN et TELEGRAM_CHAT_ID
    3. Lance le script : python alerte_vehicule.py
"""

import requests
from bs4 import BeautifulSoup
import schedule
import time
import json
import os
import math
from datetime import datetime

# ============================================================
# ⚙️ CONFIGURATION - MODIFIE CES VALEURS
# ============================================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")

# 🔍 Critères globaux
RECHERCHE = {
    "prix_max":  2500,   # Budget maximum en euros
    "annee_min": 2000,   # Année minimum du véhicule
}

# ⏰ Fréquence de vérification (en minutes)
FREQUENCE_MINUTES = 30

# ============================================================
# 📍 ZONES GÉOGRAPHIQUES - 100 km autour de chaque ville
# ============================================================
# Châtellerault : lat 46.8177, lon 0.5460
# Saumur        : lat 47.2667, lon -0.0833

ZONES = [
    {
        "nom":      "Châtellerault",
        "lat":      46.8177,
        "lon":      0.5460,
        "rayon_km": 100,
    },
    {
        "nom":      "Saumur",
        "lat":      47.2667,
        "lon":      -0.0833,
        "rayon_km": 100,
    },
]

def distance_km(lat1, lon1, lat2, lon2):
    """Calcule la distance en km entre deux points GPS (formule Haversine)."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))

def est_dans_zone(lat, lon):
    """Retourne (True, label) si le point est dans une zone, sinon (False, None)."""
    for zone in ZONES:
        dist = distance_km(zone["lat"], zone["lon"], lat, lon)
        if dist <= zone["rayon_km"]:
            return True, f"{zone['nom']} ({int(dist)} km)"
    return False, None

# Cache pour éviter de re-géocoder les mêmes villes
_cache_geo = {}

def geocoder_ville(ville):
    """Convertit un nom de ville en coordonnées GPS via Nominatim (OpenStreetMap)."""
    try:
        url    = "https://nominatim.openstreetmap.org/search"
        params = {"q": f"{ville}, France", "format": "json", "limit": 1, "countrycodes": "fr"}
        r      = requests.get(url, params=params, headers={"User-Agent": "alerte-vehicule/1.0"}, timeout=8)
        data   = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None, None

def verifier_localisation(lieu_texte):
    """
    Vérifie si un texte de lieu est dans l'une des zones.
    Si introuvable ou vide → accepté par défaut (on ne rate pas d'annonce).
    """
    if not lieu_texte or lieu_texte in ("France", "Lieu inconnu", ""):
        return True, "Zone non précisée"

    if lieu_texte in _cache_geo:
        lat, lon = _cache_geo[lieu_texte]
    else:
        lat, lon = geocoder_ville(lieu_texte)
        _cache_geo[lieu_texte] = (lat, lon)

    if lat is None:
        return True, "Zone non précisée"

    return est_dans_zone(lat, lon)

# ============================================================
# 🚗 MODÈLES RECHERCHÉS
# ============================================================
# Format : {"marque", "modele", "motorisations": ["essence"|"diesel"]}
# Mets un # devant une ligne pour désactiver temporairement un modèle.

MODELES = [
    # ── RENAULT ──────────────────────────────────────────────
    {"marque": "Renault",    "modele": "Clio",       "motorisations": ["essence", "diesel"]},
    {"marque": "Renault",    "modele": "Twingo",     "motorisations": ["essence"]},
    {"marque": "Renault",    "modele": "Megane",     "motorisations": ["essence", "diesel"]},   # ★ Ajout
    {"marque": "Renault",    "modele": "Scenic",     "motorisations": ["essence", "diesel"]},   # ★ Ajout
    {"marque": "Renault",    "modele": "Kangoo",     "motorisations": ["essence", "diesel"]},   # ★ Ajout utilitaire polyvalent

    # ── PEUGEOT ──────────────────────────────────────────────
    {"marque": "Peugeot",    "modele": "206",        "motorisations": ["essence", "diesel"]},
    {"marque": "Peugeot",    "modele": "207",        "motorisations": ["essence", "diesel"]},   # ★ Ajout
    {"marque": "Peugeot",    "modele": "307",        "motorisations": ["essence", "diesel"]},
    {"marque": "Peugeot",    "modele": "308",        "motorisations": ["essence", "diesel"]},   # ★ Ajout

    # ── CITROËN ──────────────────────────────────────────────
    {"marque": "Citroen",    "modele": "C2",         "motorisations": ["essence", "diesel"]},   # ★ Ajout citadine robuste
    {"marque": "Citroen",    "modele": "C3",         "motorisations": ["essence", "diesel"]},
    {"marque": "Citroen",    "modele": "C4",         "motorisations": ["essence", "diesel"]},
    {"marque": "Citroen",    "modele": "Xsara",      "motorisations": ["essence", "diesel"]},
    {"marque": "Citroen",    "modele": "Berlingo",   "motorisations": ["essence", "diesel"]},   # ★ Ajout familial/utilitaire

    # ── TOYOTA ───────────────────────────────────────────────
    {"marque": "Toyota",     "modele": "Yaris",      "motorisations": ["essence"]},
    {"marque": "Toyota",     "modele": "Aygo",       "motorisations": ["essence"]},             # ★ Ajout ultra fiable et économique

    # ── VOLKSWAGEN ───────────────────────────────────────────
    {"marque": "Volkswagen", "modele": "Golf",       "motorisations": ["essence", "diesel"]},
    {"marque": "Volkswagen", "modele": "Polo",       "motorisations": ["essence", "diesel"]},   # ★ Ajout
    {"marque": "Volkswagen", "modele": "Lupo",       "motorisations": ["essence", "diesel"]},   # ★ Ajout très économique

    # ── SKODA ────────────────────────────────────────────────
    {"marque": "Skoda",      "modele": "Octavia",    "motorisations": ["essence", "diesel"]},
    {"marque": "Skoda",      "modele": "Fabia",      "motorisations": ["essence", "diesel"]},   # ★ Ajout fiable et spacieuse

    # ── SEAT ─────────────────────────────────────────────────
    {"marque": "Seat",       "modele": "Ibiza",      "motorisations": ["essence", "diesel"]},
    {"marque": "Seat",       "modele": "Leon",       "motorisations": ["essence", "diesel"]},
    {"marque": "Seat",       "modele": "Arosa",      "motorisations": ["essence"]},             # ★ Ajout très abordable

    # ── FIAT ─────────────────────────────────────────────────
    {"marque": "Fiat",       "modele": "Panda",      "motorisations": ["essence"]},
    {"marque": "Fiat",       "modele": "Punto",      "motorisations": ["essence", "diesel"]},   # ★ Ajout
    {"marque": "Fiat",       "modele": "500",        "motorisations": ["essence"]},             # ★ Ajout très recherché

    # ── FORD ─────────────────────────────────────────────────
    {"marque": "Ford",       "modele": "Fiesta",     "motorisations": ["essence", "diesel"]},   # ★ Ajout
    {"marque": "Ford",       "modele": "Focus",      "motorisations": ["essence", "diesel"]},   # ★ Ajout

    # ── OPEL ─────────────────────────────────────────────────
    {"marque": "Opel",       "modele": "Corsa",      "motorisations": ["essence", "diesel"]},   # ★ Ajout
    {"marque": "Opel",       "modele": "Astra",      "motorisations": ["essence", "diesel"]},   # ★ Ajout

    # ── HONDA ────────────────────────────────────────────────
    {"marque": "Honda",      "modele": "Jazz",       "motorisations": ["essence"]},             # ★ Ajout fiabilité légendaire

    # ── DACIA ────────────────────────────────────────────────
    {"marque": "Dacia",      "modele": "Sandero",    "motorisations": ["essence", "diesel"]},   # ★ Ajout meilleur rapport qualité/prix
    {"marque": "Dacia",      "modele": "Logan",      "motorisations": ["essence", "diesel"]},   # ★ Ajout
]

# ── Détection motorisation dans le titre ─────────────────────
MOTS_ESSENCE = ["essence", "ess", "tsi", "vti", "thp", "tfsi", "gti",
                "1.0", "1.2", "1.4", "1.6 16v", "sce", "tce"]
MOTS_DIESEL  = ["diesel", "dci", "hdi", "tdi", "bluehdi", "cdti",
                "1.5 dci", "1.6 hdi", "1.9 tdi", "2.0 hdi", "jtd"]

def motorisation_acceptee(titre, motorisations_voulues):
    t = titre.lower()
    if "essence" in motorisations_voulues and "diesel" in motorisations_voulues:
        return True
    if "essence" in motorisations_voulues:
        if any(m in t for m in MOTS_ESSENCE):
            return True
        if not any(m in t for m in MOTS_DIESEL):
            return True  # Annonce sans info moteur → acceptée
    if "diesel" in motorisations_voulues:
        if any(m in t for m in MOTS_DIESEL):
            return True
    return False

def modele_correspond(titre):
    t = titre.lower()
    for m in MODELES:
        if m["marque"].lower() in t and m["modele"].lower() in t:
            if motorisation_acceptee(t, m["motorisations"]):
                return True
    return False

# ============================================================
# 📁 SUIVI DES ANNONCES DÉJÀ VUES
# ============================================================

FICHIER_ANNONCES_VUES = "annonces_vues.json"

def charger_annonces_vues():
    if os.path.exists(FICHIER_ANNONCES_VUES):
        with open(FICHIER_ANNONCES_VUES, "r") as f:
            return json.load(f)
    return []

def sauvegarder_annonce_vue(annonce_id):
    vues = charger_annonces_vues()
    if annonce_id not in vues:
        vues.append(annonce_id)
        vues = vues[-500:]
        with open(FICHIER_ANNONCES_VUES, "w") as f:
            json.dump(vues, f)

# ============================================================
# 📱 TELEGRAM
# ============================================================

def envoyer_alerte_telegram(message):
    url     = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message,
               "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        r = requests.post(url, data=payload, timeout=10)
        if r.status_code == 200:
            print(f"  ✅ Alerte envoyée → {message[55:100].strip()}...")
        else:
            print(f"  ❌ Erreur Telegram : {r.text}")
    except Exception as e:
        print(f"  ❌ Telegram indisponible : {e}")

def formater_message(annonce):
    lien = annonce.get('lien', '')
    # Nettoyage du lien pour s'assurer qu'il est valide
    if not lien.startswith("http"):
        lien = "https://" + lien
    return (
        f"🚗 <b>Nouvelle annonce !</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>{annonce.get('titre', 'N/A')}</b>\n"
        f"💶 Prix   : <b>{annonce.get('prix', 'N/A')} €</b>\n"
        f"📍 Lieu   : {annonce.get('lieu', 'N/A')}\n"
        f"🗺️ Zone   : {annonce.get('zone', 'N/A')}\n"
        f"🌐 Source : {annonce.get('source', 'N/A')}\n"
        f"🔗 Lien   : {lien}\n"
        f"🕐 {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
    )

# ============================================================
# 🛠️ AJOUT CENTRALISÉ D'UNE ANNONCE
# ============================================================

def ajouter_si_valide(liste, titre, prix_num, lieu, lien, source):
    """Ajoute l'annonce si elle passe tous les filtres (prix, modèle, zone)."""
    if prix_num <= 0 or prix_num > RECHERCHE["prix_max"]:
        return
    if not modele_correspond(titre):
        return
    dans_zone, zone_label = verifier_localisation(lieu)
    if not dans_zone:
        return
    liste.append({
        "id":     lien,
        "titre":  titre,
        "prix":   prix_num,
        "lieu":   lieu,
        "zone":   zone_label,
        "lien":   lien,
        "source": source,
    })

def extraire_prix(texte):
    chiffres = "".join(filter(str.isdigit, texte))
    return int(chiffres) if chiffres else 0

# ============================================================
# 🔎 LEBONCOIN
# ============================================================

def scraper_leboncoin():
    annonces = []
    # Headers complets imitant un vrai navigateur pour éviter le blocage
    headers = {
        "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection":      "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest":  "document",
        "Sec-Fetch-Mode":  "navigate",
        "Sec-Fetch-Site":  "none",
        "Sec-Fetch-User":  "?1",
        "Cache-Control":   "max-age=0",
        "Referer":         "https://www.leboncoin.fr/",
    }

    # On utilise une session pour conserver les cookies entre les requêtes
    session = requests.Session()
    session.headers.update(headers)

    # Première visite sur la page d'accueil pour récupérer les cookies
    try:
        session.get("https://www.leboncoin.fr/", timeout=15)
        time.sleep(3)
    except Exception:
        pass

    for m in MODELES:
        q   = f"{m['marque']} {m['modele']}".replace(" ", "%20")
        url = (f"https://www.leboncoin.fr/recherche?category=2"
               f"&text={q}&price=min-{RECHERCHE['prix_max']}")
        try:
            response = session.get(url, timeout=15)
            soup     = BeautifulSoup(response.text, "html.parser")

            # Tentative avec data-test-id classique
            items = soup.find_all("a", attrs={"data-test-id": "ad"})

            # Si rien trouvé → tentative avec structure alternative
            if not items:
                items = soup.find_all("a", href=lambda h: h and "/voitures/offre/" in h)

            for a in items[:5]:
                try:
                    titre_el = (a.find("p",    attrs={"data-test-id": "ad-title"})
                                or a.find("h2") or a.find("h3"))
                    prix_el  = (a.find("span", attrs={"data-test-id": "price"})
                                or a.find("span", class_=lambda c: c and "price" in c.lower() if c else False))
                    lieu_el  = (a.find("p",    attrs={"data-test-id": "ad-location"})
                                or a.find("p",  class_=lambda c: c and "location" in c.lower() if c else False))

                    titre = titre_el.text.strip() if titre_el else f"{m['marque']} {m['modele']}"
                    lieu  = lieu_el.text.strip()  if lieu_el  else ""
                    prix_ = prix_el.text.strip()  if prix_el  else "0"
                    lien  = "https://www.leboncoin.fr" + a.get("href", "")
                    ajouter_si_valide(annonces, titre, extraire_prix(prix_), lieu, lien, "LeBonCoin")
                except Exception:
                    continue

        except Exception as e:
            print(f"  ⚠️ LeBonCoin ({m['modele']}) : {e}")

        # Pause aléatoire entre 2 et 5 secondes pour imiter un humain
        time.sleep(2 + (hash(m['modele']) % 3))

    print(f"  🔍 LeBonCoin    → {len(annonces)} annonce(s)")
    return annonces

# ============================================================
# 🔎 AUTOSCOUT24
# ============================================================

def scraper_autoscout24():
    annonces = []
    headers  = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0",
                "Accept-Language": "fr-FR,fr;q=0.9"}
    fuel_map = {"essence": "B", "diesel": "D"}
    for m in MODELES:
        fuels = ",".join([fuel_map[x] for x in m["motorisations"] if x in fuel_map])
        q     = f"{m['marque']} {m['modele']}".replace(" ", "+")
        url   = (f"https://www.autoscout24.fr/lst?sort=standard&desc=0&ustate=N%2CU"
                 f"&size=10&page=1&atype=C&fregfrom={RECHERCHE['annee_min']}"
                 f"&priceto={RECHERCHE['prix_max']}&fuel={fuels}&q={q}")
        try:
            soup = BeautifulSoup(requests.get(url, headers=headers, timeout=15).text, "html.parser")
            for a in soup.find_all("article", class_=lambda c: c and "cldt-summary-full-item" in c)[:5]:
                try:
                    titre_el = a.find("h2")
                    prix_el  = a.find("span", class_=lambda c: c and "price" in c.lower() if c else False)
                    lieu_el  = a.find("span", class_=lambda c: c and "seller-info" in c.lower() if c else False)
                    lien_el  = a.find("a", href=True)
                    titre = titre_el.text.strip() if titre_el else "Titre inconnu"
                    lieu  = lieu_el.text.strip()  if lieu_el  else ""
                    lien  = "https://www.autoscout24.fr" + lien_el["href"] if lien_el else url
                    ajouter_si_valide(annonces, titre, extraire_prix(prix_el.text if prix_el else "0"), lieu, lien, "AutoScout24")
                except Exception:
                    continue
        except Exception as e:
            print(f"  ⚠️ AutoScout24 ({m['modele']}) : {e}")
        time.sleep(2)
    print(f"  🔍 AutoScout24  → {len(annonces)} annonce(s)")
    return annonces

# ============================================================
# 🔎 LA CENTRALE
# ============================================================

def scraper_la_centrale():
    annonces = []
    headers = {
        "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection":      "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest":  "document",
        "Sec-Fetch-Mode":  "navigate",
        "Sec-Fetch-Site":  "none",
        "Referer":         "https://www.lacentrale.fr/",
    }

    session = requests.Session()
    session.headers.update(headers)

    # Visite de la page d'accueil pour récupérer les cookies
    try:
        session.get("https://www.lacentrale.fr/", timeout=15)
        time.sleep(3)
    except Exception:
        pass

    fuel_map = {"essence": "1", "diesel": "2"}
    for m in MODELES:
        fuels = "%7C".join([fuel_map[x] for x in m["motorisations"] if x in fuel_map])
        url   = (f"https://www.lacentrale.fr/listing?"
                 f"makesModelsCommercialNames={m['marque']}%3A{m['modele']}"
                 f"&priceMax={RECHERCHE['prix_max']}&yearMin={RECHERCHE['annee_min']}"
                 f"&energies={fuels}")
        try:
            response = session.get(url, timeout=15)
            soup     = BeautifulSoup(response.text, "html.parser")

            # Tentative structure principale
            items = soup.find_all("div", class_=lambda c: c and "adCard" in c if c else False)

            # Structure alternative si rien trouvé
            if not items:
                items = soup.find_all("article")
            if not items:
                items = soup.find_all("div", class_=lambda c: c and ("vehicle" in c.lower() or "annonce" in c.lower()) if c else False)

            for a in items[:5]:
                try:
                    titre_el = a.find(["h2", "h3"])
                    prix_el  = a.find(class_=lambda c: c and "price" in c.lower() if c else False)
                    lieu_el  = a.find(class_=lambda c: c and ("location" in c.lower() or "city" in c.lower()) if c else False)
                    lien_el  = a.find("a", href=True)

                    titre = titre_el.text.strip() if titre_el else f"{m['marque']} {m['modele']}"
                    lieu  = lieu_el.text.strip()  if lieu_el  else ""
                    lien  = lien_el["href"]        if lien_el  else url
                    if not lien.startswith("http"):
                        lien = "https://www.lacentrale.fr" + lien

                    ajouter_si_valide(annonces, titre, extraire_prix(prix_el.text if prix_el else "0"), lieu, lien, "La Centrale")
                except Exception:
                    continue

        except Exception as e:
            print(f"  ⚠️ La Centrale ({m['modele']}) : {e}")

        time.sleep(2 + (hash(m['modele']) % 3))

    print(f"  🔍 La Centrale  → {len(annonces)} annonce(s)")
    return annonces

# ============================================================
# 🔎 PARUVENDU  ★ Nouveau
# ============================================================

def scraper_paruvendu():
    annonces = []
    headers  = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
    for m in MODELES:
        q   = f"{m['marque']} {m['modele']}".replace(" ", "+")
        url = (f"https://www.paruvendu.fr/auto-moto-bateau/voiture/annonce-voiture-occasion/"
               f"?q={q}&prixmax={RECHERCHE['prix_max']}&anne={RECHERCHE['annee_min']}")
        try:
            soup = BeautifulSoup(requests.get(url, headers=headers, timeout=15).text, "html.parser")
            for a in soup.find_all("div", class_=lambda c: c and "annonce" in c if c else False)[:5]:
                try:
                    titre_el = a.find(["h2", "h3"], class_=lambda c: c and "titre" in c.lower() if c else False)
                    prix_el  = a.find(class_=lambda c: c and "prix" in c.lower() if c else False)
                    lieu_el  = a.find(class_=lambda c: c and "ville" in c.lower() if c else False)
                    lien_el  = a.find("a", href=True)
                    titre = titre_el.text.strip() if titre_el else f"{m['marque']} {m['modele']}"
                    lieu  = lieu_el.text.strip()  if lieu_el  else ""
                    lien  = lien_el["href"] if lien_el else url
                    if not lien.startswith("http"):
                        lien = "https://www.paruvendu.fr" + lien
                    ajouter_si_valide(annonces, titre, extraire_prix(prix_el.text if prix_el else "0"), lieu, lien, "ParuVendu")
                except Exception:
                    continue
        except Exception as e:
            print(f"  ⚠️ ParuVendu ({m['modele']}) : {e}")
        time.sleep(2)
    print(f"  🔍 ParuVendu    → {len(annonces)} annonce(s)")
    return annonces

# ============================================================
# 🔎 OCCASION.FR  ★ Nouveau
# ============================================================

def scraper_occasion_fr():
    annonces = []
    headers  = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
    for m in MODELES:
        for carbu in m["motorisations"]:
            url = (f"https://www.occasion.fr/voitures/"
                   f"{m['marque'].lower()}/{m['modele'].lower()}/"
                   f"?prixmax={RECHERCHE['prix_max']}"
                   f"&anneemin={RECHERCHE['annee_min']}"
                   f"&carburant={carbu}")
            try:
                soup = BeautifulSoup(requests.get(url, headers=headers, timeout=15).text, "html.parser")
                for a in soup.find_all("div", class_=lambda c: c and "vehicule" in c.lower() if c else False)[:5]:
                    try:
                        titre_el = a.find(["h2", "h3"])
                        prix_el  = a.find(class_=lambda c: c and "prix" in c.lower() if c else False)
                        lieu_el  = a.find(class_=lambda c: c and ("lieu" in c.lower() or "ville" in c.lower()) if c else False)
                        lien_el  = a.find("a", href=True)
                        titre = titre_el.text.strip() if titre_el else f"{m['marque']} {m['modele']}"
                        lieu  = lieu_el.text.strip()  if lieu_el  else ""
                        lien  = lien_el["href"] if lien_el else url
                        if not lien.startswith("http"):
                            lien = "https://www.occasion.fr" + lien
                        ajouter_si_valide(annonces, titre, extraire_prix(prix_el.text if prix_el else "0"), lieu, lien, "Occasion.fr")
                    except Exception:
                        continue
            except Exception as e:
                print(f"  ⚠️ Occasion.fr ({m['modele']}/{carbu}) : {e}")
            time.sleep(2)
    print(f"  🔍 Occasion.fr  → {len(annonces)} annonce(s)")
    return annonces

# ============================================================
# 🔄 VÉRIFICATION PRINCIPALE
# ============================================================

def verifier_nouvelles_annonces():
    print(f"\n{'='*55}")
    print(f"🕐 Vérification le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}")
    print(f"{'='*55}")

    annonces_vues   = charger_annonces_vues()
    toutes_annonces = []

    toutes_annonces += scraper_leboncoin()
    toutes_annonces += scraper_autoscout24()
    toutes_annonces += scraper_la_centrale()
    toutes_annonces += scraper_paruvendu()
    toutes_annonces += scraper_occasion_fr()

    nouvelles = 0
    for annonce in toutes_annonces:
        if annonce["id"] not in annonces_vues:
            envoyer_alerte_telegram(formater_message(annonce))
            sauvegarder_annonce_vue(annonce["id"])
            nouvelles += 1
            time.sleep(1)

    if nouvelles == 0:
        print("😴 Aucune nouvelle annonce dans les zones définies.")
    else:
        print(f"🎉 {nouvelles} nouvelle(s) alerte(s) envoyée(s) !")
    print(f"⏭️  Prochaine vérification dans {FREQUENCE_MINUTES} min.\n")

# ============================================================
# 🚀 LANCEMENT
# ============================================================

if __name__ == "__main__":
    print("🚗 Script d'alertes véhicules démarré !")
    print(f"   Budget max   : {RECHERCHE['prix_max']} €")
    print(f"   Année min    : {RECHERCHE['annee_min']}")
    print(f"   Modèles      : {len(MODELES)} modèles surveillés")
    print(f"   Zones        :")
    for z in ZONES:
        print(f"     📍 {z['nom']} (rayon {z['rayon_km']} km)")
    print(f"   Sites        : LeBonCoin · AutoScout24 · La Centrale · ParuVendu · Occasion.fr")
    print(f"   Fréquence    : toutes les {FREQUENCE_MINUTES} min\n")

    verifier_nouvelles_annonces()

    schedule.every(FREQUENCE_MINUTES).minutes.do(verifier_nouvelles_annonces)
    while True:
        schedule.run_pending()
        time.sleep(60)


# ============================================================
# 📖 README - CONFIGURER LE BOT TELEGRAM
# ============================================================
"""
ÉTAPE 1 — Créer ton bot Telegram
─────────────────────────────────
1. Ouvre Telegram → cherche @BotFather → tape /newbot
2. Suis les instructions → copie le TOKEN dans TELEGRAM_BOT_TOKEN

ÉTAPE 2 — Obtenir ton Chat ID
──────────────────────────────
1. Cherche @userinfobot dans Telegram → envoie n'importe quel message
2. Copie l'ID reçu dans TELEGRAM_CHAT_ID

ÉTAPE 3 — Installer les dépendances
─────────────────────────────────────
    pip install requests beautifulsoup4 schedule

ÉTAPE 4 — Lancer le script
────────────────────────────
    python alerte_vehicule.py

PERSONNALISATION RAPIDE
────────────────────────
- Budget          → RECHERCHE["prix_max"]
- Année minimum   → RECHERCHE["annee_min"]
- Ajouter une ville → ajouter un dict dans ZONES
- Ajouter un modèle → ajouter une ligne dans MODELES
- Désactiver un modèle → mettre un # devant la ligne

⚠️ NOTE
───────
Usage personnel et raisonnable uniquement (30 min minimum entre deux cycles).
Consulte les CGU de chaque site pour t'assurer de la conformité.
"""
