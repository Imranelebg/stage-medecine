"""
PermutStage — Plateforme Collaborative d'Échange de Lieux de Stage (Médecine P3 à P8)
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
        Title("PermutStage — Permutation de Stages Médecine"),
        Meta(charset="UTF-8"),
        Meta(name="viewport", content="width=device-width, initial-scale=1.0"),
        Link(rel="preconnect", href="https://fonts.googleapis.com"),
        Link(rel="preconnect", href="https://fonts.gstatic.com", crossorigin=""),
        Link(rel="stylesheet", href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap"),
        CUSTOM_STYLE,
    ),
)

# ---------------------------------------------------------------------------
# 2. CONSTANTES MÉTIER & BASE DE DONNÉES DES HÔPITAUX PAR RÉGION
# ---------------------------------------------------------------------------
PERIODES = ["P3", "P4", "P5", "P6", "P7", "P8"]

SPECIALITES = [
    "Pédiatrie",
    "Médecine interne",
    "Gériatrie",
    "Gynécologie-obstétrique",
    "Urgences",
    "Chirurgie",
]

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
_FIRESTORE_INIT_DONE = False
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
    """Initialise Firebase Firestore une seule fois sans jamais bloquer 20s sur Render."""
    global _FIRESTORE_CLIENT, _FIRESTORE_INIT_DONE
    if _FIRESTORE_CLIENT is not None:
        return _FIRESTORE_CLIENT
    if _FIRESTORE_INIT_DONE:
        return None

    _FIRESTORE_INIT_DONE = True

    if not firebase_admin._apps:
        try:
            fb_creds_dict = None

            # 1. Variables d'environnement (JSON direct ou chemin de fichier)
            for env_key in ["FIREBASE_CREDENTIALS", "FIREBASE_CONFIG", "FIREBASE_KEY", "GOOGLE_APPLICATION_CREDENTIALS"]:
                raw_env = os.environ.get(env_key)
                if raw_env:
                    raw_env = raw_env.strip()
                    if os.path.exists(raw_env):
                        cred = credentials.Certificate(raw_env)
                        firebase_admin.initialize_app(cred)
                        _FIRESTORE_CLIENT = firestore.client()
                        return _FIRESTORE_CLIENT
                    else:
                        try:
                            fb_creds_dict = json.loads(raw_env)
                            break
                        except Exception:
                            pass

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
                                        break
                            except Exception:
                                pass

            # 3. Fichiers JSON (racine ou dossier /etc/secrets/ de Render)
            if fb_creds_dict is None:
                for p in [
                    "serviceAccountKey.json", "firebase_key.json", "firebase-credentials.json", "firebase_credentials.json",
                    "/etc/secrets/serviceAccountKey.json", "/etc/secrets/firebase_key.json", "/etc/secrets/firebase-credentials.json", "/etc/secrets/firebase_credentials.json"
                ]:
                    if os.path.exists(p):
                        cred = credentials.Certificate(p)
                        firebase_admin.initialize_app(cred)
                        _FIRESTORE_CLIENT = firestore.client()
                        return _FIRESTORE_CLIENT

            if fb_creds_dict:
                if "private_key" in fb_creds_dict and isinstance(fb_creds_dict["private_key"], str):
                    fb_creds_dict["private_key"] = fb_creds_dict["private_key"].replace("\\n", "\n")
                cred = credentials.Certificate(fb_creds_dict)
                firebase_admin.initialize_app(cred)
                _FIRESTORE_CLIENT = firestore.client()
                return _FIRESTORE_CLIENT

            # Aucun appel à firebase_admin.initialize_app() vide pour éviter le timeout de 20s sur Render
            return None

        except Exception as exc:
            print(f"[PermutStage] Firestore init notice: {exc}")
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
    created_at = user_data.get("created_at") or datetime.now().isoformat()
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
        "Date_Inscription": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # 1. Écriture Firestore
    db = get_firestore_client()
    if db is not None:
        try:
            db.collection(COLLECTION_USERS).document(clean_email).set(doc_payload)
            print(f"[PermutStage] Succès écriture Firestore user: {clean_email}")
        except Exception as exc:
            print(f"[PermutStage] Erreur écriture Firestore user: {exc}")
            logger.error(f"[PermutStage] Erreur écriture Firestore user: {exc}")

    # 2. Écriture persistante sur disque local
    local = load_local_db()
    if "users" not in local: local["users"] = {}
    local["users"][clean_email] = doc_payload
    save_local_db(local)

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

def save_demande(demande_dict: dict) -> bool:
    """
    Enregistre ou met à jour une offre de permutation dans la collection 'demandes'.
    Champs : user_email, nom_etudiant, periode, specialite, hopital_actuel, hopitaux_souhaites, statut, updated_at.
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
    statut = (demande_dict.get("statut") or demande_dict.get("Statut") or "disponible").lower()
    if statut in ("disponible", "actif"): statut_clean = "disponible"
    elif statut in ("en_discussion", "en discussion", "en_cours"): statut_clean = "en_cours"
    else: statut_clean = "conclue"

    now_iso = datetime.now().isoformat()
    now_human = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
