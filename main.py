"""
PermutStage — Plateforme Collaborative d'Échange de Lieux de Stage (Médecine P3 à P8)
Version FastHTML (python-fasthtml) & Firebase Firestore (firebase-admin).

Architecture complète dans un fichier unique main.py :
- Interface FastHTML avec Pico.css natif (Pico=True) et requêtes HTMX réactives sans rechargement lourd.
- Sélecteur moderne et interactif d'hôpitaux souhaités par cases à cocher avec sélection rapide par province, recherche instantanée et compteur dynamique.
- Gestion des sessions utilisateur natives FastHTML (session['user_id'], session['email']).
- Intégration Firebase Firestore (Collections: 'users', 'demandes', 'messages') via credentials.Certificate.
- Moteur de matching bilatéral (A <-> B) et triangulaire (A -> B -> C -> A) avec confidentialité absolue.
- Système d'alertes par email SMTP automatique lors de la formation d'un cycle complet.
- Salons de discussion privés et sécurisés par match avec échange en direct HTMX.
- Gestion du statut des demandes ("Disponible", "En discussion", "Accord trouvé").
- Espace Administration complet avec statistiques, export CSV et modération.

Exécution :
    python main.py
"""

from fasthtml.common import *
import os
import re
import uuid
import json
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore

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

    /* ==========================================================================
       NOUVEAU COMPOSANT : SÉLECTEUR D'HÔPITAUX SOUHAITÉS MODERNE (CHECKBOXES)
       ========================================================================== */
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
    live=True,
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
# (100% identiques au cahier des charges, sans la Flandre)
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

COLLECTION_USERS = "users"
COLLECTION_DEMANDES = "demandes"
COLLECTION_MESSAGES = "messages"

COLONNES_UTILISATEURS = [
    "User_ID",
    "Nom",
    "Prenom",
    "Email",
    "PIN",
    "Date_Inscription",
]

COLONNES_DEMANDES = [
    "Demande_ID",
    "Timestamp",
    "Nom",
    "Email",
    "PIN",
    "Periode",
    "Specialite",
    "Hopital_Actuel",
    "Hopitaux_Souhaites",
    "Statut",
]

COLONNES_MESSAGES = [
    "Message_ID",
    "Room_ID",
    "Sender_Email",
    "Sender_Name",
    "Timestamp",
    "Texte",
]

NOTIFIED_MATCH_ROOMS: set[str] = set()

def slugify(text: str) -> str:
    """Génère un identifiant HTML safe pour les lignes d'hôpitaux."""
    return re.sub(r'[^a-zA-Z0-9]+', '-', text).strip('-').lower()

# ---------------------------------------------------------------------------
# 3. INITIALISATION ROBUSTE FIREBASE FIRESTORE (credentials.Certificate)
# ---------------------------------------------------------------------------
_FIRESTORE_CLIENT = None

def get_firestore_client():
    global _FIRESTORE_CLIENT
    if _FIRESTORE_CLIENT is not None:
        return _FIRESTORE_CLIENT

    if not firebase_admin._apps:
        try:
            fb_creds_dict = None

            raw_env = os.environ.get("FIREBASE_CREDENTIALS") or os.environ.get("FIREBASE_CONFIG")
            if raw_env:
                if os.path.exists(raw_env):
                    cred = credentials.Certificate(raw_env)
                    firebase_admin.initialize_app(cred)
                    _FIRESTORE_CLIENT = firestore.client()
                    return _FIRESTORE_CLIENT
                else:
                    fb_creds_dict = json.loads(raw_env)

            if fb_creds_dict is None:
                toml_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
                if os.path.exists(toml_path):
                    try:
                        import tomllib
                    except ImportError:
                        try:
                            import tomli as tomllib
                        except ImportError:
                            tomllib = None
                    if tomllib:
                        with open(toml_path, "rb") as f:
                            sec = tomllib.load(f)
                            if "firebase" in sec:
                                fb_creds_dict = dict(sec["firebase"])

            if fb_creds_dict is None and os.path.exists("serviceAccountKey.json"):
                cred = credentials.Certificate("serviceAccountKey.json")
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
        except Exception as exc:
            print(f"[PermutStage] Erreur d'initialisation Firebase Firestore: {exc}")
            return None

    try:
        _FIRESTORE_CLIENT = firestore.client()
        return _FIRESTORE_CLIENT
    except Exception:
        return None

_MEMOIRE_USERS = {}
_MEMOIRE_DEMANDES = {}
_MEMOIRE_MESSAGES = {}

# ---------------------------------------------------------------------------
# 4. GESTION DES DONNÉES FIRESTORE
# ---------------------------------------------------------------------------
def normalize_pin(val: str) -> str:
    s = str(val or "").strip().replace(".0", "")
    return s.zfill(4) if (s.isdigit() and len(s) <= 4) else s

def load_users_data() -> pd.DataFrame:
    db = get_firestore_client()
    if db is None:
        if not _MEMOIRE_USERS:
            return pd.DataFrame(columns=COLONNES_UTILISATEURS)
        df = pd.DataFrame(list(_MEMOIRE_USERS.values()))
        for c in COLONNES_UTILISATEURS:
            if c not in df.columns: df[c] = ""
        return df[COLONNES_UTILISATEURS]

    try:
        docs = db.collection(COLLECTION_USERS).stream()
        data = []
        for doc in docs:
            item = doc.to_dict() or {}
            item["User_ID"] = str(item.get("User_ID") or doc.id).strip()
            item["PIN"] = normalize_pin(item.get("PIN", ""))
            data.append(item)
        if not data:
            return pd.DataFrame(columns=COLONNES_UTILISATEURS)
        df = pd.DataFrame(data)
        for c in COLONNES_UTILISATEURS:
            if c not in df.columns: df[c] = ""
        return df[COLONNES_UTILISATEURS]
    except Exception as exc:
        print(f"Erreur load_users_data: {exc}")
        return pd.DataFrame(columns=COLONNES_UTILISATEURS)

def create_user_firestore(user_dict: dict) -> bool:
    db = get_firestore_client()
    user_id = user_dict["User_ID"]
    if db is None:
        _MEMOIRE_USERS[user_id] = user_dict
        return True
    try:
        db.collection(COLLECTION_USERS).document(user_id).set(user_dict)
        return True
    except Exception as exc:
        print(f"Erreur create_user_firestore: {exc}")
        return False

def update_user_pin_firestore(user_id: str, email: str, new_pin: str) -> bool:
    pin_clean = normalize_pin(new_pin)
    db = get_firestore_client()
    if db is None:
        if user_id in _MEMOIRE_USERS:
            _MEMOIRE_USERS[user_id]["PIN"] = pin_clean
        clean_email = email.strip().lower()
        for d in _MEMOIRE_DEMANDES.values():
            if d.get("Email", "").strip().lower() == clean_email:
                d["PIN"] = pin_clean
        return True
    try:
        db.collection(COLLECTION_USERS).document(user_id).update({"PIN": pin_clean})
        clean_email = email.strip().lower()
        demandes = db.collection(COLLECTION_DEMANDES).where("Email", "==", clean_email).stream()
        for doc in demandes:
            doc.reference.update({"PIN": pin_clean})
        return True
    except Exception as exc:
        print(f"Erreur update_user_pin_firestore: {exc}")
        return False

def delete_user_firestore(user_id: str) -> bool:
    db = get_firestore_client()
    if db is None:
        user_email = _MEMOIRE_USERS.get(user_id, {}).get("Email", "").strip().lower()
        _MEMOIRE_USERS.pop(user_id, None)
        if user_email:
            to_del = [k for k, v in _MEMOIRE_DEMANDES.items() if v.get("Email", "").strip().lower() == user_email]
            for k in to_del: _MEMOIRE_DEMANDES.pop(k, None)
        return True
    try:
        clean_id = str(user_id).strip()
        ref = db.collection(COLLECTION_USERS).document(clean_id)
        snap = ref.get()
        user_email = ""
        if snap.exists:
            user_email = str((snap.to_dict() or {}).get("Email", "")).strip().lower()
        ref.delete()
        if user_email:
            demandes = db.collection(COLLECTION_DEMANDES).where("Email", "==", user_email).stream()
            for doc in demandes:
                doc.reference.delete()
        return True
    except Exception as exc:
        print(f"Erreur delete_user_firestore: {exc}")
        return False

def load_demandes_data() -> pd.DataFrame:
    db = get_firestore_client()
    if db is None:
        if not _MEMOIRE_DEMANDES:
            return pd.DataFrame(columns=COLONNES_DEMANDES)
        df = pd.DataFrame(list(_MEMOIRE_DEMANDES.values()))
        for c in COLONNES_DEMANDES:
            if c not in df.columns:
                df[c] = "Disponible" if c == "Statut" else ""
        return df[COLONNES_DEMANDES]

    try:
        docs = db.collection(COLLECTION_DEMANDES).stream()
        data = []
        for doc in docs:
            item = doc.to_dict() or {}
            item["Demande_ID"] = str(item.get("Demande_ID") or doc.id).strip()
            item["PIN"] = normalize_pin(item.get("PIN", ""))
            if "Statut" not in item or not item["Statut"]:
                item["Statut"] = "Disponible"
            data.append(item)
        if not data:
            return pd.DataFrame(columns=COLONNES_DEMANDES)
        df = pd.DataFrame(data)
        for c in COLONNES_DEMANDES:
            if c not in df.columns:
                df[c] = "Disponible" if c == "Statut" else ""
        return df[COLONNES_DEMANDES]
    except Exception as exc:
        print(f"Erreur load_demandes_data: {exc}")
        return pd.DataFrame(columns=COLONNES_DEMANDES)

def add_demande_firestore(demande_dict: dict) -> bool:
    demande_id = demande_dict.get("Demande_ID") or f"DEM_{uuid.uuid4().hex[:10].upper()}"
    demande_dict["Demande_ID"] = demande_id
    if "Statut" not in demande_dict:
        demande_dict["Statut"] = "Disponible"
    db = get_firestore_client()
    if db is None:
        _MEMOIRE_DEMANDES[demande_id] = demande_dict
        return True
    try:
        db.collection(COLLECTION_DEMANDES).document(demande_id).set(demande_dict)
        return True
    except Exception as exc:
        print(f"Erreur add_demande_firestore: {exc}")
        return False

def update_demande_firestore(demande_id: str, fields: dict) -> bool:
    db = get_firestore_client()
    if db is None:
        if demande_id in _MEMOIRE_DEMANDES:
            _MEMOIRE_DEMANDES[demande_id].update(fields)
        return True
    try:
        db.collection(COLLECTION_DEMANDES).document(demande_id).update(fields)
        return True
    except Exception as exc:
        print(f"Erreur update_demande_firestore: {exc}")
        return False

def delete_demande_firestore(demande_id: str) -> bool:
    db = get_firestore_client()
    if db is None:
        _MEMOIRE_DEMANDES.pop(demande_id, None)
        return True
    try:
        db.collection(COLLECTION_DEMANDES).document(demande_id).delete()
        return True
    except Exception as exc:
        print(f"Erreur delete_demande_firestore: {exc}")
        return False

def load_messages_data() -> pd.DataFrame:
    db = get_firestore_client()
    if db is None:
        if not _MEMOIRE_MESSAGES:
            return pd.DataFrame(columns=COLONNES_MESSAGES)
        df = pd.DataFrame(list(_MEMOIRE_MESSAGES.values()))
        if "Timestamp" in df.columns and not df.empty:
            df = df.sort_values(by="Timestamp", ascending=True).reset_index(drop=True)
        return df
    try:
        docs = db.collection(COLLECTION_MESSAGES).stream()
        data = []
        for doc in docs:
            item = doc.to_dict() or {}
            item["Message_ID"] = str(item.get("Message_ID") or doc.id).strip()
            data.append(item)
        if not data:
            return pd.DataFrame(columns=COLONNES_MESSAGES)
        df = pd.DataFrame(data)
        for c in COLONNES_MESSAGES:
            if c not in df.columns: df[c] = ""
        if "Timestamp" in df.columns and not df.empty:
            df = df.sort_values(by="Timestamp", ascending=True).reset_index(drop=True)
        return df[COLONNES_MESSAGES]
    except Exception as exc:
        print(f"Erreur load_messages_data: {exc}")
        return pd.DataFrame(columns=COLONNES_MESSAGES)

def append_message_firestore(room_id: str, sender_email: str, sender_name: str, texte: str) -> bool:
    msg_id = f"MSG_{uuid.uuid4().hex[:10].upper()}"
    msg = {
        "Message_ID": msg_id,
        "Room_ID": room_id.strip(),
        "Sender_Email": sender_email.strip().lower(),
        "Sender_Name": sender_name.strip(),
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Texte": texte.strip(),
    }
    db = get_firestore_client()
    if db is None:
        _MEMOIRE_MESSAGES[msg_id] = msg
        return True
    try:
        db.collection(COLLECTION_MESSAGES).document(msg_id).set(msg)
        return True
    except Exception as exc:
        print(f"Erreur append_message_firestore: {exc}")
        return False

# ---------------------------------------------------------------------------
# 5. MOTEUR DE MATCHING PUR (100% INTACT ET CONFORME)
# ---------------------------------------------------------------------------
def serialize_hospitals(hospitals: list[str]) -> str:
    return "; ".join([h.strip() for h in hospitals if h.strip()])

def parse_hospitals(raw_str: str) -> list[str]:
    if not raw_str or pd.isna(raw_str):
        return []
    return [h.strip() for h in str(raw_str).split(";") if h.strip()]

def build_room_id(periode: str, specialite: str, emails: list[str]) -> str:
    sorted_emails = sorted([e.strip().lower() for e in emails])
    return f"ROOM_{periode}_{specialite}_{'_'.join(sorted_emails)}"

def compute_bilateral_matches(df: pd.DataFrame) -> list[dict]:
    matches = []
    if df.empty:
        return matches
    records = [r for r in df.to_dict("records") if r.get("Statut") != "Accord trouvé"]
    n = len(records)

    for i in range(n):
        for j in range(i + 1, n):
            a, b = records[i], records[j]
            if a["Periode"] != b["Periode"] or a["Specialite"] != b["Specialite"]:
                continue
            if a["Hopital_Actuel"] == b["Hopital_Actuel"]:
                continue

            souhaites_a = set(parse_hospitals(a.get("Hopitaux_Souhaites", "")))
            souhaites_b = set(parse_hospitals(b.get("Hopitaux_Souhaites", "")))

            if (
                a["Hopital_Actuel"] in souhaites_b
                and b["Hopital_Actuel"] in souhaites_a
            ):
                room_id = build_room_id(
                    a["Periode"], a["Specialite"], [a["Email"], b["Email"]]
                )
                matches.append({
                    "room_id": room_id,
                    "periode": a["Periode"],
                    "specialite": a["Specialite"],
                    "participants": [a, b],
                    "emails": [
                        a["Email"].strip().lower(),
                        b["Email"].strip().lower(),
                    ],
                    "a": a,
                    "b": b,
                })
    return matches

def compute_triangular_matches(df: pd.DataFrame) -> list[dict]:
    matches = []
    if df.empty:
        return matches
    seen_cycles = set()
    records = [r for r in df.to_dict("records") if r.get("Statut") != "Accord trouvé"]
    n = len(records)

    souhaites_map = {
        idx: set(parse_hospitals(rec.get("Hopitaux_Souhaites", "")))
        for idx, rec in enumerate(records)
    }

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            a, b = records[i], records[j]
            if a["Periode"] != b["Periode"] or a["Specialite"] != b["Specialite"]:
                continue
            if a["Hopital_Actuel"] == b["Hopital_Actuel"]:
                continue
            if a["Hopital_Actuel"] not in souhaites_map[j]:
                continue

            for k in range(n):
                if k in (i, j):
                    continue
                c = records[k]
                if c["Periode"] != a["Periode"] or c["Specialite"] != a["Specialite"]:
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
                    id_a = f"{a['Email'].lower()}_{a['Periode']}"
                    id_b = f"{b['Email'].lower()}_{b['Periode']}"
                    id_c = f"{c['Email'].lower()}_{c['Periode']}"
                    rotations = sorted([
                        (id_a, id_b, id_c),
                        (id_b, id_c, id_a),
                        (id_c, id_a, id_b),
                    ])
                    canonical = rotations[0]
                    if canonical not in seen_cycles:
                        seen_cycles.add(canonical)
                        room_id = build_room_id(
                            a["Periode"],
                            a["Specialite"],
                            [a["Email"], b["Email"], c["Email"]],
                        )
                        matches.append({
                            "room_id": room_id,
                            "periode": a["Periode"],
                            "specialite": a["Specialite"],
                            "participants": [a, b, c],
                            "emails": [
                                a["Email"].strip().lower(),
                                b["Email"].strip().lower(),
                                c["Email"].strip().lower(),
                            ],
                            "a": a,
                            "b": b,
                            "c": c,
                        })
    return matches

def filter_private_matches_for_user(
    user_email: str | None,
    all_bilateral: list[dict],
    all_triangular: list[dict],
) -> tuple[list[dict], list[dict]]:
    if not user_email:
        return [], []
    clean_email = user_email.strip().lower()
    my_bi = [m for m in all_bilateral if clean_email in m["emails"]]
    my_tri = [t for t in all_triangular if clean_email in t["emails"]]
    return my_bi, my_tri

def build_user_notifications(
    user_email: str | None,
    my_bi: list[dict],
    my_tri: list[dict],
    df_messages: pd.DataFrame,
) -> list[dict]:
    if not user_email:
        return []
    clean_email = user_email.strip().lower()
    notifs = []
    my_rooms = set()

    for m in my_bi:
        my_rooms.add(m["room_id"])
        notifs.append({
            "titre": f"Nouvel échange direct trouvé pour {m['specialite']} ({m['periode']}) !",
            "detail": "Match bilatéral (binôme) disponible dans votre salon privé.",
            "room_id": m["room_id"],
        })

    for t in my_tri:
        my_rooms.add(t["room_id"])
        notifs.append({
            "titre": f"Cycle triangulaire trouvé pour {t['specialite']} ({t['periode']}) !",
            "detail": "Salon d'échange à 3 personnes ouvert.",
            "room_id": t["room_id"],
        })

    if not df_messages.empty and my_rooms:
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
# 6. ENVOI DES EMAILS D'ALERTE SMTP
# ---------------------------------------------------------------------------
def resolve_student_prenom(email: str, fallback_nom: str, df_utilisateurs: pd.DataFrame) -> str:
    clean_email = (email or "").strip().lower()
    if df_utilisateurs is not None and not df_utilisateurs.empty and clean_email:
        rows = df_utilisateurs[df_utilisateurs["Email"].astype(str).str.strip().str.lower() == clean_email]
        if not rows.empty:
            prenom_val = str(rows.iloc[0].get("Prenom", "")).strip()
            if prenom_val:
                return prenom_val
    if fallback_nom and str(fallback_nom).strip():
        return str(fallback_nom).strip().split()[0]
    return "Étudiant(e)"

def get_smtp_config():
    server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", 587))
    user = os.environ.get("SMTP_USERNAME", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    if not user or not password:
        return None
    return server, port, user, password

def send_match_notification_emails(
    participants: list[dict],
    periode: str,
    specialite: str,
    room_id: str,
    df_utilisateurs: pd.DataFrame,
) -> int:
    global NOTIFIED_MATCH_ROOMS
    if room_id in NOTIFIED_MATCH_ROOMS:
        return 0

    smtp_cfg = get_smtp_config()
    if not smtp_cfg:
        NOTIFIED_MATCH_ROOMS.add(room_id)
        return 0

    smtp_server, smtp_port, smtp_user, smtp_password = smtp_cfg
    sujet = "[PermutStage] Un échange de stage est disponible pour vous !"
    sent_count = 0
    seen_dest = set()

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.ehlo()
            if smtp_port in (587, 25):
                server.starttls()
                server.ehlo()
            server.login(smtp_user, smtp_password)

            for participant in participants:
                dest_email = str(participant.get("Email", "")).strip().lower()
                if not dest_email or dest_email in seen_dest:
                    continue
                seen_dest.add(dest_email)

                prenom = resolve_student_prenom(dest_email, participant.get("Nom", ""), df_utilisateurs)
                corps = (
                    f"Bonjour {prenom},\n\n"
                    f"Une opportunité d'échange direct vient de se former pour votre stage de {specialite} ({periode}) !\n\n"
                    f"Un salon de discussion privé et sécurisé a été ouvert sur PermutStage. Connectez-vous dès maintenant avec votre adresse étudiante et votre code PIN pour finaliser l'échange.\n\n"
                    f"À très vite,\n"
                    f"L'équipe PermutStage"
                )
                try:
                    msg = MIMEText(corps, "plain", "utf-8")
                    msg["Subject"] = sujet
                    msg["From"] = smtp_user
                    msg["To"] = dest_email
                    server.send_message(msg)
                    sent_count += 1
                except Exception:
                    continue

        NOTIFIED_MATCH_ROOMS.add(room_id)
        return sent_count
    except Exception as exc:
        print(f"Erreur send_match_notification_emails: {exc}")
        return sent_count

def send_pin_recovery_email(dest_email: str, prenom: str, pin: str) -> bool:
    smtp_cfg = get_smtp_config()
    if not smtp_cfg:
        raise RuntimeError("SMTP non configuré. Veuillez définir SMTP_USERNAME et SMTP_PASSWORD.")

    smtp_server, smtp_port, smtp_user, smtp_password = smtp_cfg
    pin_formatte = normalize_pin(pin)
    sujet = "[PermutStage] Récupération de votre code PIN"
    corps = (
        f"Bonjour {prenom},\n\n"
        f"Vous avez demandé la récupération de votre code PIN pour accéder à PermutStage.\n\n"
        f"Votre code PIN de connexion est : {pin_formatte}\n\n"
        f"Vous pouvez désormais vous connecter directement sur la plateforme avec votre adresse étudiante et ce code PIN.\n\n"
        f"L'équipe PermutStage"
    )

    with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
        server.ehlo()
        if smtp_port in (587, 25):
            server.starttls()
            server.ehlo()
        server.login(smtp_user, smtp_password)

        msg = MIMEText(corps, "plain", "utf-8")
        msg["Subject"] = sujet
        msg["From"] = smtp_user
        msg["To"] = dest_email.strip().lower()
        server.send_message(msg)
    return True

# ---------------------------------------------------------------------------
# 7. COMPOSANT RICHE : SÉLECTEUR D'HÔPITAUX SOUHAITÉS PAR CASES À COCHER
# ---------------------------------------------------------------------------
def render_hospital_checkbox_selector(
    selected_hospitals: list[str] = None,
    current_hospital: str = "",
    prefix: str = "depot",
):
    """
    Composant moderne et ergonomique de sélection des hôpitaux souhaités :
    A. En-tête avec compteur dynamique "(X sélectionné(s))".
    B. Bloc d'aide pastel de sélection rapide par région (+ Bruxelles (9)...).
    C. Barre de recherche textuelle fluide et sélecteur de région en direct.
    D. Liste défilable des 47 hôpitaux avec cases à cocher et blocage de l'hôpital actuel.
    """
    selected_set = set(selected_hospitals or [])
    total_hospitals = len(TOUS_LES_HOPITAUX)
    initial_count = len([h for h in selected_set if h != current_hospital])
    count_label = f"({initial_count} sélectionné{'s' if initial_count > 1 else ''})"

    # Badges de sélection rapide par région
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
    # Bouton de remise à zéro
    region_badges.append(
        Button(
            "✕ Tout désélectionner",
            type="button",
            cls="quick-badge-reset",
            onclick=f"clearAllHospitals('{prefix}')",
            title="Décocher tous les hôpitaux souhaités"
        )
    )

    # Conteneur pastel d'aide
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

    # Barre de filtre (Select Région + Recherche textuelle)
    region_options = [Option(f"Toutes les régions ({total_hospitals})", value="Toutes")]
    for reg, h_list in HOPITAUX_PAR_REGION.items():
        region_options.append(Option(f"{reg} ({len(h_list)})", value=reg))

    filter_bar = Div(
        Div(
            Label(
                "Filtrer la liste par région",
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
                "Recherche en direct",
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

    # Lignes d'hôpitaux
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
                            style="display:inline-block;" if is_current else "display:none;"
                        ),
                        style="display:flex; align-items:center; flex-wrap:wrap; gap:0.35rem; margin-right:0.75rem;"
                    ),
                    Input(
                        type="checkbox",
                        name="hopitaux_souhaites",
                        value=h,
                        checked=is_checked,
                        disabled=is_current,
                        data_region=reg,
                        data_hospital=h,
                        cls="hospital-checkbox-custom",
                        onchange=f"updateHospitalSelectionCounter('{prefix}')"
                    ),
                    style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0; width:100%; cursor:pointer;"
                ),
                id=f"hospital-row-{prefix}-{h_slug}",
                cls=f"hospital-row-item {'is-current-hospital' if is_current else ''}",
                data_region=reg,
                data_hospital=h.lower(),
            )
        )

    # Conteneur défilable
    scroll_container = Div(
        Div(*rows, id=f"hospital-list-{prefix}"),
        id=f"hospital-scroll-{prefix}",
        cls="hospital-scroll-container"
    )

    # Légende en bas
    bottom_helper = Div(
        Small(
            Span(f"{total_hospitals} hôpitaux affichés", id=f"visible-count-{prefix}"),
            " · Cliquez sur n'importe quelle ligne pour cocher ou décocher.",
            style="color:#64748b; font-size:0.78rem;"
        ),
        style="margin-top:0.4rem; display:flex; justify-content:space-between; align-items:center;"
    )

    # Script interactif client
    js_script = Script(f"""
    function updateHospitalSelectionCounter(prefix) {{
        const list = document.getElementById('hospital-list-' + prefix);
        if (!list) return;
        const checkboxes = list.querySelectorAll('input[type="checkbox"][name="hopitaux_souhaites"]:checked:not(:disabled)');
        const count = checkboxes.length;
        const counterEl = document.getElementById('selected-counter-' + prefix);
        if (counterEl) {{
            counterEl.textContent = '(' + count + (count <= 1 ? ' sélectionné' : ' sélectionnés') + ')';
            if (count > 0) {{
                counterEl.classList.add('has-selected');
            }} else {{
                counterEl.classList.remove('has-selected');
            }}
        }}
    }}

    function toggleRegionHospitals(region, prefix) {{
        const list = document.getElementById('hospital-list-' + prefix);
        if (!list) return;
        const checkboxes = list.querySelectorAll('input[type="checkbox"][data-region="' + region + '"]:not(:disabled)');
        let allChecked = true;
        checkboxes.forEach(cb => {{ if (!cb.checked) allChecked = false; }});
        checkboxes.forEach(cb => {{ cb.checked = !allChecked; }});
        updateHospitalSelectionCounter(prefix);
    }}

    function clearAllHospitals(prefix) {{
        const list = document.getElementById('hospital-list-' + prefix);
        if (!list) return;
        const checkboxes = list.querySelectorAll('input[type="checkbox"]:not(:disabled)');
        checkboxes.forEach(cb => {{ cb.checked = false; }});
        updateHospitalSelectionCounter(prefix);
    }}

    function filterHospitals(prefix) {{
        const list = document.getElementById('hospital-list-' + prefix);
        const searchInput = document.getElementById('search-hospital-' + prefix);
        const regionSelect = document.getElementById('filter-region-' + prefix);
        const visibleCountEl = document.getElementById('visible-count-' + prefix);
        if (!list) return;

        const q = searchInput ? searchInput.value.toLowerCase().trim() : '';
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
# 8. EN-TÊTE & PIED DE PAGE GLOBAUX
# ---------------------------------------------------------------------------
def render_header(session, active_tab="accueil"):
    user_email = session.get("email")
    user_prenom = session.get("prenom")
    user_nom = session.get("nom")
    is_admin = session.get("is_admin", False)

    df_demandes = load_demandes_data()
    df_messages = load_messages_data()
    all_bi = compute_bilateral_matches(df_demandes)
    all_tri = compute_triangular_matches(df_demandes)
    my_bi, my_tri = filter_private_matches_for_user(user_email, all_bi, all_tri)
    nb_mes_matchs = len(my_bi) + len(my_tri)
    notifs = build_user_notifications(user_email, my_bi, my_tri, df_messages)

    tabs = [
        ("accueil", "Accueil & Guide", "/"),
        ("deposer", "1. Déposer une demande", "/deposer"),
        ("matchs", f"2. Mes Matchs & Salons ({nb_mes_matchs})", "/matchs"),
        ("catalogue", f"3. Catalogue public ({len(df_demandes)})", "/catalogue"),
        ("gerer", "4. Gérer mon offre", "/gerer"),
    ]
    if is_admin:
        tabs.append(("admin", "🛠️ Administration", "/admin"))

    nav_items = [
        Li(A(label, href=url, cls=f"nav-tab-btn {'active' if key == active_tab else ''}"))
        for key, label, url in tabs
    ]

    if user_email:
        auth_section = Div(
            Span(
                f"👤 {user_prenom} {user_nom}",
                style="font-weight:700; font-size:0.85rem; color:#1e293b; background:#f1f5f9; padding:0.35rem 0.75rem; border-radius:9999px; margin-right:0.6rem; border:1px solid #e2e8f0;"
            ),
            A(
                f"🔔 ({len(notifs)})",
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
        Div(
            Nav(
                Ul(
                    Li(
                        A(
                            Strong("PermutStage", cls="brand-title"),
                            Span("Master 2 Médecine", cls="brand-subtitle"),
                            href="/"
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
            P("Plateforme collaborative de permutation de stages hospitaliers · Promotion Médecine 2028 · FastHTML & Firebase Firestore"),
            Small("Conception épurée avec Pico.css · Confidentialité absolue des données étudiantes"),
            A("🔒 Accès Administrateur", href="/admin-login-view", style="display:block; margin-top:0.5rem; font-size:0.75rem; color:#94a3b8; text-decoration:none;"),
            style="text-align: center; color: #64748b; font-size: 0.82rem; padding: 2rem 0 1rem 0;"
        ),
        cls="container-fluid"
    )

# ---------------------------------------------------------------------------
# 9. ROUTES DE L'APPLICATION (LES 5 VUES + AUTH + ADMIN)
# ---------------------------------------------------------------------------

# === VUE 1 : ACCUEIL & GUIDE ===
@rt("/")
def get(session):
    df_demandes = load_demandes_data()
    df_users = load_users_data()
    all_bi = compute_bilateral_matches(df_demandes)
    all_tri = compute_triangular_matches(df_demandes)

    return Main(
        render_header(session, "accueil"),
        Div(
            Div(
                Div("✨ PROMOTION MÉDECINE 2028 · MASTER 2", cls="hero-badge"),
                H1("Trouvez votre binôme de stage idéal en quelques clics", style="font-size:2.1rem; font-weight:800;"),
                P(
                    "Bienvenue sur PermutStage, l'application pensée pour fluidifier, simplifier et centraliser les échanges de lieux de stages hospitaliers. "
                    "Vos souhaits sont analysés en temps réel par notre algorithme de permutation, dans le respect le plus strict de votre confidentialité.",
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
                Div(Div(str(len(df_demandes)), cls="stat-val"), Div("Offres déposées", cls="stat-lbl"), cls="stat-card"),
                Div(Div(str(len(all_bi)), cls="stat-val"), Div("Matchs bilatéraux (A ↔ B)", cls="stat-lbl"), cls="stat-card"),
                Div(Div(str(len(all_tri)), cls="stat-val"), Div("Cycles triangulaires (3)", cls="stat-lbl"), cls="stat-card"),
                style="display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:1rem; margin-bottom:2rem;"
            ),
            # Les 4 étapes
            H3("🧭 Le parcours en 4 étapes simples", style="font-weight:800; color:#0f172a; margin-bottom:1rem;"),
            Div(
                Article(
                    Strong("1. Créer son profil"),
                    P("Nom, prénom, email institutionnel et code PIN à 4 chiffres. Aucun mot de passe complexe à mémoriser.", style="font-size:0.85rem; color:#475569; margin-top:0.35rem;"),
                ),
                Article(
                    Strong("2. Déposer son offre"),
                    P("Indiquez votre stage actuel (période P3 à P8, spécialité, hôpital) et cochez facilement vos hôpitaux souhaités par région.", style="font-size:0.85rem; color:#475569; margin-top:0.35rem;"),
                ),
                Article(
                    Strong("3. Calcul des correspondances"),
                    P("L'algorithme détecte en continu les cycles bilatéraux (A ↔ B) et triangulaires (A → B → C → A).", style="font-size:0.85rem; color:#475569; margin-top:0.35rem;"),
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
                        Li(Strong("Même période obligatoire : "), "P3 contre P3, P4 contre P4, etc."),
                        Li(Strong("Même spécialité obligatoire : "), "Pédiatrie contre Pédiatrie, Chirurgie contre Chirurgie."),
                        Li(Strong("Validation facultaire : "), "L'accord trouvé sur l'application reste un accord de principe à soumettre à la commission des stages.")
                    )
                ),
                Article(
                    H4("🔒 Confidentialité garantie", style="color:#0f172a; font-weight:700;"),
                    Ul(
                        Li(Strong("Code PIN 4 chiffres : "), "Connexion rapide sans stockage de mot de passe sensible."),
                        Li(Strong("Hermétisme complet : "), "Aucun camarade externe ne peut voir qui permute avec qui."),
                        Li(Strong("Salons chiffrés par cycle : "), "Seuls les membres du match accèdent à la messagerie.")
                    )
                ),
                style="display:grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap:1rem;"
            ),
            cls="container"
        ),
        render_footer()
    )

# === VUE 2 : DÉPOSER UNE DEMANDE ===
@rt("/deposer")
def get(session):
    user_email = session.get("email")
    user_prenom = session.get("prenom")
    user_nom = session.get("nom")

    if not user_email:
        return Main(
            render_header(session, "deposer"),
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

    default_actuel = TOUS_LES_HOPITAUX[0]

    return Main(
        render_header(session, "deposer"),
        Div(
            H2("Déposer une nouvelle offre de permutation", style="font-weight:800; color:#0f172a;"),
            P("Vos coordonnées sont automatiquement verrouillées sur votre profil étudiant connecté. Notre algorithme calculera vos correspondances en temps réel."),
            Div(id="depot-feedback"),
            Form(
                Div(
                    Div(
                        Label("Nom complet (verrouillé)", Input(value=f"{user_prenom} {user_nom}", disabled=True, style="background:#f8fafc;")),
                        Label("Email institutionnel (verrouillé)", Input(value=user_email, disabled=True, style="background:#f8fafc;")),
                    ),
                    Div(
                        Label("Période de stage *", Select(*[Option(p, value=p) for p in PERIODES], name="periode", required=True)),
                        Label("Spécialité *", Select(*[Option(s, value=s) for s in SPECIALITES], name="specialite", required=True)),
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
                # Nouveau sélecteur moderne d'hôpitaux souhaités par cases à cocher
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
async def post(session, req: Request = None, periode: str = "", specialite: str = "", hopital_actuel: str = "", hopitaux_souhaites: list[str] = None):
    user_email = session.get("email")
    user_nom = f"{session.get('prenom', '')} {session.get('nom', '')}".strip()
    user_pin = session.get("pin", "")

    if not user_email:
        return Article(P("Session expirée. Veuillez vous reconnecter.", style="color:#b91c1c; font-weight:600;"), cls="contrast")

    # Extraction robuste des cases à cocher multiples
    h_list = []
    if req is not None:
        try:
            form_data = await req.form()
            h_list = form_data.getlist("hopitaux_souhaites")
            if not periode:
                periode = form_data.get("periode", "")
            if not specialite:
                specialite = form_data.get("specialite", "")
            if not hopital_actuel:
                hopital_actuel = form_data.get("hopital_actuel", "")
        except Exception:
            pass

    if not h_list and hopitaux_souhaites:
        h_list = [hopitaux_souhaites] if isinstance(hopitaux_souhaites, str) else list(hopitaux_souhaites)

    h_list = [h.strip() for h in h_list if h and h.strip()]

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

    df_demandes = load_demandes_data()
    if not df_demandes.empty:
        doublon = df_demandes[
            (df_demandes["Email"].str.lower() == user_email.lower())
            & (df_demandes["Periode"] == periode)
        ]
        if not doublon.empty:
            return Article(
                P(f"Vous avez déjà une offre active sur la période {periode}. Modifiez-la dans l'onglet 'Gérer mon offre'.", style="color:#b91c1c; font-weight:700; margin:0;"),
                style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:10px; margin-bottom:1rem;"
            )

    df_users = load_users_data()
    all_bi_avant = compute_bilateral_matches(df_demandes)
    all_tri_avant = compute_triangular_matches(df_demandes)
    anciens_rooms = {m["room_id"] for m in all_bi_avant} | {t["room_id"] for t in all_tri_avant}

    nouvelle_demande = {
        "Demande_ID": f"DEM_{uuid.uuid4().hex[:10].upper()}",
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Nom": user_nom,
        "Email": user_email.lower(),
        "PIN": user_pin,
        "Periode": periode,
        "Specialite": specialite,
        "Hopital_Actuel": hopital_actuel,
        "Hopitaux_Souhaites": serialize_hospitals(h_list),
        "Statut": "Disponible",
    }

    if add_demande_firestore(nouvelle_demande):
        df_maj = pd.concat([df_demandes, pd.DataFrame([nouvelle_demande])], ignore_index=True)
        # Déclenchement automatique des alertes emails
        nouveaux_bi = compute_bilateral_matches(df_maj)
        nouveaux_tri = compute_triangular_matches(df_maj)
        for m in nouveaux_bi:
            if m["room_id"] not in anciens_rooms:
                send_match_notification_emails(m["participants"], m["periode"], m["specialite"], m["room_id"], df_users)
        for t in nouveaux_tri:
            if t["room_id"] not in anciens_rooms:
                send_match_notification_emails(t["participants"], t["periode"], t["specialite"], t["room_id"], df_users)

        return Article(
            H4("🎉 Offre publiée avec succès !", style="color:#14532d; font-weight:800; margin-bottom:0.4rem;"),
            P(f"Votre demande pour le stage de {specialite} en {periode} ({hopital_actuel}) a été publiée avec {len(h_list)} hôpital(ux) souhaité(s)."),
            A("Consulter mes correspondances", href="/matchs", role="button", cls="primary", style="margin-top:0.5rem; border-radius:8px;"),
            style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:1.25rem; border-radius:12px; margin-bottom:1.5rem;"
        )
    else:
        return Article(P("Erreur lors de l'enregistrement dans la base de données. Veuillez réessayer.", style="color:#b91c1c;"), cls="contrast")

# === VUE 3 : MES MATCHS & SALONS PRIVÉS (CONFIDENTIALITÉ STRICTE) ===
@rt("/matchs")
def get(session):
    user_email = session.get("email")
    if not user_email:
        return Main(
            render_header(session, "matchs"),
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

    df_demandes = load_demandes_data()
    df_messages = load_messages_data()
    all_bi = compute_bilateral_matches(df_demandes)
    all_tri = compute_triangular_matches(df_demandes)
    my_bi, my_tri = filter_private_matches_for_user(user_email, all_bi, all_tri)

    bi_sections = []
    if not my_bi:
        bi_sections.append(P("Aucun match bilatéral direct ne vous concerne actuellement.", style="color:#64748b; font-style:italic;"))
    else:
        for m in my_bi:
            a, b = m["a"], m["b"]
            room_id = m["room_id"]
            msgs_salon = df_messages[df_messages["Room_ID"] == room_id] if not df_messages.empty else pd.DataFrame()
            chat_elements = []
            for _, msg in msgs_salon.iterrows():
                is_me = msg["Sender_Email"].strip().lower() == user_email.lower()
                chat_elements.append(
                    Div(
                        Strong(msg["Sender_Name"]),
                        Small(f" · {msg['Timestamp']}", style="font-size:0.75rem; opacity:0.8;"),
                        P(msg["Texte"], style="margin:0.2rem 0 0 0;"),
                        cls=f"chat-bubble {'chat-me' if is_me else 'chat-other'}"
                    )
                )

            bi_sections.append(
                Article(
                    Div(
                        Strong(f"MATCH PRIVÉ BILATÉRAL · {m['periode']} · {m['specialite']}", style="color:#166534; font-size:0.95rem; font-weight:800;"),
                        Span("Binôme direct", cls="status-badge status-disponible", style="float:right;"),
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
                    Details(
                        Summary(f"💬 Salon de discussion privé ({len(msgs_salon)} messages)"),
                        Div(
                            Div(*chat_elements, id=f"chat-box-{room_id}", style="max-height:220px; overflow-y:auto; margin:0.75rem 0; padding:0.6rem; background:#ffffff; border-radius:10px; border:1px solid #e2e8f0;"),
                            Form(
                                Div(
                                    Input(name="texte", placeholder="Écrire un message dans ce salon privé...", required=True, style="margin-bottom:0;"),
                                    Input(type="hidden", name="room_id", value=room_id),
                                    Button("Envoyer", type="submit", cls="primary", style="margin-bottom:0; width:auto; border-radius:8px;"),
                                    style="display:flex; gap:0.5rem;"
                                ),
                                hx_post="/post-chat-message",
                                hx_target=f"#chat-box-{room_id}",
                                hx_swap="innerHTML"
                            ),
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
            msgs_salon = df_messages[df_messages["Room_ID"] == room_id] if not df_messages.empty else pd.DataFrame()
            chat_elements = []
            for _, msg in msgs_salon.iterrows():
                is_me = msg["Sender_Email"].strip().lower() == user_email.lower()
                chat_elements.append(
                    Div(
                        Strong(msg["Sender_Name"]),
                        Small(f" · {msg['Timestamp']}", style="font-size:0.75rem; opacity:0.8;"),
                        P(msg["Texte"], style="margin:0.2rem 0 0 0;"),
                        cls=f"chat-bubble {'chat-me' if is_me else 'chat-other'}"
                    )
                )

            tri_sections.append(
                Article(
                    Div(
                        Strong(f"MATCH PRIVÉ TRIANGULAIRE · {t['periode']} · {t['specialite']}", style="color:#064e3b; font-size:0.95rem; font-weight:800;"),
                        Span("Cycle à 3", cls="status-badge status-accord", style="float:right;"),
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
                    Details(
                        Summary(f"💬 Salon de discussion privé ({len(msgs_salon)} messages)"),
                        Div(
                            Div(*chat_elements, id=f"chat-box-{room_id}", style="max-height:220px; overflow-y:auto; margin:0.75rem 0; padding:0.6rem; background:#ffffff; border-radius:10px; border:1px solid #e2e8f0;"),
                            Form(
                                Div(
                                    Input(name="texte", placeholder="Écrire un message aux collègues du cycle...", required=True, style="margin-bottom:0;"),
                                    Input(type="hidden", name="room_id", value=room_id),
                                    Button("Envoyer", type="submit", cls="primary", style="margin-bottom:0; width:auto; border-radius:8px;"),
                                    style="display:flex; gap:0.5rem;"
                                ),
                                hx_post="/post-chat-message",
                                hx_target=f"#chat-box-{room_id}",
                                hx_swap="innerHTML"
                            ),
                            style="margin-top:0.5rem;"
                        )
                    ),
                    cls="tri-card"
                )
            )

    return Main(
        render_header(session, "matchs"),
        Div(
            H2("Mes correspondances privées & Salons de discussion", style="font-weight:800; color:#0f172a;"),
            P(f"Affichage strictement réservé à votre profil ({user_email}). Aucun camarade extérieur ne peut visualiser vos opportunités."),
            Div(
                Div(H3(f"Binômes bilatéraux ({len(my_bi)})", style="font-size:1.15rem; font-weight:700;"), *bi_sections),
                Div(H3(f"Cycles triangulaires ({len(my_tri)})", style="font-size:1.15rem; font-weight:700;"), *tri_sections),
                style="display:grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap:1.5rem;"
            ),
            cls="container"
        ),
        render_footer()
    )

@rt("/post-chat-message")
def post(session, room_id: str, texte: str):
    user_email = session.get("email")
    user_name = f"{session.get('prenom', '')} {session.get('nom', '')}".strip() or user_email
    if not user_email or not texte.strip():
        return ""

    append_message_firestore(room_id, user_email, user_name, texte.strip())
    df_messages = load_messages_data()
    msgs_salon = df_messages[df_messages["Room_ID"] == room_id] if not df_messages.empty else pd.DataFrame()

    elements = []
    for _, msg in msgs_salon.iterrows():
        is_me = msg["Sender_Email"].strip().lower() == user_email.lower()
        elements.append(
            Div(
                Strong(msg["Sender_Name"]),
                Small(f" · {msg['Timestamp']}", style="font-size:0.75rem; opacity:0.8;"),
                P(msg["Texte"], style="margin:0.2rem 0 0 0;"),
                cls=f"chat-bubble {'chat-me' if is_me else 'chat-other'}"
            )
        )
    return Div(*elements)

# === VUE 4 : CATALOGUE PUBLIC (ANONYMISÉ PAR CONFIDENTIALITÉ) ===
@rt("/catalogue")
def get(session, f_periode: str = "Toutes", f_specialite: str = "Toutes", f_region: str = "Toutes", q: str = ""):
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
            souhaites_str = ", ".join(parse_hospitals(row.get("Hopitaux_Souhaites", "")))
            region_act = HOPITAL_VERS_REGION.get(row.get("Hopital_Actuel", ""), "Autre")
            statut = row.get("Statut", "Disponible")
            st_class = "status-disponible" if statut == "Disponible" else ("status-discussion" if statut == "En discussion" else "status-accord")

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
                        style="font-size:0.9rem; margin-bottom:0.4rem; line-height:1.5;"
                    ),
                    Small(f"Mis à jour le {row.get('Timestamp', '')} · Identité protégée par confidentialité", style="color:#94a3b8; font-size:0.75rem;"),
                    style="margin-bottom:0.75rem; background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:1.15rem;"
                )
            )

    filtres_form = Form(
        Div(
            Div(Label("Période", Select(Option("Toutes", value="Toutes", selected=(f_periode=="Toutes")), *[Option(p, value=p, selected=(f_periode==p)) for p in PERIODES], name="f_periode", onchange="this.form.submit()"))),
            Div(Label("Spécialité", Select(Option("Toutes", value="Toutes", selected=(f_specialite=="Toutes")), *[Option(s, value=s, selected=(f_specialite==s)) for s in SPECIALITES], name="f_specialite", onchange="this.form.submit()"))),
            Div(Label("Région hôpital actuel", Select(Option("Toutes", value="Toutes", selected=(f_region=="Toutes")), *[Option(r, value=r, selected=(f_region==r)) for r in REGIONS], name="f_region", onchange="this.form.submit()"))),
            Div(Label("Recherche libre", Input(name="q", value=q, placeholder="Ex: Saint Luc, Namur...", oninput="this.form.submit()"))),
            style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:1rem; margin-bottom:1.5rem;"
        ),
        method="get",
        action="/catalogue"
    )

    return Main(
        render_header(session, "catalogue"),
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
def get(session):
    user_email = session.get("email")
    if not user_email:
        return Main(
            render_header(session, "gerer"),
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

    df_demandes = load_demandes_data()
    mes_offres = df_demandes[df_demandes["Email"].str.lower() == user_email.lower()] if not df_demandes.empty else pd.DataFrame()

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
            d_id = row["Demande_ID"]
            cur_periode = row["Periode"]
            cur_spec = row["Specialite"]
            cur_actuel = row["Hopital_Actuel"]
            cur_souhaites = parse_hospitals(row["Hopitaux_Souhaites"])
            cur_statut = row.get("Statut", "Disponible")
            edit_prefix = f"edit-{slugify(d_id)}"

            edit_form = Form(
                Input(type="hidden", name="demande_id", value=d_id),
                Div(
                    Div(Label("Période", Select(*[Option(p, value=p, selected=(p==cur_periode)) for p in PERIODES], name="periode"))),
                    Div(Label("Spécialité", Select(*[Option(s, value=s, selected=(s==cur_spec)) for s in SPECIALITES], name="specialite"))),
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
                # Sélecteur d'hôpitaux souhaités moderne pour la modification
                render_hospital_checkbox_selector(selected_hospitals=cur_souhaites, current_hospital=cur_actuel, prefix=edit_prefix),
                Div(
                    Button("Enregistrer les modifications", type="submit", cls="primary", style="border-radius:8px; font-weight:700;"),
                    style="margin-top:1rem;"
                ),
                hx_post="/modifier-demande",
                hx_target=f"#feedback-{d_id}",
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
                hx_target=f"#offre-container-{d_id}",
                hx_swap="outerHTML"
            )

            offres_blocks.append(
                Div(
                    Article(
                        H3(f"📌 {cur_periode} · {cur_spec} ({cur_actuel})", style="font-weight:800; color:#1e3a8a;"),
                        Div(id=f"feedback-{d_id}"),
                        H5("Modifier l'annonce", style="font-weight:700; margin-top:1rem;"),
                        edit_form,
                        Hr(),
                        H5("Supprimer l'annonce", style="font-weight:700; color:#b91c1c;"),
                        delete_form,
                    ),
                    id=f"offre-container-{d_id}",
                    style="margin-bottom:1.5rem;"
                )
            )

    return Main(
        render_header(session, "gerer"),
        Div(
            H2("Gérer mes annonces publiées", style="font-weight:800; color:#0f172a;"),
            P("Vous pouvez ajuster vos souhaits à tout moment ou modifier le statut de votre offre ('Disponible', 'En discussion', 'Accord trouvé')."),
            *offres_blocks,
            cls="container"
        ),
        render_footer()
    )

@rt("/modifier-demande")
async def post(session, req: Request = None, demande_id: str = "", periode: str = "", specialite: str = "", hopital_actuel: str = "", statut: str = "Disponible", hopitaux_souhaites: list[str] = None):
    user_email = session.get("email")
    if not user_email:
        return P("Session expirée.", style="color:#b91c1c; font-weight:600;")

    h_list = []
    if req is not None:
        try:
            form_data = await req.form()
            h_list = form_data.getlist("hopitaux_souhaites")
            if not demande_id: demande_id = form_data.get("demande_id", "")
            if not periode: periode = form_data.get("periode", "")
            if not specialite: specialite = form_data.get("specialite", "")
            if not hopital_actuel: hopital_actuel = form_data.get("hopital_actuel", "")
            if not statut: statut = form_data.get("statut", "Disponible")
        except Exception:
            pass

    if not h_list and hopitaux_souhaites:
        h_list = [hopitaux_souhaites] if isinstance(hopitaux_souhaites, str) else list(hopitaux_souhaites)

    h_list = [h.strip() for h in h_list if h and h.strip()]

    if not h_list:
        return P("Veuillez conserver au moins un hôpital souhaité.", style="color:#b91c1c; font-weight:600;")
    if hopital_actuel in h_list:
        return P("L'hôpital actuel ne peut pas figurer dans les hôpitaux souhaités.", style="color:#b91c1c; font-weight:600;")

    update_fields = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Periode": periode,
        "Specialite": specialite,
        "Hopital_Actuel": hopital_actuel,
        "Hopitaux_Souhaites": serialize_hospitals(h_list),
        "Statut": statut,
    }

    if update_demande_firestore(demande_id, update_fields):
        return Article(
            P("✅ Offre mise à jour avec succès dans Firestore !"),
            style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:0.75rem; margin-bottom:1rem; border-radius:8px;"
        )
    return P("Erreur lors de la mise à jour.", style="color:#b91c1c;")

@rt("/supprimer-demande")
def post(session, demande_id: str, confirm_delete: str = None):
    user_email = session.get("email")
    if not user_email or not confirm_delete:
        return P("Suppression annulée ou non autorisée.", style="color:#b91c1c;")

    if delete_demande_firestore(demande_id):
        return Article(
            P("🗑️ Votre offre a été supprimée avec succès."),
            style="background:#fef2f2; border:1px solid #fecaca; color:#991b1b; padding:1rem; border-radius:10px;"
        )
    return P("Erreur lors de la suppression.", style="color:#b91c1c;")

# === AUTHENTIFICATION & COMPTE ÉTUDIANT ===
@rt("/login-view")
def get(session):
    return Main(
        render_header(session),
        Div(
            Div(
                Article(
                    H3("🔑 Connexion Étudiant", style="font-weight:700; color:#0f172a;"),
                    P("Accédez à vos correspondances privées et vos salons sécurisés."),
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
                    P("Inscription rapide en 30 secondes sans mot de passe complexe."),
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
                        hx_post="/register",
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

@rt("/login")
def post(session, email: str, pin: str):
    em_clean = email.strip().lower()
    pin_clean = normalize_pin(pin)

    df_users = load_users_data()
    matched = df_users[df_users["Email"].astype(str).str.strip().str.lower() == em_clean] if not df_users.empty else pd.DataFrame()

    if matched.empty:
        return Article(P("Email ou code PIN incorrect.", style="color:#b91c1c; font-weight:600;"), cls="contrast")

    u_row = matched.iloc[0]
    pin_bdd = normalize_pin(u_row.get("PIN", ""))

    if pin_clean == pin_bdd:
        session["user_id"] = str(u_row.get("User_ID", "")).strip()
        session["email"] = em_clean
        session["prenom"] = str(u_row.get("Prenom", "")).strip()
        session["nom"] = str(u_row.get("Nom", "")).strip()
        session["pin"] = pin_bdd
        return Article(
            P(f"Connexion réussie ! Bienvenue {session['prenom']}."),
            A("Accéder à mes correspondances", href="/matchs", role="button", cls="primary", style="border-radius:8px;"),
            style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:1rem; border-radius:10px;"
        )
    return Article(P("Email ou code PIN incorrect.", style="color:#b91c1c; font-weight:600;"), cls="contrast")

@rt("/register")
def post(session, prenom: str, nom: str, email: str, pin: str):
    p_clean = prenom.strip()
    n_clean = nom.strip()
    e_clean = email.strip().lower()
    pin_clean = normalize_pin(pin)

    if len(p_clean) < 2 or len(n_clean) < 2:
        return P("Veuillez renseigner un prénom et un nom valides.", style="color:#b91c1c;")
    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", e_clean):
        return P("Format d'adresse email invalide.", style="color:#b91c1c;")
    if not re.match(r"^\d{4}$", pin_clean):
        return P("Le code PIN doit comporter exactement 4 chiffres.", style="color:#b91c1c;")

    df_users = load_users_data()
    if not df_users.empty and not df_users[df_users["Email"].astype(str).str.strip().str.lower() == e_clean].empty:
        return P("Un compte existe déjà avec cette adresse email.", style="color:#b91c1c;")

    new_user = {
        "User_ID": f"USR_{uuid.uuid4().hex[:8].upper()}",
        "Nom": n_clean,
        "Prenom": p_clean,
        "Email": e_clean,
        "PIN": pin_clean,
        "Date_Inscription": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    if create_user_firestore(new_user):
        session["user_id"] = new_user["User_ID"]
        session["email"] = e_clean
        session["prenom"] = p_clean
        session["nom"] = n_clean
        session["pin"] = pin_clean
        return Article(
            P(f"🎉 Compte créé avec succès ! Bienvenue {p_clean}."),
            A("Déposer ma première offre", href="/deposer", role="button", cls="primary", style="border-radius:8px;"),
            style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:1rem; border-radius:10px;"
        )
    return P("Erreur lors de la création du compte.", style="color:#b91c1c;")

@rt("/forgot-pin-view")
def get(session):
    return Main(
        render_header(session),
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
def post(session, email: str):
    em_clean = email.strip().lower()
    df_users = load_users_data()
    matched = df_users[df_users["Email"].astype(str).str.strip().str.lower() == em_clean] if not df_users.empty else pd.DataFrame()

    if matched.empty:
        return P("Aucun compte n'est associé à cette adresse email.", style="color:#b91c1c;")

    row = matched.iloc[0]
    pin = normalize_pin(row.get("PIN", ""))
    prenom = str(row.get("Prenom", "")).strip() or "étudiant"

    try:
        send_pin_recovery_email(em_clean, prenom, pin)
        return Article(
            P(f"✅ Votre code PIN a été envoyé à {em_clean}."),
            A("Se connecter", href="/login-view", role="button", cls="outline", style="border-radius:8px;"),
            style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:1rem; border-radius:10px;"
        )
    except Exception as err:
        return P(f"Impossible d'envoyer l'email : {err}", style="color:#b91c1c;")

@rt("/notifications")
def get(session):
    user_email = session.get("email")
    if not user_email:
        return RedirectResponse("/login-view")

    df_demandes = load_demandes_data()
    df_messages = load_messages_data()
    all_bi = compute_bilateral_matches(df_demandes)
    all_tri = compute_triangular_matches(df_demandes)
    my_bi, my_tri = filter_private_matches_for_user(user_email, all_bi, all_tri)
    notifs = build_user_notifications(user_email, my_bi, my_tri, df_messages)

    cards = []
    if not notifs:
        cards.append(Article(P("Aucune nouvelle notification pour le moment.")))
    else:
        for n in notifs:
            cards.append(
                Article(
                    Strong(n["titre"], style="color:#1e3a8a; display:block; margin-bottom:0.3rem; font-size:0.95rem;"),
                    P(n["detail"], style="font-size:0.9rem; color:#334155; margin-bottom:0.5rem;"),
                    A("Ouvrir le salon correspondant", href="/matchs", role="button", cls="outline secondary", style="font-size:0.8rem; padding:0.35rem 0.75rem; border-radius:6px;"),
                    style="margin-bottom:0.75rem; border-left:4px solid #1d4ed8; border-radius:8px;"
                )
            )

    return Main(
        render_header(session),
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
    return RedirectResponse("/")

# === VUE 6 : ESPACE ADMINISTRATION ===
@rt("/admin-login-view")
def get(session):
    return Main(
        render_header(session),
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
def post(session, password: str):
    admin_pwd = os.environ.get("ADMIN_PASSWORD", "admin123")
    if password.strip() == admin_pwd.strip():
        session["is_admin"] = True
        return Article(
            P("Accès accordé."),
            A("Ouvrir l'Espace Administrateur", href="/admin", role="button", cls="primary", style="border-radius:8px;"),
            style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:1rem; border-radius:10px;"
        )
    return P("Mot de passe incorrect.", style="color:#b91c1c;")

@rt("/admin")
def get(session):
    if not session.get("is_admin", False):
        return RedirectResponse("/admin-login-view")

    df_users = load_users_data()
    df_demandes = load_demandes_data()
    all_bi = compute_bilateral_matches(df_demandes)
    all_tri = compute_triangular_matches(df_demandes)

    demandes_rows = []
    for _, d in df_demandes.iterrows():
        demandes_rows.append(
            Tr(
                Td(Small(d.get("Demande_ID", ""))),
                Td(d.get("Nom", "")),
                Td(d.get("Email", "")),
                Td(d.get("Periode", "")),
                Td(d.get("Specialite", "")),
                Td(d.get("Hopital_Actuel", "")),
                Td(Span(d.get("Statut", "Disponible"), cls=f"status-badge status-{d.get('Statut', 'Disponible').lower().replace(' ', '')}")),
                Td(
                    Form(
                        Input(type="hidden", name="demande_id", value=d.get("Demande_ID", "")),
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
        users_rows.append(
            Tr(
                Td(Small(u.get("User_ID", ""))),
                Td(f"{u.get('Prenom', '')} {u.get('Nom', '')}"),
                Td(u.get("Email", "")),
                Td(u.get("Date_Inscription", "")),
                Td(
                    Form(
                        Input(type="hidden", name="user_id", value=u.get("User_ID", "")),
                        Button("Supprimer", type="submit", cls="outline secondary", style="padding:0.25rem 0.5rem; font-size:0.75rem; color:#b91c1c; border-color:#b91c1c; border-radius:6px;"),
                        hx_post="/admin-delete-user",
                        hx_target="#admin-feedback",
                        hx_swap="innerHTML"
                    )
                )
            )
        )

    return Main(
        render_header(session, "admin"),
        Div(
            H2("🛠️ Espace Administrateur (Supervision globale)", style="font-weight:800; color:#0f172a;"),
            Div(id="admin-feedback"),
            Div(
                Div(Div(str(len(df_users)), cls="stat-val"), Div("Comptes étudiants", cls="stat-lbl"), cls="stat-card"),
                Div(Div(str(len(df_demandes)), cls="stat-val"), Div("Offres actives", cls="stat-lbl"), cls="stat-card"),
                Div(Div(str(len(all_bi)), cls="stat-val"), Div("Matchs binômes", cls="stat-lbl"), cls="stat-card"),
                Div(Div(str(len(all_tri)), cls="stat-val"), Div("Boucles triangulaires", cls="stat-lbl"), cls="stat-card"),
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
                        Thead(Tr(Th("User ID"), Th("Nom complet"), Th("Email"), Th("Inscription"), Th("Action"))),
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
    if delete_demande_firestore(demande_id):
        return Article(P(f"Demande {demande_id} supprimée."), style="background:#fef2f2; color:#991b1b; padding:0.5rem; border-radius:6px;")
    return P("Erreur", style="color:#b91c1c;")

@rt("/admin-delete-user")
def post(session, user_id: str):
    if not session.get("is_admin", False):
        return P("Non autorisé", style="color:#b91c1c;")
    if delete_user_firestore(user_id):
        return Article(P(f"Utilisateur {user_id} et ses demandes supprimés."), style="background:#fef2f2; color:#991b1b; padding:0.5rem; border-radius:6px;")
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
        headers={"Content-Disposition": f"attachment; filename=permutstage_demandes_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"}
    )

# ---------------------------------------------------------------------------
# 10. DÉMARRAGE DU SERVEUR FASTHTML
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    serve()
