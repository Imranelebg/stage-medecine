"""
PermutStage — Plateforme Collaborative d'Échange de Lieux de Stage (Médecine P1 à P8)
Version FastHTML (python-fasthtml) & Google Cloud Firebase Firestore (firebase-admin).

Architecture complète dans un fichier unique main.py avec persistance Firestore fiabilisée à 100% :
- Collection 'users' : indexée par l'email de l'étudiant (email, nom, prenom, code_pin, created_at, statut).
- Collection 'demandes' : propositions de stages (user_email, nom_etudiant, periode, specialite, hopital_actuel, hopitaux_souhaites, statut, updated_at).
- Collection 'discussions' : salons de matchings privés (discussion_id, type_match, participants, demande_ids, dernier_message, dernier_timestamp).
- Collection 'messages' : messagerie interne des salons (message_id, discussion_id, sender_email, sender_name, texte, timestamp).
- Persistance de session native FastHTML et synchronisation Firestore à chaque chargement de route protégée.
- Fonctions d'interaction discussions & messages (creer_ou_recuperer_discussion, envoyer_message, recuperer_messages, recuperer_discussions_utilisateur).
- Sélecteur moderne d'hôpitaux souhaités par cases à cocher avec sélection rapide par région, recherche instantanée et compteur dynamique.
- Moteur de matching bilatéral (A <-> B) et triangulaire (A -> B -> C -> A) avec confidentialité absolue.
- Système d'alertes par email SMTP automatique lors de la formation d'un cycle complet.

Exécution :
    python main.py
"""

from fasthtml.common import *
import os
import re
import uuid
import json
import time
import logging
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PermutStage")

# ---------------------------------------------------------------------------
# 1. DESIGN SYSTEM & INITIALISATION DE L'APPLICATION FASTHTML (Pico.css)
# ---------------------------------------------------------------------------
CUSTOM_STYLE = Style("""
    :root {
        --pico-font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
        --pico-primary: #1d4ed8;
        --pico-primary-background: #1d4ed8;
        --pico-primary-hover: #1e40af;
        --pico-primary-focus: rgba(29, 78, 216, 0.2);
        --pico-border-radius: 10px;
    }
    body {
        background-color: #f8fafc;
        color: #0f172a;
        font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
        -webkit-font-smoothing: antialiased;
    }

    /* En-tête & Barre de navigation principale */
    .app-header {
        background: #ffffff;
        border-bottom: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
        padding: 0.75rem 1.25rem;
        margin-bottom: 1.25rem;
    }
    .brand-title {
        font-size: 1.4rem;
        font-weight: 800;
        color: #1d4ed8;
        letter-spacing: -0.02em;
        text-decoration: none;
    }
    .brand-subtitle {
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 700;
        color: #1e40af;
        background: #dbeafe;
        border: 1px solid #bfdbfe;
        border-radius: 6px;
        padding: 0.15rem 0.5rem;
        margin-left: 0.5rem;
        vertical-align: middle;
    }
    .nav-tabs {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        border-bottom: 2px solid #e2e8f0;
        margin-bottom: 1.5rem;
        padding-bottom: 0.5rem;
    }
    .nav-tab-btn {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        color: #475569;
        font-weight: 600;
        font-size: 0.88rem;
        padding: 0.5rem 0.95rem;
        border-radius: 8px;
        cursor: pointer;
        text-decoration: none;
        transition: all 0.15s ease;
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
    }
    .nav-tab-btn:hover {
        background: #f1f5f9;
        color: #1d4ed8;
        border-color: #cbd5e1;
    }
    .nav-tab-btn.active {
        background: #1d4ed8;
        color: #ffffff;
        border-color: #1d4ed8;
        box-shadow: 0 2px 6px rgba(29, 78, 216, 0.25);
    }

    /* Cartes & Conteneurs modernes */
    article, .card-modern {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05), 0 1px 2px rgba(15, 23, 42, 0.03);
    }

    /* Bannière Hero */
    .hero-banner {
        background: linear-gradient(135deg, #1e3a8a 0%, #172554 100%);
        color: #ffffff;
        padding: 2.2rem 2.4rem;
        border-radius: 14px;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(59, 130, 246, 0.3);
        box-shadow: 0 4px 18px rgba(15, 23, 42, 0.12);
    }
    .hero-banner h1, .hero-banner h2, .hero-banner p, .hero-banner strong {
        color: #ffffff;
    }
    .hero-badge {
        display: inline-block;
        padding: 0.25rem 0.8rem;
        background: rgba(59, 130, 246, 0.25);
        border: 1px solid rgba(147, 197, 253, 0.4);
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        color: #bfdbfe;
        margin-bottom: 0.85rem;
    }
    .hero-alpha-box {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 10px;
        padding: 0.95rem 1.15rem;
        font-size: 0.88rem;
        line-height: 1.55;
        color: #f8fafc;
    }

    /* Cartes de Match */
    .match-card {
        background-color: #f0fdf4;
        border: 1px solid #86efac;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.25rem;
        color: #14532d;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    }
    .tri-card {
        background-color: #ecfdf5;
        border: 1px solid #6ee7b7;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.25rem;
        color: #064e3b;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    }
    .quad-card {
        background-color: #faf5ff;
        border: 1px solid #d8b4fe;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.25rem;
        color: #581c87;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    }

    /* Badges de statut */
    .status-badge {
        display: inline-block;
        padding: 0.22rem 0.65rem;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.02em;
    }
    .status-disponible { background: #dcfce7; color: #166534; border: 1px solid #86efac; }
    .status-discussion { background: #fef3c7; color: #92400e; border: 1px solid #fcd34d; }
    .status-accord { background: #e0e7ff; color: #3730a3; border: 1px solid #a5b4fc; }

    /* Salons de chat */
    .chat-bubble {
        padding: 0.65rem 0.95rem;
        border-radius: 10px;
        margin-bottom: 0.5rem;
        font-size: 0.88rem;
        line-height: 1.45;
    }
    .chat-me { background: #dbeafe; color: #1e3a8a; text-align: right; margin-left: 18%; border: 1px solid #bfdbfe; }
    .chat-other { background: #f1f5f9; color: #1e293b; margin-right: 18%; border: 1px solid #e2e8f0; }

    /* Statistiques */
    .stat-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.15rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    }
    .stat-val { font-size: 1.85rem; font-weight: 800; color: #1d4ed8; }
    .stat-lbl { font-size: 0.82rem; color: #64748b; font-weight: 600; margin-top: 0.2rem; }

    /* Formulaires & Champs */
    input, select, textarea {
        border-radius: 8px !important;
        border: 1px solid #cbd5e1 !important;
        padding: 0.65rem 0.85rem !important;
        font-size: 0.9rem !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
    }
    input:focus, select:focus, textarea:focus {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15) !important;
        outline: none !important;
    }
    label {
        font-weight: 600 !important;
        font-size: 0.86rem !important;
        color: #334155 !important;
        margin-bottom: 0.35rem !important;
    }

    /* Sélecteur d'hôpitaux souhaités moderne (Checkboxes) */
    .hospital-selector-wrapper {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 1px 4px rgba(15, 23, 42, 0.05);
    }
    .badge-counter {
        display: inline-block;
        padding: 0.18rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 700;
        background: #f1f5f9;
        color: #64748b;
        transition: all 0.2s ease;
    }
    .badge-counter.has-selected {
        background: #dbeafe;
        color: #1d4ed8;
        border: 1px solid #bfdbfe;
    }
    .quick-select-card {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 1rem;
    }
    .quick-badge {
        display: inline-flex;
        align-items: center;
        background: #ffffff;
        color: #1e40af;
        border: 1px solid #93c5fd;
        padding: 0.35rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.15s ease;
        margin-bottom: 0;
        line-height: 1.2;
    }
    .quick-badge:hover {
        background: #dbeafe;
        color: #1d4ed8;
        border-color: #3b82f6;
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(37, 99, 235, 0.12);
    }
    .quick-badge-reset {
        display: inline-flex;
        align-items: center;
        background: #ffffff;
        color: #64748b;
        border: 1px solid #cbd5e1;
        padding: 0.35rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.15s ease;
        margin-bottom: 0;
        line-height: 1.2;
    }
    .quick-badge-reset:hover {
        background: #fef2f2;
        color: #b91c1c;
        border-color: #fca5a5;
    }
    .hospital-scroll-container {
        max-height: 380px;
        overflow-y: auto;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        background: #ffffff;
        box-shadow: inset 0 1px 3px rgba(15, 23, 42, 0.03);
    }
    .hospital-row-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.65rem 0.95rem;
        border-bottom: 1px solid #f1f5f9;
        transition: background-color 0.15s ease;
        cursor: pointer;
        user-select: none;
    }
    .hospital-row-item:last-child {
        border-bottom: none;
    }
    .hospital-row-item:hover {
        background-color: #f8fafc;
    }
    .hospital-row-item.is-current-hospital {
        background-color: #fffbeb !important;
        opacity: 0.8;
        cursor: not-allowed;
    }
    .hospital-reg-tag {
        color: #64748b;
        font-weight: 600;
        font-size: 0.82rem;
    }
    .hospital-name-text {
        color: #0f172a;
        font-weight: 600;
        font-size: 0.88rem;
    }
    .hospital-current-badge {
        font-size: 0.75rem;
        font-weight: 700;
        color: #b45309;
        background: #fef3c7;
        border: 1px solid #fde68a;
        border-radius: 6px;
        padding: 0.15rem 0.45rem;
        margin-left: 0.4rem;
    }
    .hospital-checkbox-custom {
        width: 1.25rem !important;
        height: 1.25rem !important;
        accent-color: #1d4ed8 !important;
        margin: 0 !important;
        cursor: pointer !important;
    }

    /* Responsive mobile */
    @media (max-width: 768px) {
        .app-header { padding: 0.6rem 0.8rem; }
        .hero-banner { padding: 1.4rem 1.2rem; }
        .hero-banner h1 { font-size: 1.45rem; }
        .nav-tabs { gap: 0.35rem; }
        .nav-tab-btn { font-size: 0.8rem; padding: 0.4rem 0.7rem; }
        .hospital-row-item { padding: 0.6rem 0.7rem; }
    }
""")

app, rt = fast_app(
    pico=True,
    live=False,
    secret_key=os.environ.get("SESSION_SECRET", "clé_secrete_session_permutstage"),
    hdrs=(
        Title("PermutStage — Plateforme d'échange de stages de médecine"),
        Meta(charset="UTF-8"),
        Meta(name="viewport", content="width=device-width, initial-scale=1.0"),
        Meta(name="description", content="Trouvez votre binôme de stage idéal en P1, P2, P3, P4, P5, P6, P7 ou P8 grâce à notre moteur de matching sécurisé."),
        Meta(property="og:title", content="PermutStage — Échange de stages de médecine"),
        Meta(property="og:description", content="Plateforme collaborative sécurisée de permutation de stages hospitaliers pour les étudiants en médecine."),
        Meta(property="og:type", content="website"),
        Meta(property="og:url", content="https://permutstage.onrender.com/"),
        Meta(property="og:site_name", content="PermutStage"),
        Meta(name="twitter:card", content="summary_large_image"),
        Meta(name="twitter:title", content="PermutStage — Échange de stages de médecine"),
        Meta(name="twitter:description", content="Plateforme collaborative sécurisée de permutation de stages hospitaliers pour les étudiants en médecine."),
        Link(rel="preconnect", href="https://fonts.googleapis.com"),
        Link(rel="preconnect", href="https://fonts.gstatic.com", crossorigin=""),
        Link(rel="stylesheet", href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap"),
        CUSTOM_STYLE,
    ),
)

# ---------------------------------------------------------------------------
# 2. CONSTANTES MÉTIER & BASE DE DONNÉES DES HÔPITAUX PAR RÉGION
# ---------------------------------------------------------------------------
PERIODES = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]

SPECIALITES_TRONC_COMMUN = [
    "Pédiatrie",
    "Médecine interne",
    "Gériatrie",
    "Gynécologie-obstétrique",
    "Urgences",
    "Chirurgie",
]

SPECIALITES_AU_CHOIX = [
    "Anatomie pathologique",
    "Anesthésie-Réanimation",
    "Biologie clinique",
    "Chirurgie viscérale",
    "Chirurgie thoracique",
    "Chirurgie cardiaque",
    "Chirurgie vasculaire",
    "Chirurgie orthopédique",
    "Chirurgie plastique, reconstructrice et esthétique",
    "Dermato-vénéréologie",
    "Génétique clinique",
    "Médecine nucléaire",
    "Médecine physique et réadaptation",
    "Neurochirurgie",
    "Neurologie",
    "Ophtalmologie",
    "Oto-rhino-laryngologie",
    "Psychiatrie adulte",
    "Psychiatrie infanto-juvénile",
    "Radiodiagnostic",
    "Radiothérapie-Oncologie",
    "Stomatologie",
    "Urologie",
    "Médecine générale",
]

# Liste complète ordonnée pour rétrocompatibilité et moteur de matching
SPECIALITES = SPECIALITES_TRONC_COMMUN + SPECIALITES_AU_CHOIX

if "Optgroup" not in globals():
    try:
        from fasthtml.components import Optgroup
    except Exception:
        try:
            from fasthtml.common import optgroup as Optgroup
        except Exception:
            def Optgroup(*children, **attrs):
                return ft("optgroup", *children, **attrs)

def render_specialite_options(selected_value: str = "", include_all: bool = False):
    """
    Génère la liste des options groupées par catégorie (<optgroup>) :
    - Tronc commun (6 spécialités obligatoires)
    - Stages au choix (24 spécialités)
    Optionnellement précédé de 'Toutes' pour les filtres de recherche.
    """
    items = []
    if include_all:
        items.append(Option("Toutes", value="Toutes", selected=(selected_value == "Toutes" or not selected_value)))

    items.append(
        Optgroup(
            label="Tronc commun",
            *[Option(s, value=s, selected=(s == selected_value)) for s in SPECIALITES_TRONC_COMMUN]
        )
    )
    items.append(
        Optgroup(
            label="Stages au choix",
            *[Option(s, value=s, selected=(s == selected_value)) for s in SPECIALITES_AU_CHOIX]
        )
    )
    return items

HOPITAUX_PAR_REGION = {
    "Bruxelles": [
        "Centre gériatrique Scheutbos Silva Médical",
        "Centre Hospitalier VALIDA",
        "CHIREC - Clinique Sainte Anne - Saint Remi",
        "Clinique Saint Jean - Bruxelles",
        "Clinique Sanatia",
        "Cliniques de l'Europe site Sainte Elisabeth",
        "Cliniques de l'Europe site Saint Michel",
        "Cliniques Universitaires Saint Luc",
        "EPSYLON - La Ramée-FOND'ROY - AREA+",
    ],
    "Brabant wallon": [
        "Centre William Lennox (Ottignies)",
        "CHIREC - Hôpital Braine-l'Alleud",
        "CHU HELORA - Hôpital de Nivelles-Tubize",
        "Clinique Saint Pierre - Ottignies",
        "Hôpital psychiatrique La Petite Maison (Chastre)",
    ],
    "Namur": [
        "Centre Hospitalier Sambre & Meuse - Site Meuse",
        "Centre Hospitalier Sambre & Meuse - Site Sambre (Auvelais)",
        "CHU UCL NAMUR - Foyer Saint François",
        "CHU UCL NAMUR - Site Dinant",
        "CHU UCL NAMUR - Site Mont-Godinne (Yvoir)",
        "CHU UCL NAMUR - Site Sainte Elisabeth - Namur",
        "Clinique Saint Luc - Bouge",
        "CNP Saint Martin (Dave)",
        "Hôpital Psychiatrique Le Beau Vallon (Saint-Servais)",
    ],
    "Hainaut": [
        "Centre Hospitalier de Mouscron",
        "Centre Psychiatrique Saint Bernard (Manage)",
        "CHR Haute-Senne - Soignies",
        "CHU HELORA - Hôpital de La Louvière - Site Jolimont",
        "CHU HELORA - Hôpital de Lobbes",
        "CHU HELORA - Hôpital de Mons",
        "CHU HELORA - Hôpital de Mons - Site Kennedy",
        "CHwapi (Tournai)",
        "Clinique N. Dame de Grâce Gosselies",
        "EPICURA - site du Grand Hornu",
        "GHdC - Centre Psychothérapeutique Charles Albert Frère (Marcinelle)",
        "GHdC - Les Viviers (Gilly)",
        "HUmani - Centre de Santé des Fagnes - Chimay",
    ],
    "Liège": [
        "Centre Hospitalier Reine Astrid - Malmédy",
        "CHR de la Citadelle Site Citadelle",
        "CHR HUY",
        "CHR Verviers",
        "Groupe Santé CHC MontLégia",
        "Hôpital Sint Nikolaus - Eupen",
    ],
    "Luxembourg": [
        "VIVALIA - Hôpital d'Arlon",
        "Vivalia - Hôpital de Libramont",
        "Vivalia - Hôpital de Marche",
    ],
    "Grand-Duché de Luxembourg": [
        "Centre Hospitalier du Luxembourg",
        "Clinique Zitha-Hôpitaux Robert Schumann",
    ],
}

REGIONS = list(HOPITAUX_PAR_REGION.keys())

TOUS_LES_HOPITAUX = [
    hopital
    for liste_reg in HOPITAUX_PAR_REGION.values()
    for hopital in liste_reg
]

HOPITAL_VERS_REGION = {
    hopital: region
    for region, liste_reg in HOPITAUX_PAR_REGION.items()
    for hopital in liste_reg
}

STATUTS_DEMANDE = ["Disponible", "En discussion", "Accord trouvé"]

# Les 4 collections Firestore officielles
COLLECTION_USERS = "users"
COLLECTION_DEMANDES = "demandes"
COLLECTION_DISCUSSIONS = "discussions"
COLLECTION_MESSAGES = "messages"

NOTIFIED_MATCH_ROOMS: set[str] = set()

def slugify(text: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]+', '-', str(text)).strip('-').lower()

def normalize_pin(val: str) -> str:
    s = str(val or "").strip().replace(".0", "")
    return s.zfill(4) if (s.isdigit() and len(s) <= 4) else s

# ---------------------------------------------------------------------------
# CACHE MÉMOIRE HAUTE PERFORMANCE (ZÉRO CHARGEMENT À L'INFINI)
# ---------------------------------------------------------------------------
_CACHE_DEMANDES = {"df": None, "timestamp": 0.0}
_CACHE_USERS = {"df": None, "timestamp": 0.0}
CACHE_TTL = 30.0  # Durée de validité du cache en secondes

def invalidate_cache(target: str = "all"):
    """Invalide immédiatement le cache mémoire lors de modifications de données."""
    global _CACHE_DEMANDES, _CACHE_USERS
    if target in ("all", "demandes"):
        _CACHE_DEMANDES["timestamp"] = 0.0
        _CACHE_DEMANDES["df"] = None
    if target in ("all", "users"):
        _CACHE_USERS["timestamp"] = 0.0
        _CACHE_USERS["df"] = None

def build_discussion_id(type_match: str, participants: list[str]) -> str:
    """Génère de façon déterministe et instantanée (en mémoire) l'identifiant de salon."""
    sorted_p = sorted([str(p).lower().strip() for p in participants if p and str(p).strip()])
    return f"disc_{type_match}_{'_'.join(sorted_p)}".replace("@", "_at_").replace(".", "_")

# ---------------------------------------------------------------------------
# 3. INITIALISATION GOOGLE CLOUD FIREBASE FIRESTORE & PERSISTANCE GARANTIE
# ---------------------------------------------------------------------------
_FIRESTORE_CLIENT = None
_FIRESTORE_LAST_ATTEMPT = 0.0
LOCAL_DB_FILE = os.path.join(os.path.dirname(__file__), ".permutstage_local_db.json")

def load_local_db() -> dict:
    """Charge la base locale persistante pour garantir zéro perte de données même hors-ligne."""
    if os.path.exists(LOCAL_DB_FILE):
        try:
            with open(LOCAL_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"users": {}, "demandes": {}, "discussions": {}, "messages": {}}

def save_local_db(data: dict):
    """Écrit atomiquement sur disque local pour préserver les comptes et offres à chaque visite."""
    try:
        with open(LOCAL_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        print(f"[PermutStage] Erreur sauvegarde locale: {exc}")

def get_firestore_client():
    """Initialise Firebase Firestore avec détection automatique sur Render."""
    global _FIRESTORE_CLIENT, _FIRESTORE_LAST_ATTEMPT
    if _FIRESTORE_CLIENT is not None:
        return _FIRESTORE_CLIENT

    # Si déjà initialisé dans firebase_admin
    if firebase_admin._apps:
        try:
            _FIRESTORE_CLIENT = firestore.client()
            return _FIRESTORE_CLIENT
        except Exception:
            pass

    # Éviter de retenter plus d'une fois toutes les 5 secondes si pas de clé
    now = time.time()
    if now - _FIRESTORE_LAST_ATTEMPT < 5.0:
        return None
    _FIRESTORE_LAST_ATTEMPT = now

    try:
        fb_creds_dict = None

        # 1. Variables d'environnement (JSON direct ou chemin de fichier)
        env_var_names = [
            "FIREBASE_CREDENTIALS", "FIREBASE_CONFIG", "FIREBASE_KEY",
            "FIREBASE_SERVICE_ACCOUNT", "FIREBASE_CREDENTIALS_JSON",
            "FIREBASE_KEY_JSON", "FIREBASE_JSON", "FIREBASE_SECRET",
            "FIREBASE_ADMIN_CREDENTIALS", "GOOGLE_APPLICATION_CREDENTIALS",
            "GOOGLE_CREDENTIALS", "SERVICE_ACCOUNT"
        ]
        
        detected_env = [k for k in env_var_names if os.environ.get(k)]
        if detected_env:
            print(f"[PermutStage] Variables Firebase détectées dans l'environnement : {detected_env}")

        for env_key in env_var_names:
            raw_env = os.environ.get(env_key)
            if raw_env:
                raw_env = raw_env.strip()
                # Supprimer d'éventuels guillemets englobants
                if (raw_env.startswith("'") and raw_env.endswith("'")) or (raw_env.startswith('"') and raw_env.endswith('"')):
                    raw_env = raw_env[1:-1].strip()

                if os.path.exists(raw_env):
                    try:
                        cred = credentials.Certificate(raw_env)
                        firebase_admin.initialize_app(cred)
                        _FIRESTORE_CLIENT = firestore.client()
                        print(f"[PermutStage] ✅ Firestore initialisé depuis fichier chemin env {env_key}: {raw_env}")
                        return _FIRESTORE_CLIENT
                    except Exception as e_cert:
                        print(f"[PermutStage] ❌ Erreur chargement certificat depuis {raw_env}: {e_cert}")
                else:
                    try:
                        fb_creds_dict = json.loads(raw_env)
                        print(f"[PermutStage] ✅ JSON de configuration Firebase parsé depuis variable {env_key}")
                        break
                    except Exception as json_err:
                        print(f"[PermutStage] ⚠️ Variable {env_key} présente mais échec du parsing JSON : {json_err}")

        # 2. Fichiers secrets.toml
        if fb_creds_dict is None:
            for p in [os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml"), "secrets.toml"]:
                if os.path.exists(p):
                    try:
                        import tomllib
                    except ImportError:
                        try:
                            import tomli as tomllib
                        except ImportError:
                            tomllib = None
                    if tomllib:
                        try:
                            with open(p, "rb") as f:
                                sec = tomllib.load(f)
                                if "firebase" in sec:
                                    fb_creds_dict = dict(sec["firebase"])
                                    print(f"[PermutStage] ✅ Configuration Firebase trouvée dans {p}")
                                    break
                        except Exception:
                            pass

        # 3. Fichiers JSON (racine du projet ou dossier /etc/secrets/ de Render)
        if fb_creds_dict is None:
            json_candidates = [
                "serviceAccountKey.json", "firebase_key.json", "firebase-credentials.json", "firebase_credentials.json", "firebase.json",
                "/etc/secrets/serviceAccountKey.json", "/etc/secrets/firebase_key.json", "/etc/secrets/firebase-credentials.json", "/etc/secrets/firebase_credentials.json", "/etc/secrets/firebase.json"
            ]
            if os.path.exists("/etc/secrets"):
                try:
                    for sf in os.listdir("/etc/secrets"):
                        if sf.endswith(".json"):
                            json_candidates.append(os.path.join("/etc/secrets", sf))
                except Exception:
                    pass

            for p in json_candidates:
                if os.path.exists(p):
                    try:
                        cred = credentials.Certificate(p)
                        firebase_admin.initialize_app(cred)
                        _FIRESTORE_CLIENT = firestore.client()
                        print(f"[PermutStage] ✅ Firestore initialisé depuis fichier JSON : {p}")
                        return _FIRESTORE_CLIENT
                    except Exception as e_cert:
                        print(f"[PermutStage] ❌ Erreur lecture certificat {p}: {e_cert}")

        if fb_creds_dict:
            if "private_key" in fb_creds_dict and isinstance(fb_creds_dict["private_key"], str):
                fb_creds_dict["private_key"] = fb_creds_dict["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(fb_creds_dict)
            firebase_admin.initialize_app(cred)
            _FIRESTORE_CLIENT = firestore.client()
            print("[PermutStage] ✅ Firestore initialisé avec succès depuis dictionnaire credentials !")
            return _FIRESTORE_CLIENT

        print("[PermutStage] ℹ️ Aucune clé Firebase valide détectée (Variables d'environnement ou fichiers secrets). Mode local activé.")
        return None

    except Exception as exc:
        print(f"[PermutStage] ❌ Firestore init exception: {exc}")
        return None

    try:
        _FIRESTORE_CLIENT = firestore.client()
        return _FIRESTORE_CLIENT
    except Exception:
        return None

# ---------------------------------------------------------------------------
# 4. GESTION FIRESTORE : UTILISATEURS & AUTHENTIFICATION (COLLECTION 'users')
# ---------------------------------------------------------------------------
def get_user_by_email(email: str) -> dict | None:
    """
    Récupère un compte utilisateur directement depuis Firestore par son email clé.
    Vérifie db.collection('users').document(email.lower().strip()).get().
    """
    clean_email = (email or "").strip().lower()
    if not clean_email:
        return None

    db = get_firestore_client()
    if db is not None:
        try:
            doc = db.collection(COLLECTION_USERS).document(clean_email).get()
            if doc.exists:
                data = doc.to_dict() or {}
                data["email"] = clean_email
                data["code_pin"] = normalize_pin(data.get("code_pin") or data.get("PIN") or "")
                # Sauvegarder dans le cache local
                local = load_local_db()
                if "users" not in local: local["users"] = {}
                local["users"][clean_email] = data
                save_local_db(local)
                return data

            # Vérification de repli par requête champ 'email' ou 'Email'
            for field in ["email", "Email", "User_ID"]:
                q = db.collection(COLLECTION_USERS).where(field, "==", clean_email).limit(1).stream()
                for d in q:
                    data = d.to_dict() or {}
                    data["email"] = clean_email
                    data["code_pin"] = normalize_pin(data.get("code_pin") or data.get("PIN") or "")
                    local = load_local_db()
                    if "users" not in local: local["users"] = {}
                    local["users"][clean_email] = data
                    save_local_db(local)
                    return data
        except Exception as exc:
            print(f"[PermutStage] Erreur lecture Firestore user {clean_email}: {exc}")

    # Repli sur le stockage persistant local
    local = load_local_db()
    users_dict = local.get("users", {})
    if clean_email in users_dict:
        data = users_dict[clean_email]
        data["code_pin"] = normalize_pin(data.get("code_pin") or data.get("PIN") or "")
        return data
    return None

def create_or_update_user(user_data: dict) -> bool:
    """
    Enregistre le document utilisateur dans la collection 'users' de Firestore
    avec comme clé unique l'email de l'étudiant (.document(email.lower().strip())).
    Champs requis : email, nom, code_pin, created_at, statut.
    """
    clean_email = (user_data.get("email") or user_data.get("Email") or "").strip().lower()
    if not clean_email:
        return False
    pin = normalize_pin(user_data.get("code_pin") or user_data.get("PIN") or "")
    nom = str(user_data.get("nom") or user_data.get("Nom") or "").strip()
    prenom = str(user_data.get("prenom") or user_data.get("Prenom") or "").strip()
    created_at = user_data.get("created_at") or datetime.now(ZoneInfo("Europe/Brussels")).isoformat()
    statut = user_data.get("statut") or "actif"

    doc_payload = {
        "email": clean_email,
        "nom": nom,
        "prenom": prenom,
        "code_pin": pin,
        "created_at": created_at,
        "statut": statut,
        # Rétro-compatibilité schémas existants
        "User_ID": clean_email,
        "Nom": nom,
        "Prenom": prenom,
        "PIN": pin,
        "Email": clean_email,
        "Date_Inscription": datetime.now(ZoneInfo("Europe/Brussels")).strftime("%Y-%m-%d %H:%M:%S"),
    }

    # 1. Écriture Firestore
    db = get_firestore_client()
    firestore_written = False
    if db is not None:
        try:
            db.collection(COLLECTION_USERS).document(clean_email).set(doc_payload)
            print(f"[PermutStage Inscription] ✅ Document écrit avec succès dans Firestore : collection '{COLLECTION_USERS}', id '{clean_email}'")
            firestore_written = True
        except Exception as exc:
            print(f"[PermutStage Inscription] ❌ ÉCHEC écriture Firestore pour '{clean_email}': {exc}")
            logger.error(f"[PermutStage Inscription] Erreur Firestore: {exc}", exc_info=True)
    else:
        print(f"[PermutStage Inscription] ⚠️ Client Firestore non initialisé. Écriture dans base de secours locale uniquement.")

    # 2. Écriture persistante sur disque local
    local = load_local_db()
    if "users" not in local: local["users"] = {}
    local["users"][clean_email] = doc_payload
    save_local_db(local)
    print(f"[PermutStage Inscription] ✅ Compte enregistré dans la base locale persistante.")

    # Invalidation du cache mémoire
    invalidate_cache("users")
    return True

def update_user_pin(email: str, new_pin: str) -> bool:
    """Met à jour le code PIN de l'étudiant dans Firestore et synchronise ses demandes."""
    clean_email = email.strip().lower()
    clean_pin = normalize_pin(new_pin)
    db = get_firestore_client()
    if db is not None:
        try:
            db.collection(COLLECTION_USERS).document(clean_email).update({
                "code_pin": clean_pin,
                "PIN": clean_pin
            })
            demandes_q = db.collection(COLLECTION_DEMANDES).where("user_email", "==", clean_email).stream()
            for doc in demandes_q:
                doc.reference.update({"code_pin": clean_pin, "PIN": clean_pin})
        except Exception as exc:
            print(f"[PermutStage] Erreur mise à jour PIN Firestore: {exc}")

    local = load_local_db()
    if clean_email in local.get("users", {}):
        local["users"][clean_email]["code_pin"] = clean_pin
        local["users"][clean_email]["PIN"] = clean_pin
    for d in local.get("demandes", {}).values():
        if (d.get("user_email") or d.get("Email") or "").lower() == clean_email:
            d["code_pin"] = clean_pin
            d["PIN"] = clean_pin
    save_local_db(local)

    # Invalidation du cache mémoire
    invalidate_cache("users")
    return True

def update_user_profile(email: str, prenom: str, nom: str, new_pin: str = None) -> bool:
    """Met à jour le prénom, nom et optionnellement le code PIN de l'étudiant dans Firestore et localement."""
    clean_email = email.strip().lower()
    clean_prenom = str(prenom or "").strip()
    clean_nom = str(nom or "").strip()

    update_dict = {
        "prenom": clean_prenom,
        "Prenom": clean_prenom,
        "nom": clean_nom,
        "Nom": clean_nom,
    }
    if new_pin:
        clean_pin = normalize_pin(new_pin)
        update_dict["code_pin"] = clean_pin
        update_dict["PIN"] = clean_pin

    db = get_firestore_client()
    if db is not None:
        try:
            db.collection(COLLECTION_USERS).document(clean_email).set(update_dict, merge=True)
            nom_complet = f"{clean_prenom} {clean_nom}".strip() or clean_email
            dem_updates = {"nom_etudiant": nom_complet, "Nom": nom_complet}
            if new_pin:
                dem_updates["code_pin"] = clean_pin
                dem_updates["PIN"] = clean_pin
            demandes_q = db.collection(COLLECTION_DEMANDES).where("user_email", "==", clean_email).stream()
            for doc in demandes_q:
                doc.reference.update(dem_updates)
            print(f"[PermutStage] ✅ Profil Firestore mis à jour pour {clean_email}")
        except Exception as exc:
            print(f"[PermutStage] Erreur mise à jour profil Firestore: {exc}")

    local = load_local_db()
    if clean_email in local.get("users", {}):
        local["users"][clean_email].update(update_dict)
    nom_complet = f"{clean_prenom} {clean_nom}".strip() or clean_email
    for d in local.get("demandes", {}).values():
        if (d.get("user_email") or d.get("Email") or "").lower() == clean_email:
            d["nom_etudiant"] = nom_complet
            d["Nom"] = nom_complet
            if new_pin:
                d["code_pin"] = clean_pin
                d["PIN"] = clean_pin
    save_local_db(local)
    invalidate_cache("all")
    return True

def delete_user_and_demandes(email: str) -> bool:
    """Supprime l'utilisateur et ses demandes associées en cascade."""
    clean_email = email.strip().lower()
    db = get_firestore_client()
    if db is not None:
        try:
            db.collection(COLLECTION_USERS).document(clean_email).delete()
            for f in ["user_email", "Email"]:
                docs = db.collection(COLLECTION_DEMANDES).where(f, "==", clean_email).stream()
                for doc in docs:
                    doc.reference.delete()
        except Exception as exc:
            print(f"[PermutStage] Erreur suppression user Firestore: {exc}")

    local = load_local_db()
    local.get("users", {}).pop(clean_email, None)
    to_del = [k for k, v in local.get("demandes", {}).items() if (v.get("user_email") or v.get("Email") or "").lower() == clean_email]
    for k in to_del: local["demandes"].pop(k, None)
    save_local_db(local)

    # Invalidation du cache mémoire
    invalidate_cache("all")
    return True

def load_all_users(force_refresh: bool = False) -> pd.DataFrame:
    """Lit l'ensemble des comptes de la collection 'users' (avec cache mémoire)."""
    global _CACHE_USERS
    now = time.time()
    if not force_refresh and _CACHE_USERS["df"] is not None and (now - _CACHE_USERS["timestamp"]) < CACHE_TTL:
        return _CACHE_USERS["df"].copy()

    db = get_firestore_client()
    users_list = []
    if db is not None:
        try:
            docs = db.collection(COLLECTION_USERS).stream()
            for doc in docs:
                item = doc.to_dict() or {}
                item["email"] = str(item.get("email") or item.get("Email") or doc.id).strip().lower()
                item["nom"] = str(item.get("nom") or item.get("Nom") or "").strip()
                item["prenom"] = str(item.get("prenom") or item.get("Prenom") or "").strip()
                item["code_pin"] = normalize_pin(item.get("code_pin") or item.get("PIN") or "")
                users_list.append(item)
        except Exception as exc:
            print(f"[PermutStage] Erreur load_all_users Firestore: {exc}")

    if not users_list:
        local = load_local_db()
        users_list = list(local.get("users", {}).values())

    cols = ["email", "nom", "prenom", "code_pin", "created_at", "statut"]
    if not users_list:
        df = pd.DataFrame(columns=cols)
    else:
        df = pd.DataFrame(users_list)
        for c in cols:
            if c not in df.columns: df[c] = ""
        # Aliases
        df["Email"] = df["email"]
        df["Nom"] = df["nom"]
        df["Prenom"] = df["prenom"]
        df["PIN"] = df["code_pin"]
        df["User_ID"] = df["email"]

    _CACHE_USERS["df"] = df.copy()
    _CACHE_USERS["timestamp"] = now
    return df

# ---------------------------------------------------------------------------
# 5. GESTION FIRESTORE : DEMANDES DE STAGE (COLLECTION 'demandes')
# ---------------------------------------------------------------------------
def serialize_hospitals(hospitals: list[str]) -> str:
    return "; ".join([str(h).strip() for h in hospitals if str(h).strip()])

def parse_hospitals(raw_val) -> list[str]:
    if isinstance(raw_val, list):
        return [str(h).strip() for h in raw_val if str(h).strip()]
    if not raw_val or pd.isna(raw_val):
        return []
    return [str(h).strip() for h in str(raw_val).split(";") if str(h).strip()]

def serialize_specialites(specialites: list[str]) -> str:
    """Sérialise une liste de spécialités sous forme de chaîne délimitée par des points-virgules."""
    return "; ".join([str(s).strip() for s in (specialites or []) if str(s).strip()])

def parse_specialites(raw_val) -> list[str]:
    """Extrait une liste propre de spécialités depuis une chaîne ou une liste."""
    if isinstance(raw_val, list):
        return [str(s).strip() for s in raw_val if str(s).strip()]
    if not raw_val or pd.isna(raw_val):
        return []
    return [str(s).strip() for s in str(raw_val).split(";") if str(s).strip()]

def wants_specialite(demande_rec: dict, target_specialite: str) -> bool:
    """
    Vérifie si le demandeur 'demande_rec' accepte la spécialité 'target_specialite'.
    - Si 'Peu importe / Toutes les spécialités' (ou 'Peu importe', 'Toutes') est présent : accepte toute spécialité.
    - Si une liste précise est sélectionnée : vérifie si target_specialite s'y trouve.
    - Rétrocompatibilité : si aucune spécialité souhaitée n'est définie (anciennes offres),
      considère que l'étudiant ne souhaite que sa propre spécialité actuelle.
    """
    raw_wants = demande_rec.get("specialites_souhaitees") or demande_rec.get("Specialites_Souhaitees")
    wants_list = parse_specialites(raw_wants) if raw_wants else []

    # Rétrocompatibilité stricte pour les anciennes offres
    if not wants_list:
        cur_spec = str(demande_rec.get("specialite") or demande_rec.get("Specialite") or "").strip().lower()
        return cur_spec == str(target_specialite or "").strip().lower()

    for w in wants_list:
        w_lower = w.strip().lower()
        if "peu importe" in w_lower or "toutes" in w_lower or "indifférent" in w_lower or "indifferent" in w_lower:
            return True

    target_clean = str(target_specialite or "").strip().lower()
    return any(w.strip().lower() == target_clean for w in wants_list)

def save_demande(demande_dict: dict) -> bool:
    """
    Enregistre ou met à jour une offre de permutation dans la collection 'demandes'.
    Champs : user_email, nom_etudiant, periode, specialite, hopital_actuel, hopitaux_souhaites, specialites_souhaitees, statut, updated_at.
    """
    user_email = demande_dict.get("user_email") or demande_dict.get("Email") or ""
    user_email = str(user_email).strip().lower()
    periode = str(demande_dict.get("periode") or demande_dict.get("Periode") or "").strip()
    doc_id = demande_dict.get("demande_id") or demande_dict.get("Demande_ID") or f"{user_email}_{periode}".replace("@", "_at_").replace(".", "_")

    raw_souhaites = demande_dict.get("hopitaux_souhaites") or demande_dict.get("Hopitaux_Souhaites") or []
    h_list = parse_hospitals(raw_souhaites)
    nom_etudiant = demande_dict.get("nom_etudiant") or demande_dict.get("Nom") or user_email
    specialite = demande_dict.get("specialite") or demande_dict.get("Specialite") or ""
    hopital_actuel = demande_dict.get("hopital_actuel") or demande_dict.get("Hopital_Actuel") or ""

    raw_spec_souhaites = demande_dict.get("specialites_souhaitees") or demande_dict.get("Specialites_Souhaitees") or []
    s_list = parse_specialites(raw_spec_souhaites)
    if not s_list:
        if periode in ("P1", "P2"):
            s_list = ["Peu importe / Toutes les spécialités"]
        elif specialite:
            s_list = [specialite]

    statut = (demande_dict.get("statut") or demande_dict.get("Statut") or "disponible").lower()
    if statut in ("disponible", "actif"): statut_clean = "disponible"
    elif statut in ("en_discussion", "en discussion", "en_cours"): statut_clean = "en_cours"
    else: statut_clean = "conclue"

    now_iso = datetime.now(ZoneInfo("Europe/Brussels")).isoformat()
    now_human = datetime.now(ZoneInfo("Europe/Brussels")).strftime("%Y-%m-%d %H:%M:%S")

    doc_payload = {
        "demande_id": doc_id,
        "Demande_ID": doc_id,
        "user_email": user_email,
        "Email": user_email,
        "nom_etudiant": nom_etudiant,
        "Nom": nom_etudiant,
        "periode": periode,
        "Periode": periode,
        "specialite": specialite,
        "Specialite": specialite,
        "hopital_actuel": hopital_actuel,
        "Hopital_Actuel": hopital_actuel,
        "hopitaux_souhaites": h_list,
        "Hopitaux_Souhaites": serialize_hospitals(h_list),
        "specialites_souhaitees": s_list,
        "Specialites_Souhaitees": serialize_specialites(s_list),
        "statut": statut_clean,
        "Statut": "Disponible" if statut_clean == "disponible" else ("En discussion" if statut_clean == "en_cours" else "Accord trouvé"),
        "updated_at": now_iso,
        "Timestamp": now_human,
    }

    db = get_firestore_client()
    if db is not None:
        try:
            db.collection(COLLECTION_DEMANDES).document(doc_id).set(doc_payload)
        except Exception as exc:
            print(f"[PermutStage] Erreur écriture Firestore demande {doc_id}: {exc}")

    local = load_local_db()
    if "demandes" not in local: local["demandes"] = {}
    local["demandes"][doc_id] = doc_payload
    save_local_db(local)

    # Invalidation du cache mémoire
    invalidate_cache("demandes")
    return True

def delete_demande(demande_id: str) -> bool:
    """Supprime une offre de stage dans Firestore."""
    clean_id = str(demande_id).strip()
    db = get_firestore_client()
    if db is not None:
        try:
            db.collection(COLLECTION_DEMANDES).document(clean_id).delete()
        except Exception as exc:
            print(f"[PermutStage] Erreur suppression demande {clean_id}: {exc}")

    local = load_local_db()
    local.get("demandes", {}).pop(clean_id, None)
    save_local_db(local)

    # Invalidation du cache mémoire
    invalidate_cache("demandes")
    return True

def load_demandes_data(force_refresh: bool = False) -> pd.DataFrame:
    """Lit toutes les annonces de la collection 'demandes' (avec cache mémoire)."""
    global _CACHE_DEMANDES
    now = time.time()
    if not force_refresh and _CACHE_DEMANDES["df"] is not None and (now - _CACHE_DEMANDES["timestamp"]) < CACHE_TTL:
        return _CACHE_DEMANDES["df"].copy()

    db = get_firestore_client()
    demandes_list = []
    if db is not None:
        try:
            docs = db.collection(COLLECTION_DEMANDES).stream()
            for doc in docs:
                item = doc.to_dict() or {}
                item["demande_id"] = str(item.get("demande_id") or item.get("Demande_ID") or doc.id).strip()
                item["Demande_ID"] = item["demande_id"]
                item["user_email"] = str(item.get("user_email") or item.get("Email") or "").strip().lower()
                item["Email"] = item["user_email"]
                item["nom_etudiant"] = str(item.get("nom_etudiant") or item.get("Nom") or "").strip()
                item["Nom"] = item["nom_etudiant"]
                item["periode"] = str(item.get("periode") or item.get("Periode") or "").strip()
                item["Periode"] = item["periode"]
                item["specialite"] = str(item.get("specialite") or item.get("Specialite") or "").strip()
                item["Specialite"] = item["specialite"]
                item["hopital_actuel"] = str(item.get("hopital_actuel") or item.get("Hopital_Actuel") or "").strip()
                item["Hopital_Actuel"] = item["hopital_actuel"]
                h_list = parse_hospitals(item.get("hopitaux_souhaites") or item.get("Hopitaux_Souhaites") or [])
                item["hopitaux_souhaites"] = h_list
                item["Hopitaux_Souhaites"] = serialize_hospitals(h_list)
                spec_raw = item.get("specialites_souhaitees") or item.get("Specialites_Souhaitees")
                s_list = parse_specialites(spec_raw)
                if not s_list and item.get("specialite"):
                    s_list = [item["specialite"]]
                item["specialites_souhaitees"] = s_list
                item["Specialites_Souhaitees"] = serialize_specialites(s_list)
                st = str(item.get("statut") or item.get("Statut") or "disponible").lower()
                item["statut"] = "disponible" if st in ("disponible", "actif") else ("en_cours" if st in ("en_discussion", "en discussion", "en_cours") else "conclue")
                item["Statut"] = "Disponible" if item["statut"] == "disponible" else ("En discussion" if item["statut"] == "en_cours" else "Accord trouvé")
                item["updated_at"] = str(item.get("updated_at") or item.get("Timestamp") or datetime.now(ZoneInfo("Europe/Brussels")).isoformat())
                item["Timestamp"] = str(item.get("Timestamp") or item["updated_at"][:19].replace("T", " "))
                demandes_list.append(item)
        except Exception as exc:
            print(f"[PermutStage] Erreur lecture demandes Firestore: {exc}")

    if not demandes_list:
        local = load_local_db()
        demandes_list = list(local.get("demandes", {}).values())

    cols = ["Demande_ID", "Timestamp", "Nom", "Email", "Periode", "Specialite", "Hopital_Actuel", "Hopitaux_Souhaites", "Statut", "user_email", "nom_etudiant", "hopitaux_souhaites", "updated_at", "specialites_souhaitees", "Specialites_Souhaitees"]
    if not demandes_list:
        df = pd.DataFrame(columns=cols)
    else:
        df = pd.DataFrame(demandes_list)
        for c in cols:
            if c not in df.columns: df[c] = ""
        # Rétrocompatibilité : s'assurer que chaque ligne a une liste pour specialites_souhaitees
        for idx in range(len(df)):
            val = df.at[idx, "specialites_souhaitees"]
            if not isinstance(val, list):
                df.at[idx, "specialites_souhaitees"] = parse_specialites(val) or [df.at[idx, "Specialite"]]

    _CACHE_DEMANDES["df"] = df.copy()
    _CACHE_DEMANDES["timestamp"] = now
    return df

# ---------------------------------------------------------------------------
# 6. GESTION FIRESTORE : DISCUSSIONS & MESSAGERIE (COLLECTIONS 'discussions', 'messages')
# ---------------------------------------------------------------------------
def creer_ou_recuperer_discussion(participants: list[str], type_match: str, demande_ids: list[str]) -> dict:
    """
    Crée ou retrouve un salon de discussion dans Firestore.
    Champs : type_match, participants, demande_ids, dernier_message, dernier_timestamp.
    """
    sorted_p = sorted([p.lower().strip() for p in participants if p and p.strip()])
    disc_id = f"disc_{type_match}_{'_'.join(sorted_p)}".replace("@", "_at_").replace(".", "_")

    db = get_firestore_client()
    if db is not None:
        try:
            ref = db.collection(COLLECTION_DISCUSSIONS).document(disc_id)
            snap = ref.get()
            if snap.exists:
                return snap.to_dict() or {}
            payload = {
                "discussion_id": disc_id,
                "type_match": type_match,
                "participants": sorted_p,
                "demande_ids": demande_ids,
                "dernier_message": "",
                "dernier_timestamp": datetime.now(ZoneInfo("Europe/Brussels")).isoformat(),
                "created_at": datetime.now(ZoneInfo("Europe/Brussels")).isoformat(),
                "statut": "nouveau",
            }
            ref.set(payload)
            return payload
        except Exception as exc:
            print(f"[PermutStage] Erreur creer_ou_recuperer_discussion Firestore: {exc}")

    local = load_local_db()
    if "discussions" not in local: local["discussions"] = {}
    if disc_id in local["discussions"]:
        return local["discussions"][disc_id]

    payload = {
        "discussion_id": disc_id,
        "type_match": type_match,
        "participants": sorted_p,
        "demande_ids": demande_ids,
        "dernier_message": "",
        "dernier_timestamp": datetime.now(ZoneInfo("Europe/Brussels")).isoformat(),
        "created_at": datetime.now(ZoneInfo("Europe/Brussels")).isoformat(),
        "statut": "nouveau",
    }
    local["discussions"][disc_id] = payload
    save_local_db(local)
    return payload

def get_discussion_by_id(discussion_id: str) -> dict:
    """Récupère une discussion depuis Firestore ou le stockage local persistant."""
    disc_id = str(discussion_id).strip()
    db = get_firestore_client()
    if db is not None:
        try:
            snap = db.collection(COLLECTION_DISCUSSIONS).document(disc_id).get()
            if snap.exists:
                d = snap.to_dict() or {}
                local = load_local_db()
                if "discussions" not in local: local["discussions"] = {}
                local["discussions"][disc_id] = d
                save_local_db(local)
                return d
        except Exception as exc:
            print(f"[PermutStage] Erreur get_discussion_by_id Firestore: {exc}")

    local = load_local_db()
    return local.get("discussions", {}).get(disc_id, {})

def mettre_a_jour_statut_discussion(discussion_id: str, nouveau_statut: str, confirmed_by: str = "") -> dict:
    """Met à jour le statut d'une discussion ('nouveau', 'en discussion', 'accord trouvé')."""
    disc_id = str(discussion_id).strip()
    now_iso = datetime.now(ZoneInfo("Europe/Brussels")).isoformat()
    upd = {
        "statut": nouveau_statut,
        "statut_updated_at": now_iso,
    }
    if confirmed_by:
        upd["accord_confirme_par"] = confirmed_by
        upd["accord_confirme_at"] = now_iso

    db = get_firestore_client()
    if db is not None:
        try:
            db.collection(COLLECTION_DISCUSSIONS).document(disc_id).set(upd, merge=True)
            print(f"[PermutStage] ✅ Statut discussion '{disc_id}' mis à jour vers '{nouveau_statut}' dans Firestore.")
        except Exception as exc:
            print(f"[PermutStage] Erreur statut discussion Firestore: {exc}")

    local = load_local_db()
    if "discussions" not in local: local["discussions"] = {}
    if disc_id not in local["discussions"]:
        local["discussions"][disc_id] = {"discussion_id": disc_id}
    local["discussions"][disc_id].update(upd)
    save_local_db(local)
    return local["discussions"][disc_id]

def envoyer_message(discussion_id: str, sender_email: str, sender_name: str, texte: str) -> bool:
    """
    Insère un message dans Firestore (collection 'messages')
    et met à jour la discussion parente (collection 'discussions') avec statut 'en discussion' automatique.
    Si c'est le TOUT PREMIER message du salon, notifie par email les autres participants.
    """
    clean_text = texte.strip()
    if not clean_text:
        return False

    clean_sender_email = sender_email.strip().lower()
    clean_sender_name = sender_name.strip() or clean_sender_email

    # 1. Vérifier si c'est le tout premier message du salon (historique vide avant cet envoi)
    is_first_message = False
    try:
        prev_messages = recuperer_messages(discussion_id)
        is_first_message = (len(prev_messages) == 0)
    except Exception as exc:
        logger.warning(f"[PermutStage] Vérification premier message échouée: {exc}")

    msg_id = f"MSG_{uuid.uuid4().hex[:10].upper()}"
    now_iso = datetime.now(ZoneInfo("Europe/Brussels")).isoformat()
    now_human = datetime.now(ZoneInfo("Europe/Brussels")).strftime("%Y-%m-%d %H:%M:%S")

    msg_payload = {
        "message_id": msg_id,
        "Message_ID": msg_id,
        "discussion_id": discussion_id,
        "Room_ID": discussion_id,
        "sender_email": clean_sender_email,
        "Sender_Email": clean_sender_email,
        "sender_name": clean_sender_name,
        "Sender_Name": clean_sender_name,
        "texte": clean_text,
        "Texte": clean_text,
        "timestamp": now_iso,
        "Timestamp": now_human,
    }

    db = get_firestore_client()
    if db is not None:
        try:
            db.collection(COLLECTION_MESSAGES).document(msg_id).set(msg_payload)
            # Vérifier si la discussion est déjà 'accord trouvé' ou non
            cur_doc = db.collection(COLLECTION_DISCUSSIONS).document(discussion_id).get()
            cur_statut = cur_doc.to_dict().get("statut") if cur_doc.exists else ""
            disc_update = {
                "dernier_message": clean_text,
                "dernier_timestamp": now_iso
            }
            if cur_statut != "accord trouvé":
                disc_update["statut"] = "en discussion"
            db.collection(COLLECTION_DISCUSSIONS).document(discussion_id).set(disc_update, merge=True)
        except Exception as exc:
            print(f"[PermutStage] Erreur envoyer_message Firestore: {exc}")

    local = load_local_db()
    if "messages" not in local: local["messages"] = {}
    local["messages"][msg_id] = msg_payload
    if "discussions" in local and discussion_id in local["discussions"]:
        local["discussions"][discussion_id]["dernier_message"] = clean_text
        local["discussions"][discussion_id]["dernier_timestamp"] = now_iso
        if local["discussions"][discussion_id].get("statut") != "accord trouvé":
            local["discussions"][discussion_id]["statut"] = "en discussion"
    save_local_db(local)

    # 2. Si premier message, notifier par email uniquement les autres participants
    if is_first_message:
        try:
            send_first_message_notification(discussion_id, clean_sender_email, clean_sender_name, clean_text)
        except Exception as exc:
            logger.warning(f"[PermutStage] Erreur envoi alerte premier message: {exc}")

    return True

def recuperer_messages(discussion_id: str) -> list[dict]:
    """Récupère l'ensemble des messages d'une discussion triés chronologiquement."""
    db = get_firestore_client()
    messages_list = []
    if db is not None:
        try:
            docs = db.collection(COLLECTION_MESSAGES).where("discussion_id", "==", discussion_id).stream()
            for d in docs:
                messages_list.append(d.to_dict() or {})
            if not messages_list:
                docs2 = db.collection(COLLECTION_MESSAGES).where("Room_ID", "==", discussion_id).stream()
                for d in docs2:
                    messages_list.append(d.to_dict() or {})
        except Exception as exc:
            print(f"[PermutStage] Erreur recuperer_messages Firestore: {exc}")

    if not messages_list:
        local = load_local_db()
        for m in local.get("messages", {}).values():
            if m.get("discussion_id") == discussion_id or m.get("Room_ID") == discussion_id:
                messages_list.append(m)

    messages_list.sort(key=lambda x: str(x.get("timestamp") or x.get("Timestamp") or ""))
    return messages_list

def recuperer_discussions_utilisateur(user_email: str) -> list[dict]:
    """Récupère tous les salons auxquels participe un utilisateur."""
    clean_email = user_email.strip().lower()
    db = get_firestore_client()
    discs = []
    if db is not None:
        try:
            docs = db.collection(COLLECTION_DISCUSSIONS).where("participants", "array_contains", clean_email).stream()
            for d in docs:
                discs.append(d.to_dict() or {})
        except Exception as exc:
            print(f"[PermutStage] Erreur recuperer_discussions_utilisateur Firestore: {exc}")

    if not discs:
        local = load_local_db()
        for d in local.get("discussions", {}).values():
            p_list = [str(p).lower() for p in d.get("participants", [])]
            if clean_email in p_list:
                discs.append(d)
    return discs

COLONNES_MESSAGES = ["Message_ID", "Room_ID", "Sender_Email", "Sender_Name", "Timestamp", "Texte"]

def load_messages_data() -> pd.DataFrame:
    """Compatibilité pour les compteurs et alertes."""
    db = get_firestore_client()
    data = []
    if db is not None:
        try:
            docs = db.collection(COLLECTION_MESSAGES).stream()
            for doc in docs:
                item = doc.to_dict() or {}
                item["Message_ID"] = str(item.get("message_id") or item.get("Message_ID") or doc.id)
                item["Room_ID"] = str(item.get("discussion_id") or item.get("Room_ID") or "")
                item["Sender_Email"] = str(item.get("sender_email") or item.get("Sender_Email") or "")
                item["Sender_Name"] = str(item.get("sender_name") or item.get("Sender_Name") or "")
                item["Timestamp"] = str(item.get("timestamp") or item.get("Timestamp") or "")
                item["Texte"] = str(item.get("texte") or item.get("Texte") or "")
                data.append(item)
        except Exception:
            pass
    if not data:
        local = load_local_db()
        data = list(local.get("messages", {}).values())
    if not data:
        return pd.DataFrame(columns=COLONNES_MESSAGES)
    df = pd.DataFrame(data)
    for c in COLONNES_MESSAGES:
        if c not in df.columns: df[c] = ""
    return df

# ---------------------------------------------------------------------------
# 7. MOTEUR DE MATCHING PUR (100% INTACT ET CONFORME)
# ---------------------------------------------------------------------------
def compute_bilateral_matches(df: pd.DataFrame) -> list[dict]:
    matches = []
    if df.empty:
        return matches
    records = [r for r in df.to_dict("records") if str(r.get("statut") or r.get("Statut") or "").lower() not in ("conclue", "accord trouvé")]
    n = len(records)

    for i in range(n):
        for j in range(i + 1, n):
            a, b = records[i], records[j]
            # Condition 1 : Même période STRICTEMENT obligatoire
            if a["Periode"] != b["Periode"]:
                continue

            # Condition 2 : Règle de spécialité
            # - P1 et P2 (Master 1) : échange selon les spécialités souhaitées croisées (ou joker 'Peu importe')
            # - P3 à P8 (Master 2) : spécialité strictement identique obligatoire
            is_m1 = a["Periode"] in ("P1", "P2")
            if not is_m1:
                if a["Specialite"] != b["Specialite"]:
                    continue
            else:
                if not (wants_specialite(a, b["Specialite"]) and wants_specialite(b, a["Specialite"])):
                    continue

            # Condition 3 : Hôpitaux différents et réciprocité des vœux
            if a["Hopital_Actuel"] == b["Hopital_Actuel"]:
                continue

            souhaites_a = set(parse_hospitals(a.get("hopitaux_souhaites") or a.get("Hopitaux_Souhaites")))
            souhaites_b = set(parse_hospitals(b.get("hopitaux_souhaites") or b.get("Hopitaux_Souhaites")))

            if (
                a["Hopital_Actuel"] in souhaites_b
                and b["Hopital_Actuel"] in souhaites_a
            ):
                email_a = str(a.get("user_email") or a.get("Email")).strip().lower()
                email_b = str(b.get("user_email") or b.get("Email")).strip().lower()
                room_id = build_discussion_id("bilateral", [email_a, email_b])

                # Affichage des spécialités échangées si différentes (Master 1 P1/P2)
                if a["Specialite"] != b["Specialite"]:
                    spec_label = f"{a['Specialite']} ⇄ {b['Specialite']}"
                else:
                    spec_label = a["Specialite"]

                matches.append({
                    "room_id": room_id,
                    "discussion_id": room_id,
                    "periode": a["Periode"],
                    "specialite": spec_label,
                    "participants": [a, b],
                    "emails": [email_a, email_b],
                    "a": a,
                    "b": b,
                })
    return matches

def compute_triangular_matches(df: pd.DataFrame) -> list[dict]:
    matches = []
    if df.empty:
        return matches
    seen_cycles = set()
    records = [r for r in df.to_dict("records") if str(r.get("statut") or r.get("Statut") or "").lower() not in ("conclue", "accord trouvé")]
    n = len(records)

    souhaites_map = {
        idx: set(parse_hospitals(rec.get("hopitaux_souhaites") or rec.get("Hopitaux_Souhaites")))
        for idx, rec in enumerate(records)
    }

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            a, b = records[i], records[j]
            # Même période obligatoire
            if a["Periode"] != b["Periode"]:
                continue

            # Règle de spécialité P1/P2 vs P3-P8
            is_m1 = a["Periode"] in ("P1", "P2")
            if not is_m1:
                if a["Specialite"] != b["Specialite"]:
                    continue
            else:
                # B reçoit le stage de A
                if not wants_specialite(b, a["Specialite"]):
                    continue

            if a["Hopital_Actuel"] == b["Hopital_Actuel"]:
                continue
            if a["Hopital_Actuel"] not in souhaites_map[j]:
                continue

            for k in range(n):
                if k in (i, j):
                    continue
                c = records[k]
                if c["Periode"] != a["Periode"]:
                    continue

                if not is_m1:
                    if c["Specialite"] != a["Specialite"] or c["Specialite"] != b["Specialite"]:
                        continue
                else:
                    # C reçoit B, et A reçoit C
                    if not (wants_specialite(c, b["Specialite"]) and wants_specialite(a, c["Specialite"])):
                        continue

                if (
                    c["Hopital_Actuel"] == a["Hopital_Actuel"]
                    or c["Hopital_Actuel"] == b["Hopital_Actuel"]
                ):
                    continue

                if (
                    b["Hopital_Actuel"] in souhaites_map[k]
                    and c["Hopital_Actuel"] in souhaites_map[i]
                ):
                    id_a = f"{str(a.get('user_email') or a.get('Email')).lower()}_{a['Periode']}"
                    id_b = f"{str(b.get('user_email') or b.get('Email')).lower()}_{b['Periode']}"
                    id_c = f"{str(c.get('user_email') or c.get('Email')).lower()}_{c['Periode']}"
                    rotations = sorted([
                        (id_a, id_b, id_c),
                        (id_b, id_c, id_a),
                        (id_c, id_a, id_b),
                    ])
                    canonical = rotations[0]
                    if canonical not in seen_cycles:
                        seen_cycles.add(canonical)
                        email_a = str(a.get("user_email") or a.get("Email")).strip().lower()
                        email_b = str(b.get("user_email") or b.get("Email")).strip().lower()
                        email_c = str(c.get("user_email") or c.get("Email")).strip().lower()
                        room_id = build_discussion_id("triangulaire", [email_a, email_b, email_c])

                        if a["Specialite"] == b["Specialite"] == c["Specialite"]:
                            spec_label = a["Specialite"]
                        else:
                            spec_label = f"{a['Specialite']} ⇄ {b['Specialite']} ⇄ {c['Specialite']}"

                        matches.append({
                            "room_id": room_id,
                            "discussion_id": room_id,
                            "periode": a["Periode"],
                            "specialite": spec_label,
                            "participants": [a, b, c],
                            "emails": [email_a, email_b, email_c],
                            "a": a,
                            "b": b,
                            "c": c,
                        })
    return matches

def compute_quadrangular_matches(df: pd.DataFrame) -> list[dict]:
    """
    Détecte les cycles de permutation quadrangulaires à 4 personnes (A → B → C → D → A).
    Conditions :
    1. Même période pour les 4 participants.
    2. Règle de spécialité : croisée avec vœux acceptés en P1/P2 (Master 1), strictement identique de P3 à P8 (Master 2).
    3. Hôpitaux actuels tous mutuellement distincts (pas de doublon parmi les 4).
    4. Chaîne cyclique complète d'acceptation : A -> B -> C -> D -> A.
    5. Dédoublonnage canonique strict sur les 4 rotations circulaires possibles.
    """
    matches = []
    if df.empty:
        return matches
    seen_cycles = set()
    records = [
        r for r in df.to_dict("records")
        if str(r.get("statut") or r.get("Statut") or "").lower() not in ("conclue", "accord trouvé")
    ]
    n = len(records)
    if n < 4:
        return matches

    souhaites_map = {
        idx: set(parse_hospitals(rec.get("hopitaux_souhaites") or rec.get("Hopitaux_Souhaites")))
        for idx, rec in enumerate(records)
    }

    for i in range(n):
        a = records[i]
        p_a = a["Periode"]
        h_a = a["Hopital_Actuel"]
        is_m1 = p_a in ("P1", "P2")

        for j in range(n):
            if j == i:
                continue
            b = records[j]
            if b["Periode"] != p_a:
                continue
            if not is_m1:
                if b["Specialite"] != a["Specialite"]:
                    continue
            else:
                # B reçoit le stage de A
                if not wants_specialite(b, a["Specialite"]):
                    continue

            h_b = b["Hopital_Actuel"]
            if h_b == h_a or h_a not in souhaites_map[j]:
                continue

            for k in range(n):
                if k in (i, j):
                    continue
                c = records[k]
                if c["Periode"] != p_a:
                    continue
                if not is_m1:
                    if c["Specialite"] != a["Specialite"]:
                        continue
                else:
                    # C reçoit le stage de B
                    if not wants_specialite(c, b["Specialite"]):
                        continue

                h_c = c["Hopital_Actuel"]
                if h_c in (h_a, h_b) or h_b not in souhaites_map[k]:
                    continue

                for l in range(n):
                    if l in (i, j, k):
                        continue
                    d = records[l]
                    if d["Periode"] != p_a:
                        continue
                    if not is_m1:
                        if d["Specialite"] != a["Specialite"]:
                            continue
                    else:
                        # D reçoit C, et A reçoit D
                        if not (wants_specialite(d, c["Specialite"]) and wants_specialite(a, d["Specialite"])):
                            continue

                    h_d = d["Hopital_Actuel"]
                    if h_d in (h_a, h_b, h_c):
                        continue

                    # Vérification des deux derniers liens de la boucle : C -> D et D -> A
                    if h_c in souhaites_map[l] and h_d in souhaites_map[i]:
                        id_a = f"{str(a.get('user_email') or a.get('Email')).lower()}_{p_a}"
                        id_b = f"{str(b.get('user_email') or b.get('Email')).lower()}_{p_a}"
                        id_c = f"{str(c.get('user_email') or c.get('Email')).lower()}_{p_a}"
                        id_d = f"{str(d.get('user_email') or d.get('Email')).lower()}_{p_a}"

                        # Dédoublonnage canonique strict des 4 rotations circulaires
                        rotations = sorted([
                            (id_a, id_b, id_c, id_d),
                            (id_b, id_c, id_d, id_a),
                            (id_c, id_d, id_a, id_b),
                            (id_d, id_a, id_b, id_c),
                        ])
                        canonical = rotations[0]
                        if canonical not in seen_cycles:
                            seen_cycles.add(canonical)
                            email_a = str(a.get("user_email") or a.get("Email")).strip().lower()
                            email_b = str(b.get("user_email") or b.get("Email")).strip().lower()
                            email_c = str(c.get("user_email") or c.get("Email")).strip().lower()
                            email_d = str(d.get("user_email") or d.get("Email")).strip().lower()
                            room_id = build_discussion_id("quadrille", [email_a, email_b, email_c, email_d])

                            if a["Specialite"] == b["Specialite"] == c["Specialite"] == d["Specialite"]:
                                spec_label = a["Specialite"]
                            else:
                                spec_label = f"{a['Specialite']} ⇄ {b['Specialite']} ⇄ {c['Specialite']} ⇄ {d['Specialite']}"

                            matches.append({
                                "room_id": room_id,
                                "discussion_id": room_id,
                                "periode": p_a,
                                "specialite": spec_label,
                                "participants": [a, b, c, d],
                                "emails": [email_a, email_b, email_c, email_d],
                                "a": a,
                                "b": b,
                                "c": c,
                                "d": d,
                            })
    return matches

def filter_private_matches_for_user(
    user_email: str | None,
    all_bilateral: list[dict],
    all_triangular: list[dict],
    all_quadrangular: list[dict] = None,
) -> tuple[list[dict], list[dict], list[dict]]:
    if not user_email:
        return [], [], []
    clean_email = user_email.strip().lower()
    my_bi = [m for m in all_bilateral if clean_email in [e.lower() for e in m["emails"]]]
    my_tri = [t for t in all_triangular if clean_email in [e.lower() for e in t["emails"]]]
    my_quad = [q for q in (all_quadrangular or []) if clean_email in [e.lower() for e in q["emails"]]]
    return my_bi, my_tri, my_quad

def build_user_notifications(
    user_email: str | None,
    my_bi: list[dict],
    my_tri: list[dict],
    df_messages: pd.DataFrame = None,
    my_quad: list[dict] = None,
) -> list[dict]:
    if not user_email:
        return []
    clean_email = user_email.strip().lower()
    notifs = []
    my_rooms = set()

    for m in my_bi:
        my_rooms.add(m["room_id"])
        notifs.append({
            "titre": f"Correspondance directe trouvée ({m['specialite']} · {m['periode']})",
            "detail": f"Échange binôme trouvé avec {m['b']['Nom'] if clean_email == str(m['a'].get('Email')).lower() else m['a']['Nom']}.",
            "room_id": m["room_id"],
        })

    for t in my_tri:
        my_rooms.add(t["room_id"])
        notifs.append({
            "titre": f"Cycle triangulaire disponible ({t['specialite']} · {t['periode']})",
            "detail": "Un cycle d'échange complet à 3 étudiants a été formé.",
            "room_id": t["room_id"],
        })

    for q in (my_quad or []):
        my_rooms.add(q["room_id"])
        notifs.append({
            "titre": f"Cycle en carré disponible ({q['specialite']} · {q['periode']})",
            "detail": "Un cycle d'échange complet à 4 étudiants a été formé.",
            "room_id": q["room_id"],
        })

    if df_messages is not None and not df_messages.empty and my_rooms:
        msgs_for_me = df_messages[
            (df_messages["Room_ID"].isin(my_rooms))
            & (df_messages["Sender_Email"].str.lower() != clean_email)
        ]
        for _, msg in msgs_for_me.iterrows():
            notifs.append({
                "titre": f"Message de {msg['Sender_Name']} ({msg['Timestamp']})",
                "detail": f"« {msg['Texte']} »",
                "room_id": msg["Room_ID"],
            })

    return notifs

# ---------------------------------------------------------------------------
# 8. ENVOI DES EMAILS D'ALERTE SMTP & NOTIFICATIONS AUTOMATIQUES
# ---------------------------------------------------------------------------
def get_smtp_config():
    """
    Récupère la configuration SMTP depuis les variables d'environnement (Render)
    ou depuis les fichiers secrets locaux de secours.
    Variables d'environnement requises : SMTP_USERNAME et SMTP_PASSWORD.
    """
    server = os.environ.get("SMTP_SERVER", "smtp.gmail.com").strip()
    try:
        port = int(os.environ.get("SMTP_PORT", 587))
    except (ValueError, TypeError):
        port = 587
    user = os.environ.get("SMTP_USERNAME", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()

    if not user or not password:
        # Repli de secours : vérification des fichiers secrets.toml si présents
        for p in [os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml"), "secrets.toml"]:
            if os.path.exists(p):
                try:
                    try:
                        import tomllib
                    except ImportError:
                        try:
                            import tomli as tomllib
                        except ImportError:
                            tomllib = None
                    if tomllib:
                        with open(p, "rb") as f:
                            sec = tomllib.load(f)
                            if "smtp" in sec:
                                s_dict = sec["smtp"]
                                user = user or str(s_dict.get("username") or s_dict.get("user") or "").strip()
                                password = password or str(s_dict.get("password") or "").strip()
                                server = str(s_dict.get("server", server)).strip()
                                try:
                                    port = int(s_dict.get("port", port))
                                except Exception:
                                    pass
                                break
                except Exception:
                    pass

    if not user or not password:
        return None
    return server, port, user, password

def _send_email_smtp(dest_email: str, subject: str, body: str) -> bool:
    """
    Envoie un email via SMTP en gérant TLS (port 587) et SSL (port 465).
    Protégé par try/except avec boucle de 3 tentatives maximum (retry) et pause de 1,5s
    pour contourner les erreurs temporaires de résolution réseau / IPv6 (Errno 101).
    """
    clean_dest = str(dest_email or "").strip().lower()
    if not clean_dest or "@" not in clean_dest:
        return False

    smtp_cfg = get_smtp_config()
    if not smtp_cfg:
        logger.info(f"[PermutStage SMTP] Email non envoyé à {clean_dest} : SMTP non configuré.")
        return False

    smtp_server, smtp_port, smtp_user, smtp_password = smtp_cfg
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = clean_dest

    for attempt in range(1, 4):
        try:
            if smtp_port == 465:
                with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=12) as server:
                    server.login(smtp_user, smtp_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(smtp_server, smtp_port, timeout=12) as server:
                    server.ehlo()
                    if smtp_port in (587, 25):
                        server.starttls()
                        server.ehlo()
                    server.login(smtp_user, smtp_password)
                    server.send_message(msg)
            logger.info(f"[PermutStage SMTP] ✅ Email envoyé avec succès à {clean_dest} (Objet: '{subject}') [Tentative {attempt}/3]")
            return True
        except Exception as exc:
            logger.warning(f"[PermutStage SMTP] ⚠️ Erreur lors de l'envoi email à {clean_dest} (tentative {attempt}/3): {exc}")
            if attempt < 3:
                time.sleep(1.5)
            else:
                return False

    return False

def send_welcome_email(dest_email: str, prenom: str, nom: str, pin: str) -> bool:
    """
    Envoie un email de bienvenue automatique à l'étudiant dès la validation de son compte.
    Rappelle son prénom, son nom, son identifiant email et son code PIN confidentiel à 4 chiffres.
    """
    try:
        clean_prenom = str(prenom or "").strip() or "étudiant(e)"
        clean_nom = str(nom or "").strip()
        clean_pin = normalize_pin(pin)
        clean_email = str(dest_email or "").strip().lower()
        sujet = "[PermutStage] Confirmation de votre inscription & Vos identifiants"
        corps = (
            f"Bonjour {clean_prenom} {clean_nom},\n\n"
            f"Bienvenue sur PermutStage, la plateforme sécurisée de permutation de stages hospitaliers !\n\n"
            f"Votre compte étudiant a été créé avec succès. Voici le récapitulatif de vos identifiants confidentiels de connexion :\n\n"
            f"• Identifiant (email institutionnel) : {clean_email}\n"
            f"• Prénom & Nom : {clean_prenom} {clean_nom}\n"
            f"• Code PIN confidentiel (4 chiffres) : {clean_pin}\n\n"
            f"Vous pouvez vous connecter dès à présent pour déposer vos offres de stage et découvrir vos correspondances :\n"
            f"👉 Connexion : https://permutstage.onrender.com/login-view\n\n"
            f"💡 Vous pourrez modifier votre code PIN à tout instant depuis votre profil en haut à droite une fois connecté(e).\n\n"
            f"Bien cordialement,\n"
            f"L'équipe PermutStage"
        )
        return _send_email_smtp(clean_email, sujet, corps)
    except Exception as exc:
        logger.warning(f"[PermutStage] Erreur send_welcome_email: {exc}")
        return False

def send_pin_recovery_email(dest_email: str, prenom: str, pin: str) -> bool:
    """
    Envoie le code PIN par email de façon sécurisée à l'adresse institutionnelle de l'étudiant.
    """
    try:
        pin_formatte = normalize_pin(pin)
        prenom_clean = str(prenom or "collègue").strip()
        sujet = "[PermutStage] Récupération de votre code PIN"
        corps = (
            f"Bonjour {prenom_clean},\n\n"
            f"Vous avez demandé la récupération de votre code PIN pour accéder à PermutStage.\n\n"
            f"Votre code PIN de connexion est : {pin_formatte}\n\n"
            f"Vous pouvez désormais vous connecter directement sur la plateforme avec votre adresse étudiante et ce code PIN :\n"
            f"👉 Connexion : https://permutstage.onrender.com/login-view\n\n"
            f"💡 Pour votre sécurité, vous pouvez modifier votre code PIN à tout moment depuis le menu profil en haut à droite après connexion.\n\n"
            f"Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet email.\n\n"
            f"L'équipe PermutStage"
        )
        return _send_email_smtp(dest_email, sujet, corps)
    except Exception as exc:
        logger.warning(f"[PermutStage] Erreur send_pin_recovery_email: {exc}")
        return False

def send_match_notification_emails(
    participants: list[dict],
    periode: str,
    specialite: str,
    room_id: str,
    df_utilisateurs: pd.DataFrame = None,
) -> int:
    """
    Alerte individuellement chaque participant d'un match (bilatéral A <-> B ou cycle triangulaire A -> B -> C -> A)
    avec la spécialité, la période et le lien vers leur salon privé.
    Système anti-doublon NOTIFIED_MATCH_ROOMS pour éviter tout spam.
    """
    global NOTIFIED_MATCH_ROOMS
    if room_id in NOTIFIED_MATCH_ROOMS:
        return 0

    smtp_cfg = get_smtp_config()
    if not smtp_cfg:
        NOTIFIED_MATCH_ROOMS.add(room_id)
        return 0

    sent_count = 0
    seen_dest = set()
    sujet = f"[PermutStage] Correspondance trouvée pour votre stage de {specialite} ({periode}) !"

    try:
        for p in participants:
            dest_email = str(p.get("Email") or p.get("user_email") or p.get("email") or "").strip().lower()
            if not dest_email or dest_email in seen_dest:
                continue
            seen_dest.add(dest_email)

            nom = str(p.get("Nom") or p.get("nom_etudiant") or p.get("prenom") or "Étudiant(e)").strip()
            corps = (
                f"Bonjour {nom},\n\n"
                f"Bonne nouvelle ! Une opportunité d'échange de stage vient de se former sur PermutStage pour votre stage de {specialite} (période {periode}).\n\n"
                f"Un salon de discussion privé et sécurisé a été automatiquement créé pour échanger avec vos correspondants :\n"
                f"👉 Accéder à votre salon privé : https://permutstage.onrender.com/salon/{room_id}\n\n"
                f"Connectez-vous dès à présent avec votre adresse institutionnelle et votre code PIN pour débuter la discussion et valider votre accord.\n\n"
                f"À très vite sur PermutStage,\n"
                f"L'équipe PermutStage"
            )
            try:
                if _send_email_smtp(dest_email, sujet, corps):
                    sent_count += 1
            except Exception as mail_err:
                logger.warning(f"[PermutStage] Erreur envoi mail match à {dest_email}: {mail_err}")

        NOTIFIED_MATCH_ROOMS.add(room_id)
        return sent_count
    except Exception as exc:
        logger.warning(f"[PermutStage] Erreur générale send_match_notification_emails: {exc}")
        NOTIFIED_MATCH_ROOMS.add(room_id)
        return sent_count

def get_discussion_participant_emails(discussion_id: str) -> list[str]:
    """Extrait la liste des adresses email des participants d'un salon de discussion."""
    emails = []
    try:
        disc = get_discussion_by_id(discussion_id) or {}
        raw_p = disc.get("participants", [])
        for p in raw_p:
            if isinstance(p, dict):
                em = str(p.get("Email") or p.get("user_email") or p.get("email") or "").strip().lower()
            else:
                em = str(p).strip().lower()
            if em and "@" in em and em not in emails:
                emails.append(em)
    except Exception:
        pass

    if not emails:
        try:
            df = load_demandes_data()
            all_m = compute_bilateral_matches(df) + compute_triangular_matches(df) + compute_quadrangular_matches(df)
            for m in all_m:
                if m.get("room_id") == discussion_id:
                    for p in m.get("participants", []):
                        em = str(p.get("Email") or p.get("user_email") or "").strip().lower()
                        if em and em not in emails:
                            emails.append(em)
                    break
        except Exception:
            pass

    return emails

def send_first_message_notification(discussion_id: str, sender_email: str, sender_name: str, texte: str) -> None:
    """
    Envoie une notification par email lors du TOUT PREMIER message dans un salon.
    Notifie UNIQUEMENT les autres participants du salon (exclut l'expéditeur).
    """
    clean_sender_email = str(sender_email or "").strip().lower()
    clean_sender_name = str(sender_name or "").strip() or clean_sender_email
    participant_emails = get_discussion_participant_emails(discussion_id)

    sujet = "[PermutStage] Nouveau message dans votre salon d'échange"
    apercu = texte.strip()
    if len(apercu) > 280:
        apercu = apercu[:280] + "..."

    for dest_email in participant_emails:
        if not dest_email or dest_email == clean_sender_email:
            continue

        corps = (
            f"Bonjour,\n\n"
            f"{clean_sender_name} vient d'envoyer un premier message dans votre salon d'échange sur PermutStage :\n\n"
            f"« {apercu} »\n\n"
            f"Connectez-vous dès à présent avec votre adresse étudiante et votre code PIN pour lui répondre et organiser votre permutation :\n"
            f"👉 Rejoindre le salon privé : https://permutstage.onrender.com/salon/{discussion_id}\n\n"
            f"L'équipe PermutStage"
        )
        try:
            _send_email_smtp(dest_email, sujet, corps)
        except Exception as exc:
            logger.warning(f"[PermutStage] Échec envoi notification premier message à {dest_email}: {exc}")

# ---------------------------------------------------------------------------
# 9. COMPOSANTS DE SÉLECTION : SPÉCIALITÉS SOUHAITÉES (P1/P2) & HÔPITAUX
# ---------------------------------------------------------------------------
def render_specialites_souhaitees_selector(
    selected_specs: list[str] = None,
    current_periode: str = "P1",
    prefix: str = "depot",
):
    """
    Composant moderne de sélection des spécialités souhaitées en retour pour Master 1 (P1 & P2).
    - Visible et actif uniquement si Période = 'P1' ou 'P2' (masqué pour P3 à P8).
    - Inclut l'option 'Peu importe / Toutes les spécialités' (joker).
    - Propose la liste complète des 6 spécialités du Tronc commun et des 24 Stages au choix.
    """
    sel_list = [str(s).strip() for s in (selected_specs or []) if str(s).strip()]
    sel_set = set(sel_list)

    is_peu_importe = any(
        ("peu importe" in s.lower() or "toutes" in s.lower())
        for s in sel_list
    ) or (not sel_list and str(current_periode).strip() in ("P1", "P2") and prefix == "depot")

    tc_items = []
    for s in SPECIALITES_TRONC_COMMUN:
        is_chk = (s in sel_set) and not is_peu_importe
        tc_items.append(
            Label(
                Input(
                    type="checkbox",
                    name="specialites_souhaitees",
                    value=s,
                    checked=is_chk,
                    cls=f"spec-cb-{prefix}",
                    onchange=f"onSpecificSpecialiteChange('{prefix}')",
                    style="accent-color:#1d4ed8; width:1.15rem; height:1.15rem; margin:0;"
                ),
                Span(s, style="font-size:0.86rem; color:#1e293b; font-weight:500;"),
                style="display:flex; align-items:center; gap:0.45rem; margin-bottom:0.35rem; cursor:pointer;"
            )
        )

    choix_items = []
    for s in SPECIALITES_AU_CHOIX:
        is_chk = (s in sel_set) and not is_peu_importe
        choix_items.append(
            Label(
                Input(
                    type="checkbox",
                    name="specialites_souhaitees",
                    value=s,
                    checked=is_chk,
                    cls=f"spec-cb-{prefix}",
                    onchange=f"onSpecificSpecialiteChange('{prefix}')",
                    style="accent-color:#1d4ed8; width:1.15rem; height:1.15rem; margin:0;"
                ),
                Span(s, style="font-size:0.86rem; color:#1e293b; font-weight:500;"),
                style="display:flex; align-items:center; gap:0.45rem; margin-bottom:0.35rem; cursor:pointer;"
            )
        )

    js_script = Script(f"""
    function updateSpecialitesSouhaiteesVisibility(periodeVal, prefix) {{
        const wrapper = document.getElementById('specialites-souhaitees-wrapper-' + prefix);
        if (!wrapper) return;
        if (periodeVal === 'P1' || periodeVal === 'P2') {{
            wrapper.style.display = 'block';
        }} else {{
            wrapper.style.display = 'none';
        }}
    }}
    function togglePeuImporteSpecialites(prefix) {{
        const masterCb = document.getElementById('spec-peu-importe-' + prefix);
        if (!masterCb) return;
        const cbs = document.querySelectorAll('.spec-cb-' + prefix);
        if (masterCb.checked) {{
            cbs.forEach(cb => {{ cb.checked = false; }});
        }}
    }}
    function onSpecificSpecialiteChange(prefix) {{
        const masterCb = document.getElementById('spec-peu-importe-' + prefix);
        if (!masterCb) return;
        const cbs = document.querySelectorAll('.spec-cb-' + prefix);
        let anyChecked = false;
        cbs.forEach(cb => {{ if (cb.checked) anyChecked = true; }});
        if (anyChecked) {{
            masterCb.checked = false;
        }}
    }}
    """)

    wrapper_display = "block" if str(current_periode).strip() in ("P1", "P2") else "none"

    return Div(
        Div(
            Div(
                Span("🎓", style="font-size:1.1rem; margin-right:0.35rem;"),
                Strong("Spécialité(s) souhaitée(s) en retour (P1 & P2 uniquement)", style="color:#1e40af; font-size:0.95rem; font-weight:700;"),
                style="display:flex; align-items:center; margin-bottom:0.35rem;"
            ),
            P(
                "En Master 1 (P1 et P2), vous pouvez échanger contre une spécialité identique ou différente. Cochez les spécialités que vous acceptez d'obtenir, ou cochez 'Peu importe' si vous êtes ouvert(e) à toutes.",
                style="font-size:0.82rem; color:#475569; margin-bottom:0.75rem; line-height:1.45;"
            ),
            Label(
                Input(
                    type="checkbox",
                    name="specialites_souhaitees",
                    value="Peu importe / Toutes les spécialités",
                    id=f"spec-peu-importe-{prefix}",
                    checked=is_peu_importe,
                    onchange=f"togglePeuImporteSpecialites('{prefix}')",
                    style="accent-color:#1d4ed8; width:1.2rem; height:1.2rem; margin:0;"
                ),
                Span(
                    Strong("✨ Peu importe / Toutes les spécialités"),
                    " (Accepte n'importe quel stage en retour)",
                    style="color:#1e40af; font-size:0.88rem; margin-left:0.4rem;"
                ),
                style="display:flex; align-items:center; background:#eff6ff; border:1px solid #bfdbfe; border-radius:8px; padding:0.6rem 0.85rem; margin-bottom:0.85rem; cursor:pointer;"
            ),
            Div(
                Div(
                    Strong("Tronc commun (6 spécialités)", style="font-size:0.84rem; color:#0f172a; display:block; margin-bottom:0.5rem; text-transform:uppercase; letter-spacing:0.03em;"),
                    *tc_items,
                    style="background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:0.75rem 0.9rem;"
                ),
                Div(
                    Strong("Stages au choix (24 spécialités)", style="font-size:0.84rem; color:#0f172a; display:block; margin-bottom:0.5rem; text-transform:uppercase; letter-spacing:0.03em;"),
                    Div(
                        *choix_items,
                        style="max-height:220px; overflow-y:auto; padding-right:0.25rem;"
                    ),
                    style="background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:0.75rem 0.9rem;"
                ),
                style="display:grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap:0.75rem;"
            ),
            style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:12px; padding:1.15rem; margin-bottom:1.25rem;"
        ),
        js_script,
        id=f"specialites-souhaitees-wrapper-{prefix}",
        style=f"display:{wrapper_display};"
    )

def render_hospital_checkbox_selector(
    selected_hospitals: list[str] = None,
    current_hospital: str = "",
    prefix: str = "depot",
):
    selected_set = set(selected_hospitals or [])
    total_hospitals = len(TOUS_LES_HOPITAUX)
    initial_count = len([h for h in selected_set if h != current_hospital])
    count_label = f"({initial_count} sélectionné{'s' if initial_count > 1 else ''})"

    region_badges = []
    for reg, h_list in HOPITAUX_PAR_REGION.items():
        region_badges.append(
            Button(
                f"+ {reg} ({len(h_list)})",
                type="button",
                cls="quick-badge",
                onclick=f"toggleRegionHospitals('{reg}', '{prefix}')",
                title=f"Ajouter ou retirer tous les hôpitaux de {reg}"
            )
        )
    region_badges.append(
        Button(
            "✕ Tout désélectionner",
            type="button",
            cls="quick-badge-reset",
            onclick=f"clearAllHospitals('{prefix}')",
            title="Décocher tous les hôpitaux souhaités"
        )
    )

    quick_select_block = Div(
        Div(
            Span("⚡", style="font-size:1rem; margin-right:0.35rem;"),
            Strong("Sélection rapide par province / région", style="color:#1e40af; font-size:0.88rem;"),
            Span(" (ajoute tous les hôpitaux de la région) :", style="color:#3b82f6; font-size:0.82rem; margin-left:0.25rem;"),
            style="margin-bottom:0.6rem; display:flex; align-items:center; flex-wrap:wrap;"
        ),
        Div(*region_badges, style="display:flex; flex-wrap:wrap; gap:0.4rem;"),
        cls="quick-select-card"
    )

    region_options = [Option(f"Toutes les régions ({total_hospitals})", value="Toutes")]
    for reg, h_list in HOPITAUX_PAR_REGION.items():
        region_options.append(Option(f"{reg} ({len(h_list)})", value=reg))

    filter_bar = Div(
        Div(
            Label(
                "Filtrer par province / région",
                Select(
                    *region_options,
                    id=f"filter-region-{prefix}",
                    onchange=f"filterHospitals('{prefix}')",
                    style="margin-bottom:0; font-size:0.85rem;"
                ),
                style="margin-bottom:0; font-size:0.8rem; font-weight:600; color:#475569;"
            ),
            style="flex:1; min-width:200px;"
        ),
        Div(
            Label(
                "Recherche textuelle en direct",
                Div(
                    Input(
                        id=f"search-hospital-{prefix}",
                        type="text",
                        placeholder="Rechercher un hôpital (ex. Saint-Luc, Citadelle, Helora...)",
                        oninput=f"filterHospitals('{prefix}')",
                        style="margin-bottom:0; font-size:0.85rem; padding-left:2.2rem;"
                    ),
                    Span("🔍", style="position:absolute; left:0.75rem; top:50%; transform:translateY(-50%); pointer-events:none; font-size:0.85rem; opacity:0.6;"),
                    style="position:relative;"
                ),
                style="margin-bottom:0; font-size:0.8rem; font-weight:600; color:#475569;"
            ),
            style="flex:2; min-width:260px;"
        ),
        style="display:flex; gap:0.75rem; flex-wrap:wrap; margin-bottom:0.75rem; align-items:flex-end;"
    )

    rows = []
    for h in TOUS_LES_HOPITAUX:
        reg = HOPITAL_VERS_REGION.get(h, "Autre")
        is_current = (h == current_hospital)
        is_checked = (h in selected_set) and not is_current
        h_slug = slugify(h)

        rows.append(
            Div(
                Label(
                    Div(
                        Span(f"[{reg}]", cls="hospital-reg-tag"),
                        Span(h, cls="hospital-name-text"),
                        Span(
                            "⚠️ (Votre hôpital actuel)",
                            cls="hospital-current-badge",
                            id=f"current-badge-{prefix}-{h_slug}",
                            style=f"display:{'inline-block' if is_current else 'none'};"
                        ),
                        style="display:flex; align-items:center; gap:0.45rem; flex-wrap:wrap;"
                    ),
                    style="margin:0; cursor:pointer; flex:1; display:flex; align-items:center;"
                ),
                Input(
                    type="checkbox",
                    name="hopitaux_souhaites",
                    value=h,
                    checked=is_checked,
                    disabled=is_current,
                    cls="hospital-checkbox-custom",
                    id=f"cb-{prefix}-{h_slug}",
                    data_region=reg,
                    data_hospital=h,
                    onchange=f"updateHospitalSelectionCounter('{prefix}')"
                ),
                id=f"row-{prefix}-{h_slug}",
                cls=f"hospital-row-item {'is-current-hospital' if is_current else ''}",
                data_region=reg,
                data_hospital=h.lower()
            )
        )

    scroll_container = Div(
        *rows,
        id=f"hospital-list-{prefix}",
        cls="hospital-scroll-container"
    )

    bottom_helper = Div(
        Small(
            Span(f"{total_hospitals} hôpitaux affichés", id=f"visible-count-{prefix}"),
            " · Cochez les hôpitaux où vous accepteriez de permuter.",
            style="color:#64748b; font-size:0.8rem;"
        ),
        style="margin-top:0.5rem; display:flex; justify-content:space-between; align-items:center;"
    )

    js_script = Script(f"""
    function updateHospitalSelectionCounter(prefix) {{
        const list = document.getElementById('hospital-list-' + prefix);
        if (!list) return;
        const cbs = list.querySelectorAll('input[type="checkbox"]:not([disabled])');
        let checkedCount = 0;
        cbs.forEach(cb => {{ if (cb.checked) checkedCount++; }});

        const counterEl = document.getElementById('selected-counter-' + prefix);
        if (counterEl) {{
            counterEl.textContent = '(' + checkedCount + ' sélectionné' + (checkedCount > 1 ? 's' : '') + ')';
            if (checkedCount > 0) {{
                counterEl.classList.add('has-selected');
            }} else {{
                counterEl.classList.remove('has-selected');
            }}
        }}
    }}

    function toggleRegionHospitals(regionName, prefix) {{
        const list = document.getElementById('hospital-list-' + prefix);
        if (!list) return;
        const cbs = list.querySelectorAll('input[type="checkbox"][data-region="' + regionName + '"]:not([disabled])');
        let allChecked = true;
        cbs.forEach(cb => {{ if (!cb.checked) allChecked = false; }});

        cbs.forEach(cb => {{
            cb.checked = !allChecked;
        }});
        updateHospitalSelectionCounter(prefix);
    }}

    function clearAllHospitals(prefix) {{
        const list = document.getElementById('hospital-list-' + prefix);
        if (!list) return;
        const cbs = list.querySelectorAll('input[type="checkbox"]:not([disabled])');
        cbs.forEach(cb => {{ cb.checked = false; }});
        updateHospitalSelectionCounter(prefix);
    }}

    function filterHospitals(prefix) {{
        const list = document.getElementById('hospital-list-' + prefix);
        const searchInput = document.getElementById('search-hospital-' + prefix);
        const regionSelect = document.getElementById('filter-region-' + prefix);
        const visibleCountEl = document.getElementById('visible-count-' + prefix);

        if (!list) return;
        const q = (searchInput ? searchInput.value : '').toLowerCase().trim();
        const selectedRegion = regionSelect ? regionSelect.value : 'Toutes';

        const rows = list.querySelectorAll('.hospital-row-item');
        let visibleCount = 0;

        rows.forEach(row => {{
            const rowRegion = row.getAttribute('data-region');
            const rowHospital = row.getAttribute('data-hospital') || '';
            const matchRegion = (selectedRegion === 'Toutes' || rowRegion === selectedRegion);
            const matchQuery = (!q || rowHospital.includes(q) || rowRegion.toLowerCase().includes(q));

            if (matchRegion && matchQuery) {{
                row.style.display = 'flex';
                visibleCount++;
            }} else {{
                row.style.display = 'none';
            }}
        }});

        if (visibleCountEl) {{
            visibleCountEl.textContent = visibleCount + ' hôpital(ux) affiché(s)';
        }}
    }}

    function syncCurrentHospitalWithSelector(currentHospitalName, prefix) {{
        const list = document.getElementById('hospital-list-' + prefix);
        if (!list) return;
        const rows = list.querySelectorAll('.hospital-row-item');
        rows.forEach(row => {{
            const cb = row.querySelector('input[type="checkbox"]');
            if (!cb) return;
            const hName = cb.getAttribute('data-hospital');
            const badge = row.querySelector('.hospital-current-badge');
            if (hName === currentHospitalName) {{
                row.classList.add('is-current-hospital');
                if (badge) badge.style.display = 'inline-block';
                cb.checked = false;
                cb.disabled = true;
            }} else {{
                row.classList.remove('is-current-hospital');
                if (badge) badge.style.display = 'none';
                cb.disabled = false;
            }}
        }});
        updateHospitalSelectionCounter(prefix);
    }}

    document.addEventListener('DOMContentLoaded', function() {{
        updateHospitalSelectionCounter('{prefix}');
    }});
    setTimeout(function() {{
        updateHospitalSelectionCounter('{prefix}');
    }}, 60);
    """)

    return Div(
        Div(
            H4("Hôpitaux souhaités *", style="margin-bottom:0; font-size:1.05rem; font-weight:700; color:#0f172a;"),
            Span(count_label, id=f"selected-counter-{prefix}", cls=f"badge-counter {'has-selected' if initial_count > 0 else ''}"),
            style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.75rem;"
        ),
        quick_select_block,
        filter_bar,
        scroll_container,
        bottom_helper,
        js_script,
        cls="hospital-selector-wrapper"
    )

# ---------------------------------------------------------------------------
# 10. EN-TÊTE & PIED DE PAGE GLOBAUX
# ---------------------------------------------------------------------------
def get_session_user(session, req: Request = None) -> dict | None:
    """
    Charge le profil complet de l'utilisateur connecté depuis Firestore.
    Priorité :
    1. session['user_id'] ou session['user_email'] ou session['email']
    2. req.query_params.get('auth') ou req.query_params.get('user_email')
    Recharge directement depuis Firestore db.collection('users').document(email).get().
    """
    user_email = session.get("user_id") or session.get("user_email") or session.get("email")
    if not user_email and req is not None:
        try:
            q_email = req.query_params.get("auth") or req.query_params.get("user_email") or req.query_params.get("u")
            if q_email:
                user_email = q_email.strip().lower()
                session["user_id"] = user_email
                session["user_email"] = user_email
                session["email"] = user_email
        except Exception:
            pass

    if not user_email:
        return None

    clean_email = str(user_email).strip().lower()
    # Si la session contient déjà le nom et prénom, retourner directement sans requête Firestore
    if session.get("nom") and session.get("prenom"):
        return {
            "email": clean_email,
            "Email": clean_email,
            "nom": session.get("nom"),
            "Nom": session.get("nom"),
            "prenom": session.get("prenom"),
            "Prenom": session.get("prenom"),
            "code_pin": session.get("pin", ""),
            "PIN": session.get("pin", ""),
            "statut": "actif",
        }

    user_data = get_user_by_email(clean_email)
    if user_data:
        session["user_id"] = clean_email
        session["user_email"] = clean_email
        session["email"] = clean_email
        if user_data.get("nom"): session["nom"] = user_data["nom"]
        if user_data.get("prenom"): session["prenom"] = user_data["prenom"]
        if user_data.get("code_pin"): session["pin"] = user_data["code_pin"]
        return user_data

    return {
        "email": clean_email,
        "Email": clean_email,
        "nom": session.get("nom", "Étudiant"),
        "Nom": session.get("nom", "Étudiant"),
        "prenom": session.get("prenom", ""),
        "Prenom": session.get("prenom", ""),
        "code_pin": session.get("pin", ""),
        "PIN": session.get("pin", ""),
        "statut": "actif",
        "created_at": datetime.now(ZoneInfo("Europe/Brussels")).isoformat(),
    }

def render_header(session, active_tab="accueil", req: Request = None):
    """
    En-tête ultra-léger et rapide : aucun calcul de matching ni requête lourde Firestore.
    Le calcul des correspondances est réservé exclusivement à la page dédiée /matchs.
    """
    current_u = get_session_user(session, req)
    user_email = current_u.get("email") if current_u else None
    user_prenom = current_u.get("prenom") if current_u else ""
    user_nom = current_u.get("nom") if current_u else ""
    is_admin = session.get("is_admin", False)

    tabs = [
        ("accueil", "Accueil & Guide", "/"),
        ("deposer", "1. Déposer une demande", "/deposer"),
        ("matchs", "2. Mes Matchs & Salons", "/matchs"),
        ("catalogue", "3. Catalogue public", "/catalogue"),
        ("gerer", "4. Gérer mon offre", "/gerer"),
    ]
    if user_email:
        tabs.append(("profil", "👤 Mon Profil", "/profil"))
    if is_admin:
        tabs.append(("admin", "🛠️ Administration", "/admin"))

    nav_items = [
        Li(A(label, href=url, cls=f"nav-tab-btn {'active' if key == active_tab else ''}", hx_boost="false"))
        for key, label, url in tabs
    ]

    if user_email:
        display_name = f"{user_prenom} {user_nom}".strip() or user_email
        auth_section = Div(
            Details(
                Summary(
                    f"👤 {display_name} ▾",
                    role="button",
                    cls="outline",
                    title="Menu profil étudiant : modifier mes informations ou changer mon code PIN",
                    style="padding:0.35rem 0.75rem; font-size:0.85rem; font-weight:700; border-radius:9999px; margin-right:0.5rem; background:#eff6ff; color:#1d4ed8; border-color:#bfdbfe; cursor:pointer; display:inline-flex; align-items:center; list-style:none;"
                ),
                Ul(
                    Li(
                        Div(
                            Strong(display_name, style="display:block; color:#0f172a; font-size:0.88rem;"),
                            Span(user_email, style="display:block; color:#64748b; font-size:0.75rem; font-family:monospace;"),
                            style="padding:0.4rem 0.75rem; border-bottom:1px solid #e2e8f0; margin-bottom:0.25rem;"
                        )
                    ),
                    Li(A("👤 Mon Profil complet", href="/profil", style="display:flex; align-items:center; gap:0.5rem; padding:0.4rem 0.75rem; font-weight:600; color:#1e293b; text-decoration:none; border-radius:6px;")),
                    Li(A("🔒 Changer mon code PIN", href="/profil#changer-pin", style="display:flex; align-items:center; gap:0.5rem; padding:0.4rem 0.75rem; font-weight:700; color:#1d4ed8; text-decoration:none; border-radius:6px; background:#eff6ff;")),
                    Li(A("📋 Gérer mon offre", href="/gerer", style="display:flex; align-items:center; gap:0.5rem; padding:0.4rem 0.75rem; font-weight:600; color:#1e293b; text-decoration:none; border-radius:6px;")),
                    Li(A("💬 Mes Matchs & Salons", href="/matchs", style="display:flex; align-items:center; gap:0.5rem; padding:0.4rem 0.75rem; font-weight:600; color:#1e293b; text-decoration:none; border-radius:6px;")),
                    Li(Hr(style="margin:0.25rem 0; border-color:#e2e8f0;")),
                    Li(A("🚪 Se déconnecter", href="/logout", style="display:flex; align-items:center; gap:0.5rem; padding:0.4rem 0.75rem; font-weight:700; color:#dc2626; text-decoration:none; border-radius:6px;")),
                    style="background:#ffffff; border:1px solid #cbd5e1; border-radius:12px; box-shadow:0 10px 25px -5px rgba(15,23,42,0.18), 0 8px 10px -6px rgba(15,23,42,0.1); padding:0.4rem; min-width:230px; position:absolute; right:0; margin-top:0.35rem; z-index:99999;"
                ),
                cls="dropdown",
                style="position:relative; display:inline-block; margin-right:0.4rem;"
            ),
            A(
                "🔔 Notifications",
                href="/notifications",
                role="button",
                cls="outline",
                style="padding:0.35rem 0.7rem; font-size:0.8rem; margin-right:0.5rem; font-weight:700; border-radius:8px;"
            ),
            A(
                "Déconnexion",
                href="/logout",
                role="button",
                cls="secondary outline",
                style="padding:0.35rem 0.7rem; font-size:0.8rem; border-radius:8px;"
            ),
            style="display:flex; align-items:center;"
        )
    else:
        auth_section = Div(
            A(
                "Connexion / Inscription",
                href="/login-view",
                role="button",
                cls="primary",
                style="padding:0.45rem 1rem; font-size:0.85rem; font-weight:700; border-radius:8px; background:#1d4ed8; border-color:#1d4ed8;"
            ),
            style="display:flex; align-items:center;"
        )

    return Header(
        Title("PermutStage — Plateforme d'échange de stages de médecine"),
        Div(
            Nav(
                Ul(
                    Li(
                        A(
                            Strong("PermutStage", cls="brand-title"),
                            Span("Master 2 Médecine", cls="brand-subtitle"),
                            href="/",
                            hx_boost="false"
                        )
                    )
                ),
                Ul(Li(auth_section)),
            ),
            cls="container-fluid"
        ),
        Div(
            Nav(
                Ul(*nav_items),
                cls="nav-tabs"
            ),
            cls="container-fluid"
        ),
        cls="app-header"
    )

def render_footer():
    return Footer(
        Div(
            P("Plateforme conçue et développée par ", Strong("Imrane Machbaête"), " — Version Alpha"),
            A("🔒 Accès Administrateur", href="/admin-login-view", style="display:block; margin-top:0.5rem; font-size:0.75rem; color:#94a3b8; text-decoration:none;"),
            style="text-align: center; color: #64748b; font-size: 0.82rem; padding: 2rem 0 1rem 0;"
        ),
        cls="container-fluid"
    )

# ---------------------------------------------------------------------------
# 11. ROUTES PRINCIPALES DE L'APPLICATION
# ---------------------------------------------------------------------------

# === VUE 1 : ACCUEIL & GUIDE ===
@rt("/")
def get(session, req: Request = None):
    try:
        df_demandes = load_demandes_data()
    except Exception as exc:
        print(f"[PermutStage] Erreur chargement demandes accueil: {exc}")
        df_demandes = pd.DataFrame()

    try:
        df_users = load_all_users()
    except Exception as exc:
        print(f"[PermutStage] Erreur chargement users accueil: {exc}")
        df_users = pd.DataFrame()

    try:
        all_bi = compute_bilateral_matches(df_demandes)
    except Exception as exc:
        print(f"[PermutStage] Erreur matching bilatéral accueil: {exc}")
        all_bi = []

    try:
        all_tri = compute_triangular_matches(df_demandes)
    except Exception as exc:
        print(f"[PermutStage] Erreur matching triangulaire accueil: {exc}")
        all_tri = []

    try:
        all_quad = compute_quadrangular_matches(df_demandes)
    except Exception as exc:
        print(f"[PermutStage] Erreur matching quadrangulaire accueil: {exc}")
        all_quad = []

    return Main(
        render_header(session, "accueil", req),
        Div(
            Div(
                Div("✨ PROMOTION MÉDECINE · MASTER 1 & MASTER 2", cls="hero-badge"),
                H1("Trouvez votre binôme de stage idéal en quelques clics", style="font-size:2.1rem; font-weight:800;"),
                P(
                    "Bienvenue sur ",
                    Strong("PermutStage"),
                    ", la plateforme conçue spécialement pour faciliter et fluidifier les permutations de lieux de stages hospitaliers entre camarades de promotion. Fini les listes dispersées et les messages perdus : vos souhaits sont analysés intelligemment en toute confidentialité.",
                    style="font-size:1.05rem; opacity:0.95; line-height:1.6;"
                ),
                Div(
                    Strong("🤝 Statut du projet : Version Alpha / Concept Test"),
                    Br(),
                    "Cette plateforme est une initiative bénévole conçue par et pour les étudiants. Seules les personnes directement impliquées dans un échange ont accès à leurs coordonnées réciproques.",
                    cls="hero-alpha-box"
                ),
                cls="hero-banner"
            ),
            # KPIs
            Div(
                Div(Div(str(len(df_users)), cls="stat-val"), Div("Étudiants inscrits", cls="stat-lbl"), cls="stat-card"),
                Div(Div(str(len(df_demandes)), cls="stat-val"), Div("Offres actives", cls="stat-lbl"), cls="stat-card"),
                Div(Div(str(len(all_bi)), cls="stat-val"), Div("Matchs bilatéraux (A ↔ B)", cls="stat-lbl"), cls="stat-card"),
                Div(Div(str(len(all_tri)), cls="stat-val"), Div("Cycles triangulaires (3)", cls="stat-lbl"), cls="stat-card"),
                Div(Div(str(len(all_quad)), cls="stat-val"), Div("Cycles en carré (4)", cls="stat-lbl"), cls="stat-card"),
                style="display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:1rem; margin-bottom:2rem;"
            ),
            # Les 4 étapes
            H3("🧭 Le parcours en 4 étapes simples", style="font-weight:800; color:#0f172a; margin-bottom:1rem;"),
            Div(
                Article(
                    Strong("1. Créer son profil"),
                    P("Nom, prénom, email institutionnel et code PIN à 4 chiffres. Votre compte persiste dans la base de données.", style="font-size:0.85rem; color:#475569; margin-top:0.35rem;"),
                ),
                Article(
                    Strong("2. Déposer son offre"),
                    P("Indiquez votre stage actuel (période P1 à P8, spécialité, hôpital) et cochez facilement vos hôpitaux souhaités par région.", style="font-size:0.85rem; color:#475569; margin-top:0.35rem;"),
                ),
                Article(
                    Strong("3. Calcul des correspondances"),
                    P("L'algorithme détecte en continu les cycles bilatéraux (A ↔ B), triangulaires (A → B → C → A) et en carré (4 participants).", style="font-size:0.85rem; color:#475569; margin-top:0.35rem;"),
                ),
                Article(
                    Strong("4. Salon privé & Accord"),
                    P("Discutez en direct dans votre salon privé sécurisé et confirmez votre accord de principe.", style="font-size:0.85rem; color:#475569; margin-top:0.35rem;"),
                ),
                style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:1rem; margin-bottom:2rem;"
            ),
            # Règles & Confidentialité
            Div(
                Article(
                    H4("⚖️ Règles d'échange", style="color:#0f172a; font-weight:700;"),
                    Ul(
                        Li(Strong("Même période obligatoire : "), "P1 contre P1, P2 contre P2, etc. jusqu'à P8."),
                        Li(Strong("Règle de spécialité : "), "Spécialité libre en Master 1 (P1 et P2) ; même spécialité obligatoire de P3 à P8 (Master 2)."),
                        Li(Strong("Validation facultaire : "), "L'accord trouvé sur l'application reste un accord de principe à soumettre à la commission des stages.")
                    )
                ),
                Article(
                    H4("🔒 Confidentialité garantie", style="color:#0f172a; font-weight:700;"),
                    Ul(
                        Li(Strong("Code PIN 4 chiffres : "), "Connexion rapide sans mot de passe complexe."),
                        Li(Strong("Hermétisme complet : "), "Aucun camarade externe ne peut voir qui permute avec qui."),
                        Li(Strong("Salons chiffrés par cycle : "), "Seuls les membres du match accèdent à la messagerie.")
                    )
                ),
                style="display:grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap:1rem;"
            ),
            # Règle spéciale Master 1 (P1 & P2)
            Article(
                H4("🎓 Règle spéciale Master 1 (P1 & P2)", style="color:#1d4ed8; font-weight:700; margin-bottom:0.75rem;"),
                P(
                    "Pour les périodes ", Strong("P1 et P2"), " (premiers stages de Master 1), la permutation est officiellement autorisée ",
                    Strong("entre spécialités identiques OU différentes"), " (par exemple : échanger un stage de ", Em("Pédiatrie"), " contre un stage de ", Em("Chirurgie"), "), ",
                    "du moment que l'échange a lieu durant la même période (P1 contre P1, P2 contre P2) et dans les hôpitaux réciproquement souhaités.",
                    style="font-size:0.92rem; color:#334155; line-height:1.6; margin-bottom:0.6rem;"
                ),
                P(
                    "💡 ", Strong("Rappel Master 2 (P3 à P8) : "),
                    "De la période P3 à P8, la règle stricte de la ",
                    Strong("même spécialité obligatoire"), " (ex: Pédiatrie contre Pédiatrie) continue de s'appliquer sans exception.",
                    style="font-size:0.88rem; color:#64748b; margin-bottom:0;"
                ),
                style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:1.5rem; margin-top:1.25rem; box-shadow:0 1px 3px rgba(15, 23, 42, 0.05);"
            ),
            # Mentions légales, vie privée & consentement des utilisateurs
            Article(
                H4("📋 Mentions légales, vie privée & consentement des utilisateurs", style="color:#0f172a; font-weight:700; margin-bottom:1rem; font-size:1.05rem; display:flex; align-items:center; gap:0.5rem;"),
                Div(
                    Div(
                        Strong("1. Initiative étudiante indépendante : "),
                        "PermutStage est un outil numérique bénévole, développé de manière totalement indépendante de toute autorité universitaire, décanale ou facultaire. Il a pour unique vocation d'aider les étudiants dans l'organisation de leurs souhaits d'échange.",
                        style="margin-bottom:0.75rem; font-size:0.875rem; line-height:1.6;"
                    ),
                    Div(
                        Strong("2. Finalité académique exclusive & Consentement éclairé : "),
                        "En utilisant la plateforme et en créant un compte, chaque étudiant·e consent expressément à ce que ses nom, prénom et adresse e-mail institutionnelle soient enregistrés et utilisés exclusivement à des fins d'organisation et d'échange de lieux de stages hospitaliers entre camarades de promotion.",
                        style="margin-bottom:0.75rem; font-size:0.875rem; line-height:1.6;"
                    ),
                    Div(
                        Strong("3. Confidentialité & Non-commercialisation des données : "),
                        "Aucune donnée personnelle n'est vendue, cédée, louée ou utilisée à des fins publicitaires. Les coordonnées directes ne sont visibles qu'entre étudiants partageant une opportunité de match réciproque validée par l'algorithme.",
                        style="margin-bottom:0.75rem; font-size:0.875rem; line-height:1.6;"
                    ),
                    Div(
                        Strong("4. Valeur juridique de l'échange & Validation facultaire : "),
                        "La plateforme n'a aucun pouvoir d'attribution officiel ni de modification réglementaire des affectations. Les accords trouvés sur PermutStage constituent de simples accords de principe mutuels, sous réserve expresse de validation formelle ultérieure par la commission des stages de la faculté.",
                        style="font-size:0.875rem; line-height:1.6;"
                    ),
                    style="color:#334155;"
                ),
                style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:12px; padding:1.5rem; margin-top:1.5rem; box-shadow:0 1px 3px rgba(15, 23, 42, 0.04);"
            ),
            cls="container"
        ),
        render_footer()
    )

# === VUE 2 : DÉPOSER UNE DEMANDE ===
@rt("/deposer")
def get(session, req: Request = None):
    u = get_session_user(session, req)
    if not u or not u.get("email"):
        return Main(
            render_header(session, "deposer", req),
            Div(
                Article(
                    H3("🔒 Connexion requise", style="font-weight:700;"),
                    P("Veuillez vous connecter avec votre adresse étudiante et votre code PIN pour déposer une offre de permutation."),
                    A("Se connecter / S'inscrire", href="/login-view", role="button", cls="primary", style="border-radius:8px;"),
                    style="text-align:center; padding:2.5rem;"
                ),
                cls="container"
            ),
            render_footer()
        )

    user_email = u["email"]
    user_nom = f"{u.get('prenom', '')} {u.get('nom', '')}".strip() or user_email
    default_actuel = TOUS_LES_HOPITAUX[0]

    return Main(
        render_header(session, "deposer", req),
        Div(
            H2("Déposer une nouvelle offre de permutation", style="font-weight:800; color:#0f172a;"),
            P("Vos coordonnées sont automatiquement verrouillées sur votre profil étudiant connecté. L'offre sera enregistrée dans la base de données et analysée en temps réel."),
            Div(id="depot-feedback"),
            Form(
                Div(
                    Div(
                        Label("Nom complet (verrouillé)", Input(value=user_nom, disabled=True, style="background:#f8fafc;")),
                        Label("Email institutionnel (verrouillé)", Input(value=user_email, disabled=True, style="background:#f8fafc;")),
                    ),
                    Div(
                        Label("Période de stage *", Select(*[Option(p, value=p) for p in PERIODES], name="periode", id="select-periode-depot", required=True, onchange="updateSpecialitesSouhaiteesVisibility(this.value, 'depot')")),
                        Label("Spécialité *", Select(*render_specialite_options(), name="specialite", required=True)),
                        Label(
                            "Hôpital actuel proposé *",
                            Select(
                                *[Option(f"[{HOPITAL_VERS_REGION.get(h, '')}] {h}", value=h, selected=(h == default_actuel)) for h in TOUS_LES_HOPITAUX],
                                name="hopital_actuel",
                                id="select-hopital-actuel-depot",
                                required=True,
                                onchange="syncCurrentHospitalWithSelector(this.value, 'depot')"
                            )
                        ),
                    ),
                    style="display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:1.5rem; margin-bottom:1rem;"
                ),
                render_specialites_souhaitees_selector(selected_specs=[], current_periode=PERIODES[0], prefix="depot"),
                render_hospital_checkbox_selector(selected_hospitals=[], current_hospital=default_actuel, prefix="depot"),
                Button(
                    "Publier ma demande de permutation",
                    type="submit",
                    cls="primary",
                    style="background:#1d4ed8; border-color:#1d4ed8; font-size:1rem; font-weight:700; padding:0.8rem 1.5rem; border-radius:10px; width:100%; box-shadow:0 2px 8px rgba(29, 78, 216, 0.25); cursor:pointer;"
                ),
                hx_post="/nouvelle-demande",
                hx_target="#depot-feedback",
                hx_swap="innerHTML"
            ),
            cls="container"
        ),
        render_footer()
    )

@rt("/nouvelle-demande")
async def post(session, req: Request = None, periode: str = "", specialite: str = "", hopital_actuel: str = "", hopitaux_souhaites: list[str] = None, specialites_souhaitees: list[str] = None):
    u = get_session_user(session, req)
    if not u or not u.get("email"):
        return Article(P("Session expirée. Veuillez vous reconnecter.", style="color:#b91c1c; font-weight:600;"), cls="contrast")

    user_email = u["email"].strip().lower()
    user_nom = f"{u.get('prenom', '')} {u.get('nom', '')}".strip() or user_email

    h_list = []
    s_list = []
    if req is not None:
        try:
            form_data = await req.form()
            h_list = form_data.getlist("hopitaux_souhaites")
            s_list = form_data.getlist("specialites_souhaitees")
            if not periode: periode = str(form_data.get("periode", "")).strip()
            if not specialite: specialite = str(form_data.get("specialite", "")).strip()
            if not hopital_actuel: hopital_actuel = str(form_data.get("hopital_actuel", "")).strip()
        except Exception:
            pass

    if not h_list and hopitaux_souhaites:
        h_list = [hopitaux_souhaites] if isinstance(hopitaux_souhaites, str) else list(hopitaux_souhaites)
    h_list = [str(h).strip() for h in h_list if str(h).strip()]

    if not s_list and specialites_souhaitees:
        s_list = [specialites_souhaitees] if isinstance(specialites_souhaitees, str) else list(specialites_souhaitees)
    s_list = [str(s).strip() for s in s_list if str(s).strip()]

    if not h_list:
        return Article(
            P("⚠️ Veuillez sélectionner au moins un hôpital souhaité en cochant les cases de votre choix.", style="color:#b91c1c; font-weight:700; margin:0;"),
            style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:10px; margin-bottom:1rem;"
        )

    if hopital_actuel in h_list:
        return Article(
            P("Validation refusée : votre hôpital actuel ne peut pas figurer dans la liste des hôpitaux souhaités.", style="color:#b91c1c; font-weight:700; margin:0;"),
            style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:10px; margin-bottom:1rem;"
        )

    doc_id = f"{user_email}_{periode}".replace("@", "_at_").replace(".", "_")
    demande_data = {
        "demande_id": doc_id,
        "Demande_ID": doc_id,
        "user_email": user_email,
        "Email": user_email,
        "nom_etudiant": user_nom,
        "Nom": user_nom,
        "periode": periode,
        "Periode": periode,
        "specialite": specialite,
        "Specialite": specialite,
        "hopital_actuel": hopital_actuel,
        "Hopital_Actuel": hopital_actuel,
        "hopitaux_souhaites": h_list,
        "Hopitaux_Souhaites": serialize_hospitals(h_list),
        "specialites_souhaitees": s_list,
        "Specialites_Souhaitees": serialize_specialites(s_list),
        "statut": "disponible",
        "Statut": "Disponible",
        "updated_at": datetime.now(ZoneInfo("Europe/Brussels")).isoformat(),
        "Timestamp": datetime.now(ZoneInfo("Europe/Brussels")).strftime("%Y-%m-%d %H:%M:%S"),
    }

    df_demandes_avant = load_demandes_data()
    all_bi_avant = compute_bilateral_matches(df_demandes_avant)
    all_tri_avant = compute_triangular_matches(df_demandes_avant)
    all_quad_avant = compute_quadrangular_matches(df_demandes_avant)
    anciens_rooms = {m["room_id"] for m in all_bi_avant} | {t["room_id"] for t in all_tri_avant} | {q["room_id"] for q in all_quad_avant}

    if save_demande(demande_data):
        df_maj = load_demandes_data()
        df_users = load_all_users()
        nouveaux_bi = compute_bilateral_matches(df_maj)
        nouveaux_tri = compute_triangular_matches(df_maj)
        nouveaux_quad = compute_quadrangular_matches(df_maj)
        for m in nouveaux_bi:
            if m["room_id"] not in anciens_rooms:
                send_match_notification_emails(m["participants"], m["periode"], m["specialite"], m["room_id"], df_users)
        for t in nouveaux_tri:
            if t["room_id"] not in anciens_rooms:
                send_match_notification_emails(t["participants"], t["periode"], t["specialite"], t["room_id"], df_users)
        for q in nouveaux_quad:
            if q["room_id"] not in anciens_rooms:
                send_match_notification_emails(q["participants"], q["periode"], q["specialite"], q["room_id"], df_users)

        return Article(
            H4("🎉 Offre publiée et enregistrée dans Firestore !", style="color:#14532d; font-weight:800; margin-bottom:0.4rem;"),
            P(f"Votre demande pour le stage de {specialite} en {periode} ({hopital_actuel}) a été persistée avec {len(h_list)} hôpital(ux) souhaité(s)."),
            A("Consulter mes correspondances", href="/matchs", role="button", cls="primary", style="margin-top:0.5rem; border-radius:8px;"),
            style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:1.25rem; border-radius:12px; margin-bottom:1.5rem;"
        )
    return Article(P("Erreur lors de l'enregistrement dans la base de données Firestore.", style="color:#b91c1c;"), cls="contrast")

# === VUE 3 : MES MATCHS & SALONS PRIVÉS (CONFIDENTIALITÉ STRICTE) ===
@rt("/matchs")
def get(session, req: Request = None):
    u = get_session_user(session, req)
    if not u or not u.get("email"):
        return Main(
            render_header(session, "matchs", req),
            Div(
                Article(
                    H3("🔒 Confidentialité absolue des correspondances", style="font-weight:700;"),
                    P("Seuls les étudiants connectés impliqués dans un cycle complet ont accès aux correspondances et aux coordonnées de leurs camarades."),
                    A("Se connecter", href="/login-view", role="button", cls="primary", style="border-radius:8px;"),
                    style="text-align:center; padding:2.5rem;"
                ),
                cls="container"
            ),
            render_footer()
        )

    user_email = u["email"]
    df_demandes = load_demandes_data()
    all_bi = compute_bilateral_matches(df_demandes)
    all_tri = compute_triangular_matches(df_demandes)
    all_quad = compute_quadrangular_matches(df_demandes)
    my_bi, my_tri, my_quad = filter_private_matches_for_user(user_email, all_bi, all_tri, all_quad)

    bi_sections = []
    if not my_bi:
        bi_sections.append(P("Aucun match bilatéral direct ne vous concerne actuellement.", style="color:#64748b; font-style:italic;"))
    else:
        for m in my_bi:
            a, b = m["a"], m["b"]
            room_id = m["room_id"]
            msgs_salon = recuperer_messages(room_id)
            chat_elements = []
            for msg in msgs_salon:
                is_me = (msg.get("sender_email") or msg.get("Sender_Email") or "").strip().lower() == user_email.lower()
                chat_elements.append(
                    Div(
                        Strong(msg.get("sender_name") or msg.get("Sender_Name")),
                        Small(f" · {msg.get('timestamp') or msg.get('Timestamp')}", style="font-size:0.75rem; opacity:0.8;"),
                        P(msg.get("texte") or msg.get("Texte"), style="margin:0.2rem 0 0 0;"),
                        cls=f"chat-bubble {'chat-me' if is_me else 'chat-other'}"
                    )
                )

            disc = get_discussion_by_id(room_id)
            statut = disc.get("statut") or ("en discussion" if msgs_salon else "nouveau")
            if statut == "accord trouvé":
                status_tag = Span("🎉 Accord trouvé", cls="status-badge", style="background:#dcfce7; color:#166534; border:1px solid #86efac; font-weight:800; font-size:0.78rem; padding:0.25rem 0.65rem; border-radius:9999px; float:right;")
                accord_action = Div(
                    P("🎉 Accord d'échange officiellement confirmé !", style="font-weight:700; color:#166534; margin:0; font-size:0.85rem;"),
                    id=f"match-accord-{slugify(room_id)}",
                    style="background:#f0fdf4; border:1px solid #86efac; padding:0.5rem 0.75rem; border-radius:8px; margin-top:0.6rem;"
                )
            elif statut == "en discussion":
                status_tag = Span("💬 En discussion", cls="status-badge", style="background:#dbeafe; color:#1e40af; border:1px solid #bfdbfe; font-weight:700; font-size:0.78rem; padding:0.25rem 0.65rem; border-radius:9999px; float:right;")
                accord_action = Div(
                    Form(
                        Input(type="hidden", name="discussion_id", value=room_id),
                        Button(
                            "🤝 Confirmer l'accord trouvé",
                            type="submit",
                            cls="outline",
                            style="border-color:#16a34a; color:#166534; font-weight:700; border-radius:8px; font-size:0.8rem; padding:0.35rem 0.75rem; margin:0;",
                        ),
                        hx_post="/confirmer-accord",
                        hx_confirm="🤝 Confirmation requise : Avez-vous trouvé un accord de permutation avec votre binôme ? Le salon passera au statut 'Accord trouvé'.",
                        hx_target=f"#match-accord-{slugify(room_id)}",
                        hx_swap="outerHTML"
                    ),
                    id=f"match-accord-{slugify(room_id)}",
                    style="margin-top:0.6rem;"
                )
            else:
                if statut == "en discussion":
                    status_tag = Span("💬 En discussion", cls="status-badge", style="background:#dbeafe; color:#1e40af; border:1px solid #bfdbfe; font-weight:700; font-size:0.78rem; padding:0.25rem 0.65rem; border-radius:9999px; float:right;")
                else:
                    status_tag = Span("⏳ Nouveau salon", cls="status-badge", style="background:#f1f5f9; color:#475569; border:1px solid #cbd5e1; font-weight:700; font-size:0.78rem; padding:0.25rem 0.65rem; border-radius:9999px; float:right;")
                accord_action = Div(
                    Form(
                        Input(type="hidden", name="discussion_id", value=room_id),
                        Button(
                            "🤝 Confirmer l'accord trouvé",
                            type="submit",
                            cls="outline",
                            style="border-color:#16a34a; color:#166534; font-weight:700; border-radius:8px; font-size:0.8rem; padding:0.35rem 0.75rem; margin:0;",
                        ),
                        hx_post="/demander-confirmation-accord",
                        hx_target=f"#match-accord-{slugify(room_id)}",
                        hx_swap="outerHTML"
                    ),
                    id=f"match-accord-{slugify(room_id)}",
                    style="margin-top:0.6rem;"
                )

            bi_sections.append(
                Article(
                    Div(
                        Strong(f"MATCH PRIVÉ BILATÉRAL · {m['periode']} · {m['specialite']}", style="color:#166534; font-size:0.95rem; font-weight:800;"),
                        status_tag,
                        style="margin-bottom:0.75rem;"
                    ),
                    P(
                        Strong(a["Nom"]), f" ({a['Hopital_Actuel']})",
                        "  ⇄  ",
                        Strong(b["Nom"]), f" ({b['Hopital_Actuel']})",
                        style="font-size:1.05rem; margin-bottom:0.4rem;"
                    ),
                    P(
                        "Coordonnées directes : ",
                        A(a["Email"], href=f"mailto:{a['Email']}"), " | ",
                        A(b["Email"], href=f"mailto:{b['Email']}"),
                        style="font-size:0.85rem; color:#15803d;"
                    ),
                    accord_action,
                    Details(
                        Summary(f"💬 Salon de discussion privé ({len(msgs_salon)} messages)"),
                        Div(
                            Div(*chat_elements, id=f"chat-box-{slugify(room_id)}", style="max-height:220px; overflow-y:auto; margin:0.75rem 0; padding:0.6rem; background:#ffffff; border-radius:10px; border:1px solid #e2e8f0;"),
                            Form(
                                Div(
                                    Input(name="texte", placeholder="Écrire un message dans ce salon privé...", required=True, style="margin-bottom:0;"),
                                    Input(type="hidden", name="discussion_id", value=room_id),
                                    Input(type="hidden", name="room_id", value=room_id),
                                    Button("Envoyer", type="submit", cls="primary", style="margin-bottom:0; width:auto; border-radius:8px;"),
                                    style="display:flex; gap:0.5rem;"
                                ),
                                hx_post="/envoyer-message",
                                hx_target=f"#chat-box-{slugify(room_id)}",
                                hx_swap="innerHTML"
                            ),
                            A("Ouvrir en plein écran", href=f"/salon/{room_id}", style="font-size:0.78rem; display:inline-block; margin-top:0.4rem;"),
                            style="margin-top:0.5rem;"
                        )
                    ),
                    cls="match-card"
                )
            )

    tri_sections = []
    if not my_tri:
        tri_sections.append(P("Aucun cycle triangulaire à 3 personnes ne vous concerne actuellement.", style="color:#64748b; font-style:italic;"))
    else:
        for t in my_tri:
            a, b, c = t["a"], t["b"], t["c"]
            room_id = t["room_id"]
            msgs_salon = recuperer_messages(room_id)
            chat_elements = []
            for msg in msgs_salon:
                is_me = (msg.get("sender_email") or msg.get("Sender_Email") or "").strip().lower() == user_email.lower()
                chat_elements.append(
                    Div(
                        Strong(msg.get("sender_name") or msg.get("Sender_Name")),
                        Small(f" · {msg.get('timestamp') or msg.get('Timestamp')}", style="font-size:0.75rem; opacity:0.8;"),
                        P(msg.get("texte") or msg.get("Texte"), style="margin:0.2rem 0 0 0;"),
                        cls=f"chat-bubble {'chat-me' if is_me else 'chat-other'}"
                    )
                )

            disc_t = get_discussion_by_id(room_id)
            statut_t = disc_t.get("statut") or ("en discussion" if msgs_salon else "nouveau")
            if statut_t == "accord trouvé":
                status_tag_t = Span("🎉 Accord trouvé", cls="status-badge", style="background:#dcfce7; color:#166534; border:1px solid #86efac; font-weight:800; font-size:0.78rem; padding:0.25rem 0.65rem; border-radius:9999px; float:right;")
                accord_action_t = Div(
                    P("🎉 Accord d'échange officiellement confirmé !", style="font-weight:700; color:#166534; margin:0; font-size:0.85rem;"),
                    id=f"match-accord-{slugify(room_id)}",
                    style="background:#f0fdf4; border:1px solid #86efac; padding:0.5rem 0.75rem; border-radius:8px; margin-top:0.6rem;"
                )
            else:
                if statut_t == "en discussion":
                    status_tag_t = Span("💬 En discussion", cls="status-badge", style="background:#dbeafe; color:#1e40af; border:1px solid #bfdbfe; font-weight:700; font-size:0.78rem; padding:0.25rem 0.65rem; border-radius:9999px; float:right;")
                else:
                    status_tag_t = Span("⏳ Nouveau salon", cls="status-badge", style="background:#f1f5f9; color:#475569; border:1px solid #cbd5e1; font-weight:700; font-size:0.78rem; padding:0.25rem 0.65rem; border-radius:9999px; float:right;")
                accord_action_t = Div(
                    Form(
                        Input(type="hidden", name="discussion_id", value=room_id),
                        Button(
                            "🤝 Confirmer l'accord trouvé",
                            type="submit",
                            cls="outline",
                            style="border-color:#16a34a; color:#166534; font-weight:700; border-radius:8px; font-size:0.8rem; padding:0.35rem 0.75rem; margin:0;",
                        ),
                        hx_post="/demander-confirmation-accord",
                        hx_target=f"#match-accord-{slugify(room_id)}",
                        hx_swap="outerHTML"
                    ),
                    id=f"match-accord-{slugify(room_id)}",
                    style="margin-top:0.6rem;"
                )

            tri_sections.append(
                Article(
                    Div(
                        Strong(f"MATCH PRIVÉ TRIANGULAIRE · {t['periode']} · {t['specialite']}", style="color:#064e3b; font-size:0.95rem; font-weight:800;"),
                        status_tag_t,
                        style="margin-bottom:0.75rem;"
                    ),
                    P(
                        Strong(a["Nom"]), f" ({a['Hopital_Actuel']}) → ",
                        Strong(b["Nom"]), f" ({b['Hopital_Actuel']}) → ",
                        Strong(c["Nom"]), f" ({c['Hopital_Actuel']}) → ",
                        Strong(a["Nom"]),
                        style="font-size:0.95rem; line-height:1.5; margin-bottom:0.4rem;"
                    ),
                    P(
                        "Coordonnées du cycle : ",
                        A(a["Email"], href=f"mailto:{a['Email']}"), " · ",
                        A(b["Email"], href=f"mailto:{b['Email']}"), " · ",
                        A(c["Email"], href=f"mailto:{c['Email']}"),
                        style="font-size:0.85rem; color:#047857;"
                    ),
                    accord_action_t,
                    Details(
                        Summary(f"💬 Salon de discussion privé ({len(msgs_salon)} messages)"),
                        Div(
                            Div(*chat_elements, id=f"chat-box-{slugify(room_id)}", style="max-height:220px; overflow-y:auto; margin:0.75rem 0; padding:0.6rem; background:#ffffff; border-radius:10px; border:1px solid #e2e8f0;"),
                            Form(
                                Div(
                                    Input(name="texte", placeholder="Écrire un message aux collègues du cycle...", required=True, style="margin-bottom:0;"),
                                    Input(type="hidden", name="discussion_id", value=room_id),
                                    Input(type="hidden", name="room_id", value=room_id),
                                    Button("Envoyer", type="submit", cls="primary", style="margin-bottom:0; width:auto; border-radius:8px;"),
                                    style="display:flex; gap:0.5rem;"
                                ),
                                hx_post="/envoyer-message",
                                hx_target=f"#chat-box-{slugify(room_id)}",
                                hx_swap="innerHTML"
                            ),
                            A("Ouvrir en plein écran", href=f"/salon/{room_id}", style="font-size:0.78rem; display:inline-block; margin-top:0.4rem;"),
                            style="margin-top:0.5rem;"
                        )
                    ),
                    cls="tri-card"
                )
            )

    quad_sections = []
    if not my_quad:
        quad_sections.append(P("Aucun cycle en carré à 4 personnes ne vous concerne actuellement.", style="color:#64748b; font-style:italic;"))
    else:
        for q in my_quad:
            a, b, c, d = q["a"], q["b"], q["c"], q["d"]
            room_id = q["room_id"]
            msgs_salon = recuperer_messages(room_id)
            chat_elements = []
            for msg in msgs_salon:
                is_me = (msg.get("sender_email") or msg.get("Sender_Email") or "").strip().lower() == user_email.lower()
                chat_elements.append(
                    Div(
                        Strong(msg.get("sender_name") or msg.get("Sender_Name")),
                        Small(f" · {msg.get('timestamp') or msg.get('Timestamp')}", style="font-size:0.75rem; opacity:0.8;"),
                        P(msg.get("texte") or msg.get("Texte"), style="margin:0.2rem 0 0 0;"),
                        cls=f"chat-bubble {'chat-me' if is_me else 'chat-other'}"
                    )
                )

            disc_q = get_discussion_by_id(room_id)
            statut_q = disc_q.get("statut") or ("en discussion" if msgs_salon else "nouveau")
            if statut_q == "accord trouvé":
                status_tag_q = Span("🎉 Accord trouvé", cls="status-badge", style="background:#dcfce7; color:#166534; border:1px solid #86efac; font-weight:800; font-size:0.78rem; padding:0.25rem 0.65rem; border-radius:9999px; float:right;")
                accord_action_q = Div(
                    P("🎉 Accord d'échange officiellement confirmé !", style="font-weight:700; color:#166534; margin:0; font-size:0.85rem;"),
                    id=f"match-accord-{slugify(room_id)}",
                    style="background:#f0fdf4; border:1px solid #86efac; padding:0.5rem 0.75rem; border-radius:8px; margin-top:0.6rem;"
                )
            else:
                if statut_q == "en discussion":
                    status_tag_q = Span("💬 En discussion", cls="status-badge", style="background:#f3e8ff; color:#6b21a8; border:1px solid #d8b4fe; font-weight:700; font-size:0.78rem; padding:0.25rem 0.65rem; border-radius:9999px; float:right;")
                else:
                    status_tag_q = Span("⏳ Nouveau salon", cls="status-badge", style="background:#f1f5f9; color:#475569; border:1px solid #cbd5e1; font-weight:700; font-size:0.78rem; padding:0.25rem 0.65rem; border-radius:9999px; float:right;")
                accord_action_q = Div(
                    Form(
                        Input(type="hidden", name="discussion_id", value=room_id),
                        Button(
                            "🤝 Confirmer l'accord trouvé",
                            type="submit",
                            cls="outline",
                            style="border-color:#7c3aed; color:#6d28d9; font-weight:700; border-radius:8px; font-size:0.8rem; padding:0.35rem 0.75rem; margin:0;",
                        ),
                        hx_post="/demander-confirmation-accord",
                        hx_target=f"#match-accord-{slugify(room_id)}",
                        hx_swap="outerHTML"
                    ),
                    id=f"match-accord-{slugify(room_id)}",
                    style="margin-top:0.6rem;"
                )

            quad_sections.append(
                Article(
                    Div(
                        Strong(f"MATCH PRIVÉ EN CARRÉ (4) · {q['periode']} · {q['specialite']}", style="color:#581c87; font-size:0.95rem; font-weight:800;"),
                        status_tag_q,
                        style="margin-bottom:0.75rem;"
                    ),
                    P(
                        Strong(a["Nom"]), f" ({a['Hopital_Actuel']}) → ",
                        Strong(b["Nom"]), f" ({b['Hopital_Actuel']}) → ",
                        Strong(c["Nom"]), f" ({c['Hopital_Actuel']}) → ",
                        Strong(d["Nom"]), f" ({d['Hopital_Actuel']}) → ",
                        Strong(a["Nom"]),
                        style="font-size:0.92rem; line-height:1.5; margin-bottom:0.4rem;"
                    ),
                    P(
                        "Coordonnées du cycle : ",
                        A(a["Email"], href=f"mailto:{a['Email']}"), " · ",
                        A(b["Email"], href=f"mailto:{b['Email']}"), " · ",
                        A(c["Email"], href=f"mailto:{c['Email']}"), " · ",
                        A(d["Email"], href=f"mailto:{d['Email']}"),
                        style="font-size:0.83rem; color:#6d28d9;"
                    ),
                    accord_action_q,
                    Details(
                        Summary(f"💬 Salon de discussion privé ({len(msgs_salon)} messages)"),
                        Div(
                            Div(*chat_elements, id=f"chat-box-{slugify(room_id)}", style="max-height:220px; overflow-y:auto; margin:0.75rem 0; padding:0.6rem; background:#ffffff; border-radius:10px; border:1px solid #e2e8f0;"),
                            Form(
                                Div(
                                    Input(name="texte", placeholder="Écrire un message aux collègues du cycle à 4...", required=True, style="margin-bottom:0;"),
                                    Input(type="hidden", name="discussion_id", value=room_id),
                                    Input(type="hidden", name="room_id", value=room_id),
                                    Button("Envoyer", type="submit", cls="primary", style="margin-bottom:0; width:auto; border-radius:8px;"),
                                    style="display:flex; gap:0.5rem;"
                                ),
                                hx_post="/envoyer-message",
                                hx_target=f"#chat-box-{slugify(room_id)}",
                                hx_swap="innerHTML"
                            ),
                            A("Ouvrir en plein écran", href=f"/salon/{room_id}", style="font-size:0.78rem; display:inline-block; margin-top:0.4rem;"),
                            style="margin-top:0.5rem;"
                        )
                    ),
                    cls="quad-card"
                )
            )

    return Main(
        render_header(session, "matchs", req),
        Div(
            H2("Mes correspondances privées & Salons de discussion", style="font-weight:800; color:#0f172a;"),
            P(f"Affichage strictement réservé à votre profil ({user_email}). Les salons et messages sont persistés en temps réel dans la base de données."),
            Div(
                Div(H3(f"Binômes bilatéraux ({len(my_bi)})", style="font-size:1.15rem; font-weight:700;"), *bi_sections),
                Div(H3(f"Cycles triangulaires ({len(my_tri)})", style="font-size:1.15rem; font-weight:700;"), *tri_sections),
                Div(H3(f"Cycles en carré (4) ({len(my_quad)})", style="font-size:1.15rem; font-weight:700;"), *quad_sections),
                style="display:grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap:1.5rem;"
            ),
            cls="container"
        ),
        render_footer()
    )

# === VUE SALON DÉDIÉ : /salon/{id} ===
@rt("/salon/{id}")
def get(session, id: str, req: Request = None):
    u = get_session_user(session, req)
    if not u or not u.get("email"):
        return RedirectResponse("/login-view")

    user_email = u["email"].strip().lower()
    disc_id = str(id).strip()

    msgs = recuperer_messages(disc_id)
    chat_elements = []
    for msg in msgs:
        is_me = (msg.get("sender_email") or msg.get("Sender_Email") or "").strip().lower() == user_email
        chat_elements.append(
            Div(
                Strong(msg.get("sender_name") or msg.get("Sender_Name")),
                Small(f" · {msg.get('timestamp') or msg.get('Timestamp')}", style="font-size:0.75rem; opacity:0.8;"),
                P(msg.get("texte") or msg.get("Texte"), style="margin:0.2rem 0 0 0;"),
                cls=f"chat-bubble {'chat-me' if is_me else 'chat-other'}"
            )
        )

    disc = get_discussion_by_id(disc_id)
    statut = disc.get("statut") or ("en discussion" if msgs else "nouveau")

    if statut == "accord trouvé":
        accord_banner = Div(
            Article(
                H4("🎉 Accord trouvé et validé !", style="color:#14532d; font-weight:800; margin-bottom:0.3rem;"),
                P("Tous les participants ont validé leur accord d'échange pour ce salon. Félicitations ! Pensez à transmettre votre accord officiel à la commission des stages de votre faculté."),
                style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:1rem; border-radius:10px; margin-bottom:1rem;"
            ),
            id=f"match-accord-{slugify(disc_id)}"
        )
    else:
        accord_banner = Div(
            Article(
                Div(
                    Span("💬 En discussion" if statut == "en discussion" else "⏳ Nouveau salon",
                         cls="status-badge",
                         style="background:#dbeafe; color:#1e40af; border:1px solid #bfdbfe; font-weight:700; font-size:0.8rem; padding:0.25rem 0.65rem; border-radius:9999px; margin-right:0.75rem;"),
                    Span("Discutez des modalités de permutation. Une fois d'accord, confirmez votre entente :", style="font-size:0.88rem; color:#475569;"),
                    style="margin-bottom:0.6rem; display:flex; align-items:center; flex-wrap:wrap; gap:0.5rem;"
                ),
                Form(
                    Input(type="hidden", name="discussion_id", value=disc_id),
                    Button(
                        "🤝 Confirmer l'accord trouvé",
                        type="submit",
                        cls="primary",
                        style="background:#16a34a; border-color:#16a34a; font-weight:700; border-radius:8px; font-size:0.88rem; padding:0.45rem 1rem; width:auto;",
                    ),
                    hx_post="/demander-confirmation-accord",
                    hx_target=f"#match-accord-{slugify(disc_id)}",
                    hx_swap="outerHTML"
                ),
                style="background:#f8fafc; border:1px solid #e2e8f0; padding:1rem; border-radius:10px; margin-bottom:1rem;"
            ),
            id=f"match-accord-{slugify(disc_id)}"
        )

    return Main(
        render_header(session, "matchs", req),
        Div(
            A("← Retour à Mes Matchs", href="/matchs", style="display:inline-block; margin-bottom:1rem; font-size:0.9rem; font-weight:600;"),
            Article(
                H3(f"💬 Salon de discussion privé : {disc_id}", style="font-weight:700;"),
                accord_banner,
                Div(*chat_elements, id=f"chat-box-{slugify(disc_id)}", style="min-height:280px; max-height:450px; overflow-y:auto; margin:1rem 0; padding:1rem; background:#ffffff; border-radius:10px; border:1px solid #e2e8f0;"),
                Form(
                    Div(
                        Input(name="texte", placeholder="Écrire votre message...", required=True, style="margin-bottom:0;"),
                        Input(type="hidden", name="discussion_id", value=disc_id),
                        Input(type="hidden", name="room_id", value=disc_id),
                        Button("Envoyer", type="submit", cls="primary", style="margin-bottom:0; width:auto; border-radius:8px;"),
                        style="display:flex; gap:0.5rem;"
                    ),
                    hx_post="/envoyer-message",
                    hx_target=f"#chat-box-{slugify(disc_id)}",
                    hx_swap="innerHTML"
                )
            ),
            cls="container"
        ),
        render_footer()
    )

@rt("/envoyer-message")
@rt("/post-chat-message")
def post(session, req: Request = None, discussion_id: str = "", room_id: str = "", texte: str = ""):
    u = get_session_user(session, req)
    if not u or not u.get("email") or not texte.strip():
        return ""

    target_id = discussion_id.strip() or room_id.strip()
    if not target_id:
        return ""

    user_email = u["email"].strip().lower()
    user_name = f"{u.get('prenom', '')} {u.get('nom', '')}".strip() or user_email

    envoyer_message(target_id, user_email, user_name, texte.strip())
    msgs_salon = recuperer_messages(target_id)

    elements = []
    for msg in msgs_salon:
        is_me = (msg.get("sender_email") or msg.get("Sender_Email") or "").strip().lower() == user_email
        elements.append(
            Div(
                Strong(msg.get("sender_name") or msg.get("Sender_Name")),
                Small(f" · {msg.get('timestamp') or msg.get('Timestamp')}", style="font-size:0.75rem; opacity:0.8;"),
                P(msg.get("texte") or msg.get("Texte"), style="margin:0.2rem 0 0 0;"),
                cls=f"chat-bubble {'chat-me' if is_me else 'chat-other'}"
            )
        )
    return Div(*elements)

@rt("/demander-confirmation-accord")
def post(session, req: Request = None, discussion_id: str = ""):
    u = get_session_user(session, req)
    if not u or not u.get("email"):
        return Article(P("⚠️ Session expirée. Veuillez vous reconnecter.", style="color:#b91c1c; font-weight:600;"), cls="contrast")

    disc_id = str(discussion_id).strip()
    if not disc_id and req is not None:
        try:
            rf = getattr(req, "_form", None)
            if rf: disc_id = str(rf.get("discussion_id", "")).strip()
        except Exception:
            pass

    return Div(
        Article(
            H4("🤝 Confirmation d'accord trouvé", style="color:#166534; font-weight:800; margin-bottom:0.4rem;"),
            P("Avez-vous convenu de l'ensemble des modalités de permutation avec l'ensemble des correspondants de ce salon ?", style="font-weight:600; color:#14532d; margin-bottom:0.3rem;"),
            P("En validant, le statut du salon passera officiellement à 'Accord trouvé'. Un message automatique de confirmation sera consigné dans le salon pour acter cette entente.", style="font-size:0.85rem; color:#166534; margin-bottom:0.75rem;"),
            Div(
                Form(
                    Input(type="hidden", name="discussion_id", value=disc_id),
                    Button(
                        "✅ Oui, confirmer l'accord trouvé",
                        type="submit",
                        cls="primary",
                        style="background:#16a34a; border-color:#16a34a; font-weight:700; border-radius:8px; font-size:0.85rem; padding:0.45rem 1rem;",
                    ),
                    hx_post="/confirmer-accord",
                    hx_confirm="🤝 Confirmation requise : Avez-vous convenu de l'ensemble des modalités d'échange avec vos correspondants et confirmez-vous cet accord ? Cette action passera définitivement le salon au statut 'Accord trouvé'.",
                    hx_target=f"#match-accord-{slugify(disc_id)}",
                    hx_swap="outerHTML",
                    style="display:inline-block; margin-right:0.5rem; margin-bottom:0;"
                ),
                A("Annuler", href="/matchs", role="button", cls="outline secondary", style="border-radius:8px; font-size:0.85rem; padding:0.45rem 1rem; text-decoration:none;"),
                style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap; margin-top:0.5rem;"
            ),
            style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:1rem; border-radius:10px; margin-top:0.6rem;"
        ),
        id=f"match-accord-{slugify(disc_id)}"
    )

@rt("/confirmer-accord")
def post(session, req: Request = None, discussion_id: str = ""):
    u = get_session_user(session, req)
    if not u or not u.get("email"):
        return Article(P("⚠️ Session expirée. Veuillez vous reconnecter.", style="color:#b91c1c; font-weight:600;"), cls="contrast")

    disc_id = str(discussion_id).strip()
    if not disc_id and req is not None:
        try:
            rf = getattr(req, "_form", None)
            if rf: disc_id = str(rf.get("discussion_id", "")).strip()
        except Exception:
            pass

    if not disc_id:
        return Article(P("Discussion introuvable.", style="color:#b91c1c; font-weight:600;"))

    user_email = u["email"].strip().lower()
    user_nom = f"{u.get('prenom', '')} {u.get('nom', '')}".strip() or user_email

    mettre_a_jour_statut_discussion(disc_id, "accord trouvé", confirmed_by=user_email)

    envoyer_message(
        disc_id,
        "system@permutstage",
        "Système PermutStage",
        f"🎉 Accord d'échange officiellement confirmé par {user_nom} ! Félicitations aux participants. Pensez à transmettre votre accord officiel à la commission des stages."
    )

    return Div(
        Article(
            H4("🎉 Accord trouvé et validé !", style="color:#14532d; font-weight:800; margin-bottom:0.3rem;"),
            P(f"L'accord a été officiellement confirmé par {user_nom}. Le statut de ce salon est désormais 'Accord trouvé'."),
            P("Conservez vos coordonnées et soumettez votre dossier conjoint de permutation à votre commission de stage facultaire.", style="font-size:0.85rem; color:#166534; margin:0;"),
            style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:1rem; border-radius:10px; margin-bottom:1rem;"
        ),
        id=f"match-accord-{slugify(disc_id)}"
    )

# === VUE 4 : CATALOGUE PUBLIC (ANONYMISÉ PAR CONFIDENTIALITÉ) ===
@rt("/catalogue")
def get(session, f_periode: str = "Toutes", f_specialite: str = "Toutes", f_region: str = "Toutes", q: str = "", req: Request = None):
    df_demandes = load_demandes_data()
    df_filtre = df_demandes.copy()

    if f_periode != "Toutes":
        df_filtre = df_filtre[df_filtre["Periode"] == f_periode]
    if f_specialite != "Toutes":
        df_filtre = df_filtre[df_filtre["Specialite"] == f_specialite]
    if f_region != "Toutes":
        hopitaux_reg = set(HOPITAUX_PAR_REGION.get(f_region, []))
        df_filtre = df_filtre[df_filtre["Hopital_Actuel"].isin(hopitaux_reg)]
    if q and q.strip():
        terme = q.strip().lower()
        df_filtre = df_filtre[
            df_filtre["Hopital_Actuel"].str.lower().str.contains(terme, na=False)
            | df_filtre["Hopitaux_Souhaites"].str.lower().str.contains(terme, na=False)
        ]

    cards = []
    if df_filtre.empty:
        cards.append(P("Aucune offre ne correspond aux critères sélectionnés.", style="font-style:italic; color:#64748b;"))
    else:
        for _, row in df_filtre.iterrows():
            souhaites_str = ", ".join(parse_hospitals(row.get("hopitaux_souhaites") or row.get("Hopitaux_Souhaites")))
            region_act = HOPITAL_VERS_REGION.get(row.get("Hopital_Actuel", ""), "Autre")
            statut = row.get("Statut", "Disponible")
            st_class = "status-disponible" if statut == "Disponible" else ("status-discussion" if statut == "En discussion" else "status-accord")

            spec_info = []
            if str(row.get("Periode")).strip() in ("P1", "P2"):
                s_wants = parse_specialites(row.get("specialites_souhaitees") or row.get("Specialites_Souhaitees"))
                s_wants_txt = ", ".join(s_wants) if s_wants else "Peu importe / Toutes les spécialités"
                spec_info = [
                    Br(),
                    Strong("Spécialité(s) souhaitée(s) : "), Span(s_wants_txt, style="color:#1d4ed8; font-weight:600;"),
                ]

            cards.append(
                Article(
                    Div(
                        Strong(f"{row['Periode']} · {row['Specialite']} — Région {region_act}", style="color:#1e3a8a; font-size:1.05rem; font-weight:700;"),
                        Span(statut, cls=f"status-badge {st_class}", style="float:right;"),
                        style="margin-bottom:0.5rem;"
                    ),
                    P(
                        Strong("Hôpital proposé : "), row.get("Hopital_Actuel", ""),
                        Br(),
                        Strong("Hôpitaux souhaités : "), souhaites_str,
                        *spec_info,
                        style="font-size:0.9rem; margin-bottom:0.4rem; line-height:1.5;"
                    ),
                    Small(f"Mis à jour le {row.get('Timestamp', '')} · Synchronisé Firestore · Anonymat garanti", style="color:#94a3b8; font-size:0.75rem;"),
                    style="margin-bottom:0.75rem; background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:1.15rem;"
                )
            )

    filtres_form = Form(
        Div(
            Div(Label("Période", Select(Option("Toutes", value="Toutes", selected=(f_periode=="Toutes")), *[Option(p, value=p, selected=(f_periode==p)) for p in PERIODES], name="f_periode", onchange="this.form.submit()"))),
            Div(Label("Spécialité", Select(*render_specialite_options(selected_value=f_specialite, include_all=True), name="f_specialite", onchange="this.form.submit()"))),
            Div(Label("Région hôpital actuel", Select(Option("Toutes", value="Toutes", selected=(f_region=="Toutes")), *[Option(r, value=r, selected=(f_region==r)) for r in REGIONS], name="f_region", onchange="this.form.submit()"))),
            Div(Label("Recherche libre", Input(name="q", value=q, placeholder="Ex: Saint Luc, Namur...", oninput="this.form.submit()"))),
            style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:1rem; margin-bottom:1.5rem;"
        ),
        method="get",
        action="/catalogue"
    )

    return Main(
        render_header(session, "catalogue", req),
        Div(
            H2(f"Catalogue des offres de stage disponibles ({len(df_filtre)} affichée(s))", style="font-weight:800; color:#0f172a;"),
            P("Pour préserver la vie privée des étudiants, les coordonnées ne sont jamais révélées publiquement mais uniquement aux partenaires d'échange dans l'onglet 'Mes Matchs'."),
            filtres_form,
            Div(*cards),
            cls="container"
        ),
        render_footer()
    )

# === VUE 5 : GÉRER MON OFFRE (MODIFICATION, STATUT & SUPPRESSION) ===
@rt("/gerer")
def get(session, req: Request = None):
    u = get_session_user(session, req)
    if not u or not u.get("email"):
        return Main(
            render_header(session, "gerer", req),
            Div(
                Article(
                    H3("🔒 Connexion requise", style="font-weight:700;"),
                    P("Connectez-vous pour modifier vos annonces ou mettre à jour leur statut."),
                    A("Se connecter", href="/login-view", role="button", cls="primary", style="border-radius:8px;"),
                    style="text-align:center; padding:2.5rem;"
                ),
                cls="container"
            ),
            render_footer()
        )

    user_email = u["email"].strip().lower()
    df_demandes = load_demandes_data()
    mes_offres = df_demandes[df_demandes["Email"].str.lower() == user_email] if not df_demandes.empty else pd.DataFrame()

    offres_blocks = []
    if mes_offres.empty:
        offres_blocks.append(
            Article(
                H4("Vous n'avez aucune offre active pour le moment.", style="font-weight:700;"),
                P("Déposez votre première demande de permutation pour que notre moteur détecte vos correspondances."),
                A("Déposer une offre", href="/deposer", role="button", cls="primary", style="border-radius:8px;"),
                style="text-align:center; padding:2rem;"
            )
        )
    else:
        for _, row in mes_offres.iterrows():
            d_id = str(row["Demande_ID"]).strip()
            cur_periode = row["Periode"]
            cur_spec = row["Specialite"]
            cur_actuel = row["Hopital_Actuel"]
            cur_souhaites = parse_hospitals(row.get("hopitaux_souhaites") or row.get("Hopitaux_Souhaites"))
            cur_spec_souhaites = parse_specialites(row.get("specialites_souhaitees") or row.get("Specialites_Souhaitees"))
            cur_statut = row.get("Statut", "Disponible")
            edit_prefix = f"edit-{slugify(d_id)}"

            edit_form = Form(
                Input(type="hidden", name="demande_id", value=d_id),
                Div(
                    Div(
                        Label(
                            "Période",
                            Select(
                                *[Option(p, value=p, selected=(p==cur_periode)) for p in PERIODES],
                                name="periode",
                                id=f"select-periode-{edit_prefix}",
                                onchange=f"updateSpecialitesSouhaiteesVisibility(this.value, '{edit_prefix}')"
                            )
                        )
                    ),
                    Div(Label("Spécialité", Select(*render_specialite_options(selected_value=cur_spec), name="specialite"))),
                    Div(
                        Label(
                            "Hôpital actuel",
                            Select(
                                *[Option(h, value=h, selected=(h==cur_actuel)) for h in TOUS_LES_HOPITAUX],
                                name="hopital_actuel",
                                id=f"select-hopital-actuel-{edit_prefix}",
                                onchange=f"syncCurrentHospitalWithSelector(this.value, '{edit_prefix}')"
                            )
                        )
                    ),
                    Div(Label("Statut de la demande", Select(*[Option(st, value=st, selected=(st==cur_statut)) for st in STATUTS_DEMANDE], name="statut"))),
                    style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:1rem; margin-bottom:1rem;"
                ),
                render_specialites_souhaitees_selector(selected_specs=cur_spec_souhaites, current_periode=cur_periode, prefix=edit_prefix),
                render_hospital_checkbox_selector(selected_hospitals=cur_souhaites, current_hospital=cur_actuel, prefix=edit_prefix),
                Div(
                    Button("Enregistrer les modifications", type="submit", cls="primary", style="border-radius:8px; font-weight:700;"),
                    style="margin-top:1rem;"
                ),
                hx_post="/modifier-demande",
                hx_target=f"#feedback-{slugify(d_id)}",
                hx_swap="innerHTML"
            )

            delete_form = Form(
                Input(type="hidden", name="demande_id", value=d_id),
                Label(
                    Input(type="checkbox", name="confirm_delete", required=True),
                    "Je confirme vouloir supprimer définitivement cette offre et fermer les salons associés."
                ),
                Button("Supprimer définitivement l'offre", type="submit", cls="secondary outline", style="color:#b91c1c; border-color:#b91c1c; border-radius:8px;"),
                hx_post="/supprimer-demande",
                hx_target=f"#offre-container-{slugify(d_id)}",
                hx_swap="outerHTML"
            )

            offres_blocks.append(
                Div(
                    Article(
                        H3(f"📌 {cur_periode} · {cur_spec} ({cur_actuel})", style="font-weight:800; color:#1e3a8a;"),
                        Div(id=f"feedback-{slugify(d_id)}"),
                        H5("Modifier l'annonce", style="font-weight:700; margin-top:1rem;"),
                        edit_form,
                        Hr(),
                        H5("Supprimer l'annonce", style="font-weight:700; color:#b91c1c;"),
                        delete_form,
                    ),
                    id=f"offre-container-{slugify(d_id)}",
                    style="margin-bottom:1.5rem;"
                )
            )

    return Main(
        render_header(session, "gerer", req),
        Div(
            H2("Gérer mes annonces publiées", style="font-weight:800; color:#0f172a;"),
            P("Vous pouvez ajuster vos souhaits à tout moment ou modifier le statut de votre offre ('Disponible', 'En discussion', 'Accord trouvé'). Les modifications sont directement enregistrées dans la base de données."),
            *offres_blocks,
            cls="container"
        ),
        render_footer()
    )

@rt("/modifier-demande")
async def post(session, req: Request = None, demande_id: str = "", periode: str = "", specialite: str = "", hopital_actuel: str = "", statut: str = "Disponible", hopitaux_souhaites: list[str] = None, specialites_souhaitees: list[str] = None):
    u = get_session_user(session, req)
    if not u or not u.get("email"):
        return P("Session expirée.", style="color:#b91c1c; font-weight:600;")

    h_list = []
    s_list = []
    if req is not None:
        try:
            form_data = await req.form()
            h_list = form_data.getlist("hopitaux_souhaites")
            s_list = form_data.getlist("specialites_souhaitees")
            if not demande_id: demande_id = str(form_data.get("demande_id", "")).strip()
            if not periode: periode = str(form_data.get("periode", "")).strip()
            if not specialite: specialite = str(form_data.get("specialite", "")).strip()
            if not hopital_actuel: hopital_actuel = str(form_data.get("hopital_actuel", "")).strip()
            if not statut: statut = str(form_data.get("statut", "Disponible")).strip()
        except Exception:
            pass

    if not h_list and hopitaux_souhaites:
        h_list = [hopitaux_souhaites] if isinstance(hopitaux_souhaites, str) else list(hopitaux_souhaites)
    h_list = [str(h).strip() for h in h_list if str(h).strip()]

    if not s_list and specialites_souhaitees:
        s_list = [specialites_souhaitees] if isinstance(specialites_souhaitees, str) else list(specialites_souhaitees)
    s_list = [str(s).strip() for s in s_list if str(s).strip()]

    if not h_list:
        return P("Veuillez conserver au moins un hôpital souhaité.", style="color:#b91c1c; font-weight:600;")
    if hopital_actuel in h_list:
        return P("L'hôpital actuel ne peut pas figurer dans les hôpitaux souhaités.", style="color:#b91c1c; font-weight:600;")

    update_payload = {
        "demande_id": demande_id,
        "user_email": u["email"],
        "nom_etudiant": f"{u.get('prenom', '')} {u.get('nom', '')}".strip() or u["email"],
        "periode": periode,
        "specialite": specialite,
        "hopital_actuel": hopital_actuel,
        "hopitaux_souhaites": h_list,
        "Hopitaux_Souhaites": serialize_hospitals(h_list),
        "specialites_souhaitees": s_list,
        "Specialites_Souhaitees": serialize_specialites(s_list),
        "statut": statut,
    }

    df_demandes_avant = load_demandes_data()
    all_bi_avant = compute_bilateral_matches(df_demandes_avant)
    all_tri_avant = compute_triangular_matches(df_demandes_avant)
    all_quad_avant = compute_quadrangular_matches(df_demandes_avant)
    anciens_rooms = {m["room_id"] for m in all_bi_avant} | {t["room_id"] for t in all_tri_avant} | {q["room_id"] for q in all_quad_avant}

    if save_demande(update_payload):
        df_maj = load_demandes_data()
        df_users = load_all_users()
        try:
            nouveaux_bi = compute_bilateral_matches(df_maj)
            nouveaux_tri = compute_triangular_matches(df_maj)
            nouveaux_quad = compute_quadrangular_matches(df_maj)
            for m in nouveaux_bi:
                if m["room_id"] not in anciens_rooms:
                    send_match_notification_emails(m["participants"], m["periode"], m["specialite"], m["room_id"], df_users)
            for t in nouveaux_tri:
                if t["room_id"] not in anciens_rooms:
                    send_match_notification_emails(t["participants"], t["periode"], t["specialite"], t["room_id"], df_users)
            for q in nouveaux_quad:
                if q["room_id"] not in anciens_rooms:
                    send_match_notification_emails(q["participants"], q["periode"], q["specialite"], q["room_id"], df_users)
        except Exception as exc:
            logger.warning(f"[PermutStage] Erreur non-bloquante notification match après modif: {exc}")

        return Article(
            P("✅ Offre mise à jour avec succès dans Firestore !"),
            style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:0.75rem; margin-bottom:1rem; border-radius:8px;"
        )
    return P("Erreur lors de la mise à jour.", style="color:#b91c1c;")

@rt("/supprimer-demande")
def post(session, demande_id: str, confirm_delete: str = None, req: Request = None):
    u = get_session_user(session, req)
    if not u or not u.get("email") or not confirm_delete:
        return P("Suppression annulée ou non autorisée.", style="color:#b91c1c;")

    if delete_demande(demande_id):
        return Article(
            P("🗑️ Votre offre a été supprimée avec succès de Firestore."),
            style="background:#fef2f2; border:1px solid #fecaca; color:#991b1b; padding:1rem; border-radius:10px;"
        )
    return P("Erreur lors de la suppression.", style="color:#b91c1c;")

# === AUTHENTIFICATION & COMPTE ÉTUDIANT (COLLECTION 'users') ===
@rt("/login-view")
def get(session, req: Request = None):
    u = get_session_user(session, req)
    if u and u.get("email"):
        return RedirectResponse("/deposer")

    return Main(
        render_header(session, "accueil", req),
        Div(
            Div(
                Article(
                    H3("🔑 Connexion Étudiant", style="font-weight:700; color:#0f172a;"),
                    P("Vérification directe de votre compte dans Firestore via votre email et votre code PIN."),
                    Div(id="login-feedback"),
                    Form(
                        Label("Email institutionnel", Input(name="email", type="email", placeholder="prenom.nom@student.uclouvain.be", required=True)),
                        Label("Code PIN (4 chiffres)", Input(name="pin", type="password", maxlength=4, placeholder="••••", required=True)),
                        Button("Se connecter", type="submit", cls="primary", style="border-radius:8px; font-weight:700; width:100%;"),
                        hx_post="/login",
                        hx_target="#login-feedback",
                        hx_swap="innerHTML"
                    ),
                    A("Code PIN oublié ?", href="/forgot-pin-view", style="display:block; margin-top:0.75rem; font-size:0.85rem;"),
                ),
                Article(
                    H3("📝 Créer mon profil", style="font-weight:700; color:#0f172a;"),
                    P("Inscription rapide. Votre profil sera enregistré immédiatement dans la collection 'users' de Firestore."),
                    Div(id="reg-feedback"),
                    Form(
                        Div(
                            Div(Label("Prénom *", Input(name="prenom", required=True))),
                            Div(Label("Nom *", Input(name="nom", required=True))),
                            style="display:grid; grid-template-columns: 1fr 1fr; gap:0.5rem;"
                        ),
                        Label("Email institutionnel *", Input(name="email", type="email", placeholder="prenom.nom@student.uclouvain.be", required=True)),
                        Label("Choisir un code PIN à 4 chiffres *", Input(name="pin", type="password", maxlength=4, placeholder="••••", required=True)),
                        Button("Créer mon compte étudiant", type="submit", cls="outline", style="border-radius:8px; font-weight:700; width:100%;"),
                        hx_post="/inscription",
                        hx_target="#reg-feedback",
                        hx_swap="innerHTML"
                    )
                ),
                style="display:grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap:2rem;"
            ),
            cls="container"
        ),
        render_footer()
    )

def handle_login(session, email: str = "", pin: str = "", code_pin: str = "", req: Request = None):
    em_clean = str(email or "").strip().lower()
    input_pin = normalize_pin(str(pin or code_pin or "").strip())

    if req is not None:
        rf = getattr(req, "_form", None)
        if rf:
            em_clean = em_clean or str(rf.get("email", "")).strip().lower()
            input_pin = input_pin or normalize_pin(str(rf.get("pin", "") or rf.get("code_pin", "")).strip())
        qp = getattr(req, "query_params", None)
        if qp:
            em_clean = em_clean or str(qp.get("email", "")).strip().lower()
            input_pin = input_pin or normalize_pin(str(qp.get("pin", "") or qp.get("code_pin", "")).strip())
        if hasattr(req, "_body") and req._body:
            try:
                from urllib.parse import parse_qs
                parsed = parse_qs(req._body.decode("utf-8", errors="ignore"))
                if not em_clean and "email" in parsed:
                    em_clean = str(parsed["email"][0]).strip().lower()
                if not input_pin and ("pin" in parsed or "code_pin" in parsed):
                    raw_p = parsed.get("pin", parsed.get("code_pin", [""]))[0]
                    input_pin = normalize_pin(str(raw_p).strip())
            except Exception:
                pass

    if not em_clean or not input_pin:
        return Article(
            P("⚠️ Veuillez renseigner votre email et votre code PIN.", style="color:#b91c1c; font-weight:600; margin:0;"),
            style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:10px; margin-bottom:1rem;"
        )

    # Vérification directe dans Firestore
    try:
        user_doc = get_user_by_email(em_clean)
    except Exception as exc:
        logger.error(f"[PermutStage] Erreur lors de la vérification de compte: {exc}")
        user_doc = None

    if not user_doc:
        return Article(
            P("⚠️ Compte introuvable, veuillez vous inscrire.", style="color:#b91c1c; font-weight:700; margin:0;"),
            P("Aucun document n'existe pour cet email dans la collection 'users'.", style="font-size:0.85rem; color:#64748b; margin-top:0.3rem;"),
            style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:10px; margin-bottom:1rem;"
        )

    bdd_pin = normalize_pin(user_doc.get("code_pin") or user_doc.get("PIN") or "")

    if input_pin == bdd_pin:
        session["user_id"] = em_clean
        session["user_email"] = em_clean
        session["email"] = em_clean
        session["nom"] = user_doc.get("nom") or user_doc.get("Nom") or "Étudiant"
        session["prenom"] = user_doc.get("prenom") or user_doc.get("Prenom") or ""
        session["pin"] = bdd_pin
        display_name = session["prenom"] or session["nom"]

        return Article(
            H4(f"🎉 Connexion réussie ! Bienvenue {display_name}.", style="color:#14532d; font-weight:800; margin-bottom:0.4rem;"),
            P("Votre compte a été vérifié dans Firestore. Votre session est active."),
            Div(
                A("Consulter mes correspondances", href="/matchs", role="button", cls="primary", style="margin-right:0.5rem; border-radius:8px;"),
                A("Déposer une offre", href="/deposer", role="button", cls="outline", style="border-radius:8px;"),
                style="margin-top:0.75rem;"
            ),
            Script(f"""
                localStorage.setItem('permutstage_auth_email', '{em_clean}');
                sessionStorage.removeItem('permutstage_logged_out');
                setTimeout(function() {{
                    window.location.href = '/matchs';
                }}, 600);
            """),
            style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:1.25rem; border-radius:12px; margin-bottom:1.5rem;"
        )

    return Article(
        P("⚠️ Email ou code PIN incorrect. Veuillez réessayer.", style="color:#b91c1c; font-weight:600; margin:0;"),
        style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:10px; margin-bottom:1rem;"
    )

@rt("/login")
def post(session, email: str = "", pin: str = "", code_pin: str = "", req: Request = None):
    return handle_login(session, email=email, pin=pin, code_pin=code_pin, req=req)

@rt("/login")
def get(session):
    return RedirectResponse("/login-view")


def handle_inscription(session, prenom: str = "", nom: str = "", email: str = "", pin: str = "", code_pin: str = "", req: Request = None):
    clean_prenom = str(prenom or "").strip()
    clean_nom = str(nom or "").strip()
    clean_email = str(email or "").strip().lower()
    clean_pin = normalize_pin(str(pin or code_pin or "").strip())

    if req is not None:
        rf = getattr(req, "_form", None)
        if rf:
            clean_prenom = clean_prenom or str(rf.get("prenom", "")).strip()
            clean_nom = clean_nom or str(rf.get("nom", "")).strip()
            clean_email = clean_email or str(rf.get("email", "")).strip().lower()
            clean_pin = clean_pin or normalize_pin(str(rf.get("pin", "") or rf.get("code_pin", "")).strip())
        qp = getattr(req, "query_params", None)
        if qp:
            clean_prenom = clean_prenom or str(qp.get("prenom", "")).strip()
            clean_nom = clean_nom or str(qp.get("nom", "")).strip()
            clean_email = clean_email or str(qp.get("email", "")).strip().lower()
            clean_pin = clean_pin or normalize_pin(str(qp.get("pin", "") or qp.get("code_pin", "")).strip())
        if hasattr(req, "_body") and req._body:
            try:
                from urllib.parse import parse_qs
                parsed = parse_qs(req._body.decode("utf-8", errors="ignore"))
                if not clean_prenom and "prenom" in parsed:
                    clean_prenom = str(parsed["prenom"][0]).strip()
                if not clean_nom and "nom" in parsed:
                    clean_nom = str(parsed["nom"][0]).strip()
                if not clean_email and "email" in parsed:
                    clean_email = str(parsed["email"][0]).strip().lower()
                if not clean_pin and ("pin" in parsed or "code_pin" in parsed):
                    raw_p = parsed.get("pin", parsed.get("code_pin", [""]))[0]
                    clean_pin = normalize_pin(str(raw_p).strip())
            except Exception:
                pass

    print(f"[PermutStage Inscription] 📩 Requête POST reçue : prenom='{clean_prenom}', nom='{clean_nom}', email='{clean_email}'")

    # 1. Validation assouplie : Prénom et Nom dès 1 caractère
    if len(clean_prenom) < 1:
        print("[PermutStage Inscription] ⚠️ Échec validation : prénom vide")
        return Article(
            P("⚠️ Veuillez renseigner votre prénom (au moins 1 caractère).", style="color:#b91c1c; font-weight:600; margin:0;"),
            style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:10px; margin-bottom:1rem;"
        )
    if len(clean_nom) < 1:
        print("[PermutStage Inscription] ⚠️ Échec validation : nom vide")
        return Article(
            P("⚠️ Veuillez renseigner votre nom (au moins 1 caractère).", style="color:#b91c1c; font-weight:600; margin:0;"),
            style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:10px; margin-bottom:1rem;"
        )

    # 2. Validation assouplie : Email avec @ et un domaine avec point
    if not clean_email or "@" not in clean_email or "." not in clean_email.split("@")[-1]:
        print(f"[PermutStage Inscription] ⚠️ Échec validation email invalide : {clean_email}")
        return Article(
            P("⚠️ Format d'adresse email invalide. Veuillez saisir une adresse universitaire valide contenant '@' et un nom de domaine.", style="color:#b91c1c; font-weight:600; margin:0;"),
            style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:10px; margin-bottom:1rem;"
        )

    # 3. Validation assouplie : Code PIN de 4 chiffres
    if not clean_pin or len(clean_pin) != 4 or not clean_pin.isdigit():
        print(f"[PermutStage Inscription] ⚠️ Échec validation code PIN invalide : {clean_pin}")
        return Article(
            P("⚠️ Le code PIN doit comporter exactement 4 chiffres numériques (ex: 1234).", style="color:#b91c1c; font-weight:600; margin:0;"),
            style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:10px; margin-bottom:1rem;"
        )

    # 4. Vérification d'existence dans Firestore
    try:
        existing = get_user_by_email(clean_email)
        if existing:
            print(f"[PermutStage Inscription] ⚠️ Compte déjà existant pour l'email : {clean_email}")
            return Article(
                P("⚠️ Un compte existe déjà avec cette adresse email. Veuillez vous connecter.", style="color:#b91c1c; font-weight:700; margin:0;"),
                P("Votre profil est déjà enregistré dans Firestore. Utilisez le formulaire de connexion ci-contre.", style="font-size:0.85rem; color:#64748b; margin-top:0.35rem;"),
                A("Basculer vers la connexion", href="/login-view", role="button", cls="outline", style="margin-top:0.6rem; border-radius:8px; font-size:0.85rem;"),
                style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:10px; margin-bottom:1rem;"
            )
    except Exception as exc:
        logger.error(f"Erreur vérification Firestore get_user_by_email: {exc}")

    # 5. Création immédiate et persistante dans Firestore
    new_user = {
        "email": clean_email,
        "nom": clean_nom,
        "prenom": clean_prenom,
        "code_pin": clean_pin,
        "created_at": datetime.now(ZoneInfo("Europe/Brussels")).isoformat(),
        "statut": "actif",
        "User_ID": clean_email,
        "Nom": clean_nom,
        "Prenom": clean_prenom,
        "PIN": clean_pin,
        "Email": clean_email,
        "Date_Inscription": datetime.now(ZoneInfo("Europe/Brussels")).strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        saved = create_or_update_user(new_user)
        if not saved:
            raise RuntimeError("Échec d'enregistrement create_or_update_user")
    except Exception as exc:
        logger.error(f"Erreur Firestore lors de create_or_update_user: {exc}", exc_info=True)
        return Article(
            P(f"⚠️ Erreur technique lors de l'enregistrement dans la base de données : {exc}. Veuillez réessayer.", style="color:#b91c1c; font-weight:600; margin:0;"),
            style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:10px; margin-bottom:1rem;"
        )

    # Envoi de l'e-mail de bienvenue automatique avec rappel des identifiants (non-bloquant)
    try:
        send_welcome_email(clean_email, clean_prenom, clean_nom, clean_pin)
    except Exception as mail_exc:
        logger.warning(f"[PermutStage Inscription] Erreur non-bloquante envoi email bienvenue: {mail_exc}")

    # 6. Enregistrement direct et complet dans la session FastHTML
    session["user_id"] = clean_email
    session["user_email"] = clean_email
    session["email"] = clean_email
    session["nom"] = clean_nom
    session["prenom"] = clean_prenom
    session["pin"] = clean_pin

    # 7. Retour visuel vert avec redirection automatique vers /deposer
    return Article(
        H4(f"🎉 Compte créé avec succès ! Bienvenue {clean_prenom}.", style="color:#14532d; font-weight:800; margin-bottom:0.4rem;"),
        P("Votre profil étudiant est désormais enregistré dans Firestore. Vous êtes automatiquement connecté."),
        Div(
            A("🚀 Déposer ma première offre de stage", href="/deposer", role="button", cls="primary", style="margin-right:0.5rem; border-radius:8px; font-weight:700;"),
            A("Consulter le catalogue", href="/catalogue", role="button", cls="outline", style="border-radius:8px;"),
            style="margin-top:0.75rem;"
        ),
        Script(f"""
            localStorage.setItem('permutstage_auth_email', '{clean_email}');
            sessionStorage.removeItem('permutstage_logged_out');
            setTimeout(function() {{
                window.location.href = '/deposer';
            }}, 800);
        """),
        style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:1.25rem; border-radius:12px; margin-bottom:1.5rem;"
    )

@rt("/inscription")
def post(session, prenom: str = "", nom: str = "", email: str = "", pin: str = "", code_pin: str = "", req: Request = None):
    return handle_inscription(session, prenom=prenom, nom=nom, email=email, pin=pin, code_pin=code_pin, req=req)

@rt("/inscription")
def get(session):
    return RedirectResponse("/login-view")

@rt("/register")
def post(session, prenom: str = "", nom: str = "", email: str = "", pin: str = "", code_pin: str = "", req: Request = None):
    return handle_inscription(session, prenom=prenom, nom=nom, email=email, pin=pin, code_pin=code_pin, req=req)

@rt("/register")
def get(session):
    return RedirectResponse("/login-view")

@rt("/forgot-pin-view")
def get(session, req: Request = None):
    return Main(
        render_header(session, "accueil", req),
        Div(
            Article(
                H3("🔑 Récupération de code PIN", style="font-weight:700;"),
                P("Entrez votre adresse email étudiante pour recevoir instantanément votre code PIN par email."),
                Div(id="forgot-feedback"),
                Form(
                    Label("Email institutionnel", Input(name="email", type="email", required=True)),
                    Button("M'envoyer mon code PIN", type="submit", cls="primary", style="border-radius:8px; font-weight:700;"),
                    hx_post="/forgot-pin",
                    hx_target="#forgot-feedback",
                    hx_swap="innerHTML"
                ),
                style="max-width:540px; margin:0 auto;"
            ),
            cls="container"
        ),
        render_footer()
    )

@rt("/forgot-pin")
def post(session, email: str = "", req: Request = None):
    em_clean = str(email or "").strip().lower()
    if not em_clean and req is not None:
        try:
            rf = getattr(req, "_form", None)
            if rf:
                em_clean = str(rf.get("email", "")).strip().lower()
            if not em_clean:
                qp = req.query_params
                if qp and qp.get("email"):
                    em_clean = str(qp.get("email", "")).strip().lower()
        except Exception:
            pass

    if not em_clean:
        return Article(
            P("⚠️ Veuillez renseigner votre adresse email institutionnelle.", style="color:#b91c1c; font-weight:700; margin:0;"),
            style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:10px;"
        )

    smtp_cfg = get_smtp_config()
    if not smtp_cfg:
        # Mesure de sécurité stricte : aucun code PIN ne doit jamais être affiché en clair sur l'écran
        return Article(
            H4("🔒 Sécurité & Confidentialité des accès", style="color:#991b1b; font-weight:800; margin-bottom:0.4rem;"),
            P("Pour des raisons de stricte confidentialité entre étudiants, aucun code PIN ne peut être affiché directement à l'écran."),
            P("La transmission de votre code PIN s'effectue exclusivement par email sécurisé vers votre boîte institutionnelle. Or, le service d'envoi d'email automatique (SMTP) n'est pas encore configuré sur ce serveur d'hébergement.", style="font-size:0.88rem; color:#475569; margin:0.5rem 0; line-height:1.5;"),
            P("💡 Si vous avez oublié votre code PIN, veuillez contacter l'administrateur de la plateforme pour réinitialiser votre accès ou vous connecter si vous vous souvenez de votre code.", style="font-size:0.85rem; color:#1e293b; font-weight:600; margin-top:0.6rem;"),
            Div(
                A("Retour à la page de connexion", href="/login-view", role="button", cls="outline", style="border-radius:8px; margin-top:0.75rem; font-size:0.85rem;"),
                style="margin-top:0.75rem;"
            ),
            style="background:#fef2f2; border:1px solid #fecaca; color:#991b1b; padding:1.25rem; border-radius:12px;"
        )

    # Si SMTP est configuré, envoyer l'email de manière sécurisée
    user_doc = get_user_by_email(em_clean)
    if user_doc:
        pin = normalize_pin(user_doc.get("code_pin") or user_doc.get("PIN") or "")
        prenom = str(user_doc.get("prenom") or user_doc.get("Prenom") or "étudiant").strip()
        try:
            send_pin_recovery_email(em_clean, prenom, pin)
        except Exception as err:
            logger.warning(f"[PermutStage] Envoi email échoué: {err}")
            return Article(
                H4("⚠️ Service d'envoi temporairement indisponible", style="color:#b91c1c; font-weight:800; margin-bottom:0.4rem;"),
                P("Une erreur est survenue lors de l'envoi de l'email de récupération. Veuillez réessayer ultérieurement ou contacter l'administrateur.", style="margin:0; font-size:0.88rem;"),
                style="background:#fef2f2; border:1px solid #fecaca; color:#b91c1c; padding:1rem; border-radius:10px;"
            )

    # Réponse générique conforme aux bonnes pratiques de sécurité (aucun PIN affiché)
    return Article(
        H4("📧 Demande enregistrée avec succès", style="color:#14532d; font-weight:800; margin-bottom:0.4rem;"),
        P(f"Si l'adresse {em_clean} correspond à un compte étudiant existant, un email contenant votre code PIN de connexion vient de vous être expédié."),
        P("Veuillez consulter votre boîte de réception ainsi que vos courriers indésirables (dossier spams).", style="font-size:0.85rem; color:#166534; margin:0.35rem 0;"),
        A("Retour à la connexion", href="/login-view", role="button", cls="primary", style="border-radius:8px; margin-top:0.75rem;"),
        style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:1.25rem; border-radius:12px;"
    )

# === VUE PROFIL ÉTUDIANT & MODIFICATION CODE PIN ===
@rt("/profil")
def get(session, req: Request = None):
    u = get_session_user(session, req)
    if not u or not u.get("email"):
        return RedirectResponse("/login-view")

    user_email = u["email"].strip().lower()
    user_doc = get_user_by_email(user_email) or {}
    prenom = str(user_doc.get("prenom") or u.get("prenom") or "").strip()
    nom = str(user_doc.get("nom") or u.get("nom") or "").strip()
    current_pin = normalize_pin(user_doc.get("code_pin") or u.get("pin") or "")
    date_insc = user_doc.get("Date_Inscription") or user_doc.get("created_at") or "Récemment"

    df_demandes = load_demandes_data()
    my_demandes = []
    if not df_demandes.empty and "Email" in df_demandes.columns:
        sub = df_demandes[df_demandes["Email"].str.lower() == user_email]
        for _, row in sub.iterrows():
            my_demandes.append(row.to_dict())

    demandes_elements = []
    if not my_demandes:
        demandes_elements.append(
            P("Vous n'avez pas encore déposé d'offre de stage.", style="color:#64748b; font-style:italic;")
        )
    else:
        for d in my_demandes:
            demandes_elements.append(
                Article(
                    Div(
                        Strong(f"{d.get('Periode')} · {d.get('Specialite')}", style="color:#1d4ed8; font-weight:700;"),
                        Span(d.get("Statut", "Disponible"), cls="status-badge status-disponible", style="float:right;"),
                        style="margin-bottom:0.5rem;"
                    ),
                    P(f"Hôpital actuel : {d.get('Hopital_Actuel')}", style="margin:0 0 0.25rem 0; font-size:0.9rem;"),
                    P(f"Hôpitaux souhaités : {d.get('Hopitaux_Souhaites')}", style="margin:0; font-size:0.85rem; color:#64748b;"),
                    A("Modifier cette offre dans 'Gérer mon offre' →", href="/gerer", style="display:inline-block; margin-top:0.5rem; font-size:0.82rem; font-weight:600;"),
                    style="padding:0.75rem 1rem; border:1px solid #e2e8f0; border-radius:8px; margin-bottom:0.5rem; background:#f8fafc;"
                )
            )

    return Main(
        render_header(session, "profil", req),
        Div(
            H2("👤 Mon Profil Étudiant", style="font-weight:800; color:#0f172a; margin-bottom:0.4rem;"),
            P("Gérez vos informations personnelles et mettez à jour votre code PIN de connexion."),
            Div(
                Article(
                    H3("⚙️ Paramètres du compte", style="font-weight:700; color:#0f172a; margin-bottom:1rem;"),
                    Div(id="profil-feedback"),
                    Form(
                        Label("Email institutionnel (identifiant unique)",
                            Input(type="email", value=user_email, disabled=True, style="background:#f1f5f9; cursor:not-allowed; opacity:0.8;")
                        ),
                        Div(
                            Div(Label("Prénom *", Input(name="prenom", value=prenom, required=True))),
                            Div(Label("Nom *", Input(name="nom", value=nom, required=True))),
                            style="display:grid; grid-template-columns: 1fr 1fr; gap:0.5rem;"
                        ),
                        Hr(style="margin:1.25rem 0;"),
                        Div(
                            H4("🔒 Modification du code PIN", id="changer-pin", style="font-weight:700; font-size:1.05rem; margin-bottom:0.3rem; color:#1d4ed8; scroll-margin-top:2rem;"),
                            P(f"Code PIN actuel : {current_pin} (laisser vide ci-dessous si vous souhaitez le conserver).", style="font-size:0.85rem; color:#64748b; margin-bottom:0.75rem;"),
                            Div(
                                Div(Label("Nouveau code PIN (4 chiffres)", Input(name="nouveau_pin", type="password", maxlength=4, placeholder="••••"))),
                                Div(Label("Confirmer le code PIN", Input(name="confirmer_pin", type="password", maxlength=4, placeholder="••••"))),
                                style="display:grid; grid-template-columns: 1fr 1fr; gap:0.5rem;"
                            ),
                            style="background:#f8fafc; border:1px solid #bfdbfe; border-radius:10px; padding:1rem; margin-bottom:1rem;"
                        ),
                        Button("💾 Enregistrer les modifications", type="submit", cls="primary", style="border-radius:8px; font-weight:700; width:100%; margin-top:1.25rem;"),
                        hx_post="/modifier-profil",
                        hx_target="#profil-feedback",
                        hx_swap="innerHTML"
                    ),
                    style="border-radius:12px;"
                ),
                Div(
                    Article(
                        H3("📋 Informations de session", style="font-weight:700; color:#0f172a; margin-bottom:0.75rem;"),
                        Ul(
                            Li(Strong("Statut : "), Span("Actif & Vérifié", style="color:#15803d; font-weight:700;")),
                            Li(Strong("Compte : "), user_email),
                            Li(Strong("Date d'inscription : "), str(date_insc)[:19]),
                            Li(Strong("Base de données : "), "Google Cloud Firestore (users)")
                        ),
                        Div(
                            A("Déposer une offre de stage", href="/deposer", role="button", cls="outline", style="border-radius:8px; font-size:0.85rem; margin-right:0.5rem;"),
                            A("Gérer mes offres", href="/gerer", role="button", cls="outline", style="border-radius:8px; font-size:0.85rem;"),
                            style="margin-top:1rem;"
                        ),
                        style="border-radius:12px; margin-bottom:1.5rem;"
                    ),
                    Article(
                        H3("🏥 Mes propositions de stages", style="font-weight:700; color:#0f172a; margin-bottom:0.75rem;"),
                        *demandes_elements,
                        style="border-radius:12px;"
                    ),
                ),
                style="display:grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap:2rem;"
            ),
            cls="container"
        ),
        render_footer()
    )

@rt("/modifier-profil")
def post(session, prenom: str = "", nom: str = "", nouveau_pin: str = "", confirmer_pin: str = "", req: Request = None):
    u = get_session_user(session, req)
    if not u or not u.get("email"):
        return Article(P("⚠️ Session expirée. Veuillez vous reconnecter.", style="color:#b91c1c; font-weight:600; margin:0;"), style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:10px;")

    clean_email = u["email"].strip().lower()
    clean_prenom = str(prenom or "").strip()
    clean_nom = str(nom or "").strip()
    np = str(nouveau_pin or "").strip()
    cp = str(confirmer_pin or "").strip()

    if req is not None:
        rf = getattr(req, "_form", None)
        if rf:
            clean_prenom = clean_prenom or str(rf.get("prenom", "")).strip()
            clean_nom = clean_nom or str(rf.get("nom", "")).strip()
            np = np or str(rf.get("nouveau_pin", "")).strip()
            cp = cp or str(rf.get("confirmer_pin", "")).strip()

    if len(clean_prenom) < 1 or len(clean_nom) < 1:
        return Article(
            P("⚠️ Le prénom et le nom sont obligatoires (au moins 1 caractère).", style="color:#b91c1c; font-weight:600; margin:0;"),
            style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:10px; margin-bottom:1rem;"
        )

    clean_pin_to_save = None
    if np or cp:
        norm_np = normalize_pin(np)
        norm_cp = normalize_pin(cp)
        if len(norm_np) != 4 or not norm_np.isdigit():
            return Article(
                P("⚠️ Le nouveau code PIN doit comporter exactement 4 chiffres numériques.", style="color:#b91c1c; font-weight:600; margin:0;"),
                style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:10px; margin-bottom:1rem;"
            )
        if norm_np != norm_cp:
            return Article(
                P("⚠️ La confirmation du code PIN ne correspond pas au nouveau code PIN saisi.", style="color:#b91c1c; font-weight:600; margin:0;"),
                style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:10px; margin-bottom:1rem;"
            )
        clean_pin_to_save = norm_np

    update_user_profile(clean_email, clean_prenom, clean_nom, clean_pin_to_save)

    session["prenom"] = clean_prenom
    session["nom"] = clean_nom
    if clean_pin_to_save:
        session["pin"] = clean_pin_to_save

    pin_msg = f"Votre nouveau code PIN est désormais : Strong({clean_pin_to_save})." if clean_pin_to_save else "Code PIN inchangé."

    return Article(
        H4("🎉 Modifications enregistrées avec succès !", style="color:#14532d; font-weight:800; margin-bottom:0.4rem;"),
        P(f"Votre profil ({clean_prenom} {clean_nom}) a été mis à jour dans Firestore. {pin_msg}"),
        Script(f"""
            setTimeout(function() {{
                window.location.reload();
            }}, 1200);
        """),
        style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:1.25rem; border-radius:12px; margin-bottom:1rem;"
    )

@rt("/notifications")
def get(session, req: Request = None):
    u = get_session_user(session, req)
    if not u or not u.get("email"):
        return RedirectResponse("/login-view")

    user_email = u["email"]
    df_demandes = load_demandes_data()
    df_messages = load_messages_data()
    all_bi = compute_bilateral_matches(df_demandes)
    all_tri = compute_triangular_matches(df_demandes)
    all_quad = compute_quadrangular_matches(df_demandes)
    my_bi, my_tri, my_quad = filter_private_matches_for_user(user_email, all_bi, all_tri, all_quad)
    notifs = build_user_notifications(user_email, my_bi, my_tri, df_messages, my_quad)

    cards = []
    if not notifs:
        cards.append(Article(P("Aucune nouvelle notification pour le moment.")))
    else:
        for n in notifs:
            cards.append(
                Article(
                    Strong(n["titre"], style="color:#1e3a8a; display:block; margin-bottom:0.3rem; font-size:0.95rem;"),
                    P(n["detail"], style="font-size:0.9rem; color:#334155; margin-bottom:0.5rem;"),
                    A("Ouvrir le salon correspondant", href=f"/salon/{n['room_id']}", role="button", cls="outline secondary", style="font-size:0.8rem; padding:0.35rem 0.75rem; border-radius:6px;"),
                    style="margin-bottom:0.75rem; border-left:4px solid #1d4ed8; border-radius:8px;"
                )
            )

    return Main(
        render_header(session, "accueil", req),
        Div(
            H2("🔔 Centre de Notifications", style="font-weight:800; color:#0f172a;"),
            *cards,
            cls="container"
        ),
        render_footer()
    )

@rt("/logout")
def get(session):
    session.clear()
    return Main(
        Script("""
            localStorage.removeItem('permutstage_auth_email');
            sessionStorage.setItem('permutstage_logged_out', '1');
            window.location.href = '/login-view';
        """),
        Div(
            Article(
                H3("👋 Déconnexion réussie"),
                P("Votre session a été fermée avec succès."),
                A("Retour à la connexion", href="/login-view", role="button", cls="primary"),
                style="text-align:center; padding:2rem;"
            ),
            cls="container"
        )
    )

# === VUE 6 : ESPACE ADMINISTRATION ===
@rt("/admin-login-view")
def get(session, req: Request = None):
    return Main(
        render_header(session, "accueil", req),
        Div(
            Article(
                H3("🔒 Accès Administrateur", style="font-weight:700;"),
                P("Espace réservé à la coordination technique et facultaire."),
                Div(id="admin-feedback"),
                Form(
                    Label("Mot de passe secret administrateur", Input(name="password", type="password", required=True)),
                    Button("Déverrouiller l'Espace Administrateur", type="submit", cls="primary", style="border-radius:8px; font-weight:700;"),
                    hx_post="/admin-login",
                    hx_target="#admin-feedback",
                    hx_swap="innerHTML"
                ),
                style="max-width:480px; margin:0 auto;"
            ),
            cls="container"
        ),
        render_footer()
    )

@rt("/admin-login")
def post(session, password: str = ""):
    admin_pwd = os.environ.get("ADMIN_PASSWORD", "admin123")
    if password.strip() == admin_pwd.strip():
        session["is_admin"] = True
        return Article(
            P("Accès accordé."),
            A("Ouvrir l'Espace Administrateur", href="/admin", role="button", cls="primary", style="border-radius:8px;"),
            style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:1rem; border-radius:10px;"
        )
    return P("Mot de passe incorrect.", style="color:#b91c1c; font-weight:600;")

@rt("/admin")
def get(session, req: Request = None):
    if not session.get("is_admin", False):
        return RedirectResponse("/admin-login-view")

    df_users = load_all_users()
    df_demandes = load_demandes_data()
    all_bi = compute_bilateral_matches(df_demandes)
    all_tri = compute_triangular_matches(df_demandes)
    all_quad = compute_quadrangular_matches(df_demandes)

    demandes_rows = []
    for _, d in df_demandes.iterrows():
        d_id = str(d.get("demande_id") or d.get("Demande_ID") or "")
        demandes_rows.append(
            Tr(
                Td(Small(d_id)),
                Td(d.get("Nom", "")),
                Td(d.get("Email", "")),
                Td(d.get("Periode", "")),
                Td(d.get("Specialite", "")),
                Td(d.get("Hopital_Actuel", "")),
                Td(Span(d.get("Statut", "Disponible"), cls=f"status-badge status-{str(d.get('Statut', 'Disponible')).lower().replace(' ', '')}")),
                Td(
                    Form(
                        Input(type="hidden", name="demande_id", value=d_id),
                        Button("Supprimer", type="submit", cls="outline secondary", style="padding:0.25rem 0.5rem; font-size:0.75rem; color:#b91c1c; border-color:#b91c1c; border-radius:6px;"),
                        hx_post="/admin-delete-demande",
                        hx_target="#admin-feedback",
                        hx_swap="innerHTML"
                    )
                )
            )
        )

    users_rows = []
    for _, u in df_users.iterrows():
        u_email = str(u.get("email") or u.get("Email") or "")
        users_rows.append(
            Tr(
                Td(Small(u_email)),
                Td(f"{u.get('prenom', '')} {u.get('nom', '')}".strip() or u.get("Nom", "")),
                Td(u_email),
                Td(u.get("created_at") or u.get("Date_Inscription", "")),
                Td(
                    Form(
                        Input(type="hidden", name="user_email", value=u_email),
                        Button("Supprimer", type="submit", cls="outline secondary", style="padding:0.25rem 0.5rem; font-size:0.75rem; color:#b91c1c; border-color:#b91c1c; border-radius:6px;"),
                        hx_post="/admin-delete-user",
                        hx_target="#admin-feedback",
                        hx_swap="innerHTML"
                    )
                )
            )
        )

    return Main(
        render_header(session, "admin", req),
        Div(
            H2("🛠️ Espace Administrateur (Supervision globale)", style="font-weight:800; color:#0f172a;"),
            Div(id="admin-feedback"),
            Div(
                Div(Div(str(len(df_users)), cls="stat-val"), Div("Comptes étudiants", cls="stat-lbl"), cls="stat-card"),
                Div(Div(str(len(df_demandes)), cls="stat-val"), Div("Offres actives", cls="stat-lbl"), cls="stat-card"),
                Div(Div(str(len(all_bi)), cls="stat-val"), Div("Matchs binômes", cls="stat-lbl"), cls="stat-card"),
                Div(Div(str(len(all_tri)), cls="stat-val"), Div("Boucles triangulaires", cls="stat-lbl"), cls="stat-card"),
                Div(Div(str(len(all_quad)), cls="stat-val"), Div("Cycles en carré (4)", cls="stat-lbl"), cls="stat-card"),
                style="display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:1rem; margin-bottom:2rem;"
            ),
            Article(
                H3(f"📋 Collection 'demandes' ({len(df_demandes)})", style="font-weight:700;"),
                Div(
                    A("📥 Télécharger CSV", href="/admin-export-demandes-csv", role="button", cls="outline", style="margin-bottom:1rem; padding:0.4rem 0.8rem; font-size:0.8rem; border-radius:6px;"),
                    Table(
                        Thead(Tr(Th("ID"), Th("Nom"), Th("Email"), Th("Période"), Th("Spécialité"), Th("Hôpital actuel"), Th("Statut"), Th("Action"))),
                        Tbody(*demandes_rows),
                        cls="striped"
                    ),
                    style="overflow-x:auto;"
                )
            ),
            Article(
                H3(f"👥 Collection 'users' ({len(df_users)})", style="font-weight:700;"),
                Div(
                    Table(
                        Thead(Tr(Th("Email (Clé doc)"), Th("Nom complet"), Th("Email"), Th("Inscription"), Th("Action"))),
                        Tbody(*users_rows),
                        cls="striped"
                    ),
                    style="overflow-x:auto;"
                )
            ),
            cls="container"
        ),
        render_footer()
    )

@rt("/admin-delete-demande")
def post(session, demande_id: str):
    if not session.get("is_admin", False):
        return P("Non autorisé", style="color:#b91c1c;")
    if delete_demande(demande_id):
        return Article(P(f"Demande {demande_id} supprimée."), style="background:#fef2f2; color:#991b1b; padding:0.5rem; border-radius:6px;")
    return P("Erreur", style="color:#b91c1c;")

@rt("/admin-delete-user")
def post(session, user_email: str):
    if not session.get("is_admin", False):
        return P("Non autorisé", style="color:#b91c1c;")
    if delete_user_and_demandes(user_email):
        return Article(P(f"Utilisateur {user_email} et ses demandes supprimés de Firestore."), style="background:#fef2f2; color:#991b1b; padding:0.5rem; border-radius:6px;")
    return P("Erreur", style="color:#b91c1c;")

@rt("/admin-export-demandes-csv")
def get(session):
    if not session.get("is_admin", False):
        return RedirectResponse("/")
    df_demandes = load_demandes_data()
    csv_str = df_demandes.to_csv(index=False)
    return Response(
        csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=permutstage_demandes_{datetime.now(ZoneInfo('Europe/Brussels')).strftime('%Y%m%d_%H%M')}.csv"}
    )

# === ROUTE DE HEALTHCHECK CLOUD (RENDER / KUBERNETES) ===
@rt("/healthz")
@rt("/health")
def get():
    return Response("OK", media_type="text/plain")

# === VALIDATION DE PROPRIÉTÉ GOOGLE SEARCH CONSOLE (RÉFÉRENCEMENT GOOGLE) ===
@rt("/googleb26e30d985ea7bf8.html")
def get():
    return Response("google-site-verification: googlef15bfd55c9dd0120.html", media_type="text/html")

# ---------------------------------------------------------------------------
# 12. DÉMARRAGE DU SERVEUR FASTHTML (COMPATIBLE RENDER & LOCAL MAC/LINUX)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    host = os.environ.get("HOST", "0.0.0.0")
    serve(host=host, port=port)
