"""
PermutStage — Plateforme Collaborative d'Échange de Lieux de Stage (Médecine P3 à P8)
Version FastHTML (python-fasthtml) & Firebase Firestore (firebase-admin).

Architecture complète dans un fichier unique main.py :
- Interface FastHTML avec Pico.css natif (Pico=True) et requêtes HTMX réactives sans rechargement lourd.
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
# 1. INITIALISATION DE L'APPLICATION FASTHTML (Pico.css + Live Reload)
# ---------------------------------------------------------------------------
CUSTOM_STYLE = Style("""
    :root {
        --pico-font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
        --pico-primary: #1d4ed8;
        --pico-primary-background: #1d4ed8;
        --pico-primary-hover: #1e40af;
        --pico-primary-focus: rgba(29, 78, 216, 0.2);
    }
    body {
        background-color: #f8fafc;
        color: #0f172a;
    }
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
    .match-card {
        background-color: #f0fdf4;
        border: 1px solid #86efac;
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        color: #14532d;
    }
    .tri-card {
        background-color: #ecfdf5;
        border: 1px solid #6ee7b7;
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        color: #064e3b;
    }
    .status-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .status-disponible { background: #dcfce7; color: #166534; border: 1px solid #86efac; }
    .status-discussion { background: #fef3c7; color: #92400e; border: 1px solid #fcd34d; }
    .status-accord { background: #e0e7ff; color: #3730a3; border: 1px solid #a5b4fc; }
    .chat-bubble {
        padding: 0.6rem 0.9rem;
        border-radius: 10px;
        margin-bottom: 0.5rem;
        font-size: 0.88rem;
    }
    .chat-me { background: #dbeafe; color: #1e3a8a; text-align: right; margin-left: 20%; }
    .chat-other { background: #f1f5f9; color: #1e293b; margin-right: 20%; }
    .nav-tabs {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        border-bottom: 2px solid #e2e8f0;
        margin-bottom: 1.5rem;
        padding-bottom: 0.5rem;
    }
    .nav-tab-btn {
        background: transparent;
        border: none;
        color: #64748b;
        font-weight: 600;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        cursor: pointer;
        text-decoration: none;
    }
    .nav-tab-btn.active {
        background: #1d4ed8;
        color: #ffffff;
    }
    .stat-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .stat-val { font-size: 1.7rem; font-weight: 800; color: #0f172a; }
    .stat-lbl { font-size: 0.8rem; color: #64748b; font-weight: 600; }
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

# Statuts normalisés des offres de stage
STATUTS_DEMANDE = ["Disponible", "En discussion", "Accord trouvé"]

# Noms des collections Firebase Firestore
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

# Set en mémoire pour éviter le spam d'alertes emails sur les salons déjà notifiés
NOTIFIED_MATCH_ROOMS: set[str] = set()

# ---------------------------------------------------------------------------
# 3. INITIALISATION ROBUSTE FIREBASE FIRESTORE (credentials.Certificate)
# ---------------------------------------------------------------------------
_FIRESTORE_CLIENT = None

def get_firestore_client():
    """
    Initialise l'application Firebase Admin de façon protégée (anti-réinitialisation multiple)
    en utilisant les credentials stockés dans FIREBASE_CREDENTIALS, secrets.toml ou fichier de clé.
    Retourne l'instance client Firestore ou None avec fallback transparent si non configuré.
    """
    global _FIRESTORE_CLIENT
    if _FIRESTORE_CLIENT is not None:
        return _FIRESTORE_CLIENT

    if not firebase_admin._apps:
        try:
            fb_creds_dict = None

            # 1. Variable d'environnement FIREBASE_CONFIG ou FIREBASE_CREDENTIALS
            raw_env = os.environ.get("FIREBASE_CREDENTIALS") or os.environ.get("FIREBASE_CONFIG")
            if raw_env:
                if os.path.exists(raw_env):
                    cred = credentials.Certificate(raw_env)
                    firebase_admin.initialize_app(cred)
                    _FIRESTORE_CLIENT = firestore.client()
                    return _FIRESTORE_CLIENT
                else:
                    fb_creds_dict = json.loads(raw_env)

            # 2. Fichier .streamlit/secrets.toml si présent
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

            # 3. Fichier local serviceAccountKey.json
            if fb_creds_dict is None and os.path.exists("serviceAccountKey.json"):
                cred = credentials.Certificate("serviceAccountKey.json")
                firebase_admin.initialize_app(cred)
                _FIRESTORE_CLIENT = firestore.client()
                return _FIRESTORE_CLIENT

            if fb_creds_dict:
                # Traitement sécurisé des retours à la ligne dans la clé RSA
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

# Fallback en mémoire locale pour garantir l'exécution sans plantage si Firestore n'est pas encore provisionné
_MEMOIRE_USERS = {}
_MEMOIRE_DEMANDES = {}
_MEMOIRE_MESSAGES = {}

# ---------------------------------------------------------------------------
# 4. GESTION DES DONNÉES FIRESTORE (users, demandes, messages)
# ---------------------------------------------------------------------------
def normalize_pin(val: str) -> str:
    """Nettoie et force le format à 4 chiffres d'un code PIN."""
    s = str(val or "").strip().replace(".0", "")
    return s.zfill(4) if (s.isdigit() and len(s) <= 4) else s

def load_users_data() -> pd.DataFrame:
    """Lit les profils étudiants de la collection 'users'."""
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
    """Crée un nouvel utilisateur dans la collection 'users'."""
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
    """Met à jour atomiquement le code PIN d'un étudiant et ses demandes associées."""
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
    """Supprime l'utilisateur et toutes ses demandes associées en cascade."""
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
    """Lit toutes les annonces de la collection 'demandes'."""
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
    """Publie une nouvelle offre dans la collection 'demandes'."""
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
    """Met à jour une offre existante."""
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
    """Supprime définitivement une demande de la base."""
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
    """Lit l'ensemble des messages de discussion des salons privés."""
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
    """Insère un message dans la collection 'messages'."""
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
# 5. MOTEUR DE MATCHING PUR (100% CONFORME ET INTACT)
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
    """Détecte tous les échanges bilatéraux (A <-> B) pour même période et même spécialité."""
    matches = []
    if df.empty:
        return matches
    # Exclure les offres qui ont déjà trouvé accord définitif
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
    """Détecte tous les cycles à 3 personnes (A donne à B, B donne à C, C donne à A)."""
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
    """
    RÈGLE ABSOLUE DE CONFIDENTIALITÉ :
    Ne retourne QUE les correspondances impliquant directement l'étudiant connecté.
    """
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
    """Construit la liste des alertes pour l'étudiant connecté."""
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
# 6. ENVOI DES EMAILS D'ALERTE SMTP (send_match_notification_emails, send_pin_recovery_email)
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
    """Récupère les identifiants SMTP depuis les variables d'environnement."""
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
    """
    Envoie un email individuel aux étudiants faisant partie intégrante d'un nouveau cycle.
    Anti-plantage complet (try/except) et mémorisation anti-doublon par room_id.
    """
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
    """Envoie le code PIN par email en cas d'oubli."""
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
# 7. COMPOSANTS D'INTERFACE FASTHTML (Pico.css + HTMX)
# ---------------------------------------------------------------------------
def render_header(session, active_tab="accueil"):
    """En-tête de navigation global avec statut de session et cloche de notifications."""
    user_email = session.get("email")
    user_prenom = session.get("prenom")
    user_nom = session.get("nom")
    is_admin = session.get("is_admin", False)

    # Récupération des compteurs
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

    auth_section = None
    if user_email:
        auth_section = Div(
            Span(f"👤 {user_prenom} {user_nom}", style="font-weight:600; font-size:0.85rem; margin-right:0.75rem;"),
            A(f"🔔 ({len(notifs)})", href="/notifications", role="button", cls="outline secondary", style="padding:0.35rem 0.75rem; font-size:0.8rem; margin-right:0.5rem;"),
            A("Déconnexion", href="/logout", role="button", cls="outline", style="padding:0.35rem 0.75rem; font-size:0.8rem;"),
            style="display:flex; align-items:center;"
        )
    else:
        auth_section = Div(
            A("Connexion / Inscription", href="/login-view", role="button", cls="primary", style="padding:0.4rem 0.9rem; font-size:0.85rem;"),
            style="display:flex; align-items:center;"
        )

    return Header(
        Nav(
            Ul(
                Li(
                    Strong("PermutStage", style="font-size:1.35rem; color:#1d4ed8; letter-spacing:-0.02em;"),
                    Small(" · Médecine P3-P8", style="color:#64748b; font-size:0.8rem; margin-left:0.3rem;")
                )
            ),
            Ul(Li(auth_section)),
            cls="container-fluid",
            style="border-bottom: 1px solid #e2e8f0; padding: 0.75rem 1rem; margin-bottom: 1rem; background: #ffffff;"
        ),
        Nav(
            Ul(*nav_items),
            cls="container-fluid nav-tabs"
        )
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
# 8. ROUTES DE L'APPLICATION (LES 5 VUES + AUTH + ADMIN)
# ---------------------------------------------------------------------------

# === VUE 1 : ACCUEIL & GUIDE ===
@rt("/")
def get(session):
    df_demandes = load_demandes_data()
    df_users = load_users_data()
    all_bi = compute_bilateral_matches(df_demandes)
    all_tri = compute_triangular_matches(df_demandes)

    content = Main(
        render_header(session, "accueil"),
        Div(
            Div(
                Div("✨ PROMOTION MÉDECINE 2028 · MASTER 2", cls="hero-badge"),
                H1("Trouvez votre binôme de stage idéal en quelques clics", style="font-size:2rem; font-weight:800;"),
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
                Div(Div(str(len(all_bi)), cls="stat-val"), Div("Matchs bilatéraux (2)", cls="stat-lbl"), cls="stat-card"),
                Div(Div(str(len(all_tri)), cls="stat-val"), Div("Cycles triangulaires (3)", cls="stat-lbl"), cls="stat-card"),
                style="display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:1rem; margin-bottom:2rem;"
            ),
            # Les 4 étapes
            H3("🧭 Le parcours en 4 étapes simples"),
            Div(
                Article(
                    Strong("1. Créer son profil"),
                    P("Nom, prénom, email institutionnel et code PIN à 4 chiffres. Aucun mot de passe complexe.", style="font-size:0.85rem; color:#475569;"),
                ),
                Article(
                    Strong("2. Déposer son offre"),
                    P("Indiquez votre stage actuel (période P3 à P8, spécialité, hôpital) et vos hôpitaux souhaités.", style="font-size:0.85rem; color:#475569;"),
                ),
                Article(
                    Strong("3. Calcul des correspondances"),
                    P("L'algorithme détecte en continu les cycles bilatéraux (A ↔ B) et triangulaires (A → B → C → A).", style="font-size:0.85rem; color:#475569;"),
                ),
                Article(
                    Strong("4. Salon privé & Accord"),
                    P("Discutez en direct dans votre salon privé sécurisé et confirmez votre accord de principe.", style="font-size:0.85rem; color:#475569;"),
                ),
                style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:1rem; margin-bottom:2rem;"
            ),
            # Règles & Confidentialité
            Div(
                Article(
                    H4("⚖️ Règles d'échange"),
                    Ul(
                        Li(Strong("Même période obligatoire : "), "P3 contre P3, P4 contre P4, etc."),
                        Li(Strong("Même spécialité obligatoire : "), "Pédiatrie contre Pédiatrie, Chirurgie contre Chirurgie."),
                        Li(Strong("Validation facultaire : "), "L'accord trouvé sur l'application reste un accord de principe à soumettre à la commission des stages.")
                    )
                ),
                Article(
                    H4("🔒 Confidentialité garantie"),
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
    return content

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
                    H3("🔒 Connexion requise"),
                    P("Veuillez vous connecter avec votre adresse étudiante et votre code PIN pour déposer une offre de permutation."),
                    A("Se connecter / S'inscrire", href="/login-view", role="button", cls="primary"),
                    style="text-align:center; padding:2.5rem;"
                ),
                cls="container"
            ),
            render_footer()
        )

    return Main(
        render_header(session, "deposer"),
        Div(
            H2("Déposer une nouvelle offre de permutation"),
            P("Vos coordonnées sont automatiquement verrouillées sur votre profil étudiant connecté."),
            Div(id="depot-feedback"),
            Form(
                Div(
                    Div(
                        Label("Nom complet (verrouillé)", Input(value=f"{user_prenom} {user_nom}", disabled=True)),
                        Label("Email institutionnel (verrouillé)", Input(value=user_email, disabled=True)),
                    ),
                    Div(
                        Label("Période de stage *", Select(*[Option(p, value=p) for p in PERIODES], name="periode", required=True)),
                        Label("Spécialité *", Select(*[Option(s, value=s) for s in SPECIALITES], name="specialite", required=True)),
                        Label("Hôpital actuel proposé *", Select(*[Option(f"[{HOPITAL_VERS_REGION.get(h, '')}] {h}", value=h) for h in TOUS_LES_HOPITAUX], name="hopital_actuel", required=True)),
                    ),
                    style="display:grid; grid-template-columns: 1fr 1fr; gap:1.5rem;"
                ),
                Label(
                    "Hôpitaux souhaités en échange (sélectionnez-en un ou plusieurs) *",
                    Select(
                        *[Option(f"[{HOPITAL_VERS_REGION.get(h, '')}] {h}", value=h) for h in TOUS_LES_HOPITAUX],
                        name="hopitaux_souhaites",
                        multiple=True,
                        size=8,
                        required=True
                    )
                ),
                Small("Conseil : Maintenez Ctrl (ou Cmd sur Mac) pour sélectionner plusieurs hôpitaux souhaités.", style="display:block; margin-bottom:1rem; color:#64748b;"),
                Button("Publier ma demande de permutation", type="submit", cls="primary"),
                hx_post="/nouvelle-demande",
                hx_target="#depot-feedback",
                hx_swap="innerHTML"
            ),
            cls="container"
        ),
        render_footer()
    )

@rt("/nouvelle-demande")
def post(session, periode: str, specialite: str, hopital_actuel: str, hopitaux_souhaites: list[str] = None):
    user_email = session.get("email")
    user_nom = f"{session.get('prenom', '')} {session.get('nom', '')}".strip()
    user_pin = session.get("pin", "")

    if not user_email:
        return Article(P("Session expirée. Veuillez vous reconnecter.", style="color:#b91c1c;"), cls="contrast")

    # Si un seul hôpital sélectionné, FastHTML peut le passer en str au lieu de list
    if isinstance(hopitaux_souhaites, str):
        hopitaux_souhaites = [hopitaux_souhaites]
    if not hopitaux_souhaites:
        return Article(P("Veuillez sélectionner au moins un hôpital souhaité.", style="color:#b91c1c;"), cls="contrast")

    if hopital_actuel in hopitaux_souhaites:
        return Article(P("Validation refusée : votre hôpital actuel ne peut pas figurer dans vos hôpitaux souhaités.", style="color:#b91c1c;"), cls="contrast")

    df_demandes = load_demandes_data()
    if not df_demandes.empty:
        doublon = df_demandes[
            (df_demandes["Email"].str.lower() == user_email.lower())
            & (df_demandes["Periode"] == periode)
        ]
        if not doublon.empty:
            return Article(P(f"Vous avez déjà une offre active sur la période {periode}. Modifiez-la dans 'Gérer mon offre'.", style="color:#b91c1c;"), cls="contrast")

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
        "Hopitaux_Souhaites": serialize_hospitals(hopitaux_souhaites),
        "Statut": "Disponible",
    }

    if add_demande_firestore(nouvelle_demande):
        df_maj = pd.concat([df_demandes, pd.DataFrame([nouvelle_demande])], ignore_index=True)
        # Déclenchement automatique des emails d'alerte
        nouveaux_bi = compute_bilateral_matches(df_maj)
        nouveaux_tri = compute_triangular_matches(df_maj)
        for m in nouveaux_bi:
            if m["room_id"] not in anciens_rooms:
                send_match_notification_emails(m["participants"], m["periode"], m["specialite"], m["room_id"], df_users)
        for t in nouveaux_tri:
            if t["room_id"] not in anciens_rooms:
                send_match_notification_emails(t["participants"], t["periode"], t["specialite"], t["room_id"], df_users)

        return Article(
            H4("🎉 Offre publiée avec succès !"),
            P(f"Votre demande pour le stage de {specialite} en {periode} ({hopital_actuel}) est enregistrée."),
            A("Consulter mes correspondances", href="/matchs", role="button", cls="outline"),
            style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:1.25rem;"
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
                    H3("🔒 Confidentialité absolue des correspondances"),
                    P("Seuls les étudiants connectés impliqués dans un cycle complet ont accès aux correspondances et aux coordonnées de leurs camarades."),
                    A("Se connecter", href="/login-view", role="button", cls="primary"),
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
            # Récupération des messages de ce salon
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
                        Strong(f"MATCH PRIVÉ BILATÉRAL · {m['periode']} · {m['specialite']}", style="color:#166534;"),
                        Span("Binôme direct", cls="status-badge status-disponible", style="float:right;"),
                        style="margin-bottom:0.75rem;"
                    ),
                    P(
                        Strong(a["Nom"]), f" ({a['Hopital_Actuel']})",
                        "  ⇄  ",
                        Strong(b["Nom"]), f" ({b['Hopital_Actuel']})",
                        style="font-size:1.05rem;"
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
                            Div(*chat_elements, id=f"chat-box-{room_id}", style="max-height:220px; overflow-y:auto; margin:0.75rem 0; padding:0.5rem; background:#ffffff; border-radius:8px; border:1px solid #e2e8f0;"),
                            Form(
                                Div(
                                    Input(name="texte", placeholder="Écrire un message dans ce salon privé...", required=True, style="margin-bottom:0;"),
                                    Input(type="hidden", name="room_id", value=room_id),
                                    Button("Envoyer", type="submit", cls="primary", style="margin-bottom:0; width:auto;"),
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
                        Strong(f"MATCH PRIVÉ TRIANGULAIRE · {t['periode']} · {t['specialite']}", style="color:#064e3b;"),
                        Span("Cycle à 3", cls="status-badge status-accord", style="float:right;"),
                        style="margin-bottom:0.75rem;"
                    ),
                    P(
                        Strong(a["Nom"]), f" ({a['Hopital_Actuel']}) → ",
                        Strong(b["Nom"]), f" ({b['Hopital_Actuel']}) → ",
                        Strong(c["Nom"]), f" ({c['Hopital_Actuel']}) → ",
                        Strong(a["Nom"]),
                        style="font-size:0.95rem; line-height:1.5;"
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
                            Div(*chat_elements, id=f"chat-box-{room_id}", style="max-height:220px; overflow-y:auto; margin:0.75rem 0; padding:0.5rem; background:#ffffff; border-radius:8px; border:1px solid #e2e8f0;"),
                            Form(
                                Div(
                                    Input(name="texte", placeholder="Écrire un message aux collègues du cycle...", required=True, style="margin-bottom:0;"),
                                    Input(type="hidden", name="room_id", value=room_id),
                                    Button("Envoyer", type="submit", cls="primary", style="margin-bottom:0; width:auto;"),
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
            H2("Mes correspondances privées & Salons de discussion"),
            P(f"Affichage strictement réservé à votre profil ({user_email}). Aucun camarade extérieur ne peut visualiser vos opportunités."),
            Div(
                Div(H3(f"Binômes bilatéraux ({len(my_bi)})"), *bi_sections),
                Div(H3(f"Cycles triangulaires ({len(my_tri)})"), *tri_sections),
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
                        Strong(f"{row['Periode']} · {row['Specialite']} — Région {region_act}", style="color:#1e3a8a; font-size:1.05rem;"),
                        Span(statut, cls=f"status-badge {st_class}", style="float:right;"),
                        style="margin-bottom:0.5rem;"
                    ),
                    P(
                        Strong("Hôpital proposé : "), row.get("Hopital_Actuel", ""),
                        Br(),
                        Strong("Hôpitaux souhaités : "), souhaites_str,
                        style="font-size:0.9rem; margin-bottom:0.4rem;"
                    ),
                    Small(f"Mis à jour le {row.get('Timestamp', '')} · Identité protégée par confidentialité", style="color:#94a3b8; font-size:0.75rem;"),
                    style="margin-bottom:0.75rem; background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:1rem;"
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
            H2(f"Catalogue des offres de stage disponibles ({len(df_filtre)} affichée(s))"),
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
                    H3("🔒 Connexion requise"),
                    P("Connectez-vous pour modifier vos annonces ou mettre à jour leur statut."),
                    A("Se connecter", href="/login-view", role="button", cls="primary"),
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
                H4("Vous n'avez aucune offre active pour le moment."),
                P("Déposez votre première demande de permutation pour que notre moteur détecte vos binômes."),
                A("Déposer une offre", href="/deposer", role="button", cls="primary"),
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

            edit_form = Form(
                Input(type="hidden", name="demande_id", value=d_id),
                Div(
                    Div(Label("Période", Select(*[Option(p, value=p, selected=(p==cur_periode)) for p in PERIODES], name="periode"))),
                    Div(Label("Spécialité", Select(*[Option(s, value=s, selected=(s==cur_spec)) for s in SPECIALITES], name="specialite"))),
                    Div(Label("Hôpital actuel", Select(*[Option(h, value=h, selected=(h==cur_actuel)) for h in TOUS_LES_HOPITAUX], name="hopital_actuel"))),
                    Div(Label("Statut de la demande", Select(*[Option(st, value=st, selected=(st==cur_statut)) for st in STATUTS_DEMANDE], name="statut"))),
                    style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:1rem;"
                ),
                Label(
                    "Hôpitaux souhaités",
                    Select(
                        *[Option(f"[{HOPITAL_VERS_REGION.get(h, '')}] {h}", value=h, selected=(h in cur_souhaites)) for h in TOUS_LES_HOPITAUX],
                        name="hopitaux_souhaites",
                        multiple=True,
                        size=6,
                        required=True
                    )
                ),
                Div(
                    Button("Enregistrer les modifications", type="submit", cls="primary"),
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
                Button("Supprimer définitivement l'offre", type="submit", cls="secondary outline", style="color:#b91c1c; border-color:#b91c1c;"),
                hx_post="/supprimer-demande",
                hx_target=f"#offre-container-{d_id}",
                hx_swap="outerHTML"
            )

            offres_blocks.append(
                Div(
                    Article(
                        H3(f"📌 {cur_periode} · {cur_spec} ({cur_actuel})"),
                        Div(id=f"feedback-{d_id}"),
                        H5("Modifier l'annonce"),
                        edit_form,
                        Hr(),
                        H5("Supprimer l'annonce"),
                        delete_form,
                    ),
                    id=f"offre-container-{d_id}",
                    style="margin-bottom:1.5rem;"
                )
            )

    return Main(
        render_header(session, "gerer"),
        Div(
            H2("Gérer mes annonces publiées"),
            P("Vous pouvez ajuster vos souhaits à tout moment ou modifier le statut de votre offre ('Disponible', 'En discussion', 'Accord trouvé')."),
            *offres_blocks,
            cls="container"
        ),
        render_footer()
    )

@rt("/modifier-demande")
def post(session, demande_id: str, periode: str, specialite: str, hopital_actuel: str, statut: str, hopitaux_souhaites: list[str] = None):
    user_email = session.get("email")
    if not user_email:
        return P("Session expirée.", style="color:#b91c1c;")

    if isinstance(hopitaux_souhaites, str):
        hopitaux_souhaites = [hopitaux_souhaites]
    if not hopitaux_souhaites:
        return P("Veuillez conserver au moins un hôpital souhaité.", style="color:#b91c1c;")
    if hopital_actuel in hopitaux_souhaites:
        return P("L'hôpital actuel ne peut pas figurer dans les hôpitaux souhaités.", style="color:#b91c1c;")

    update_fields = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Periode": periode,
        "Specialite": specialite,
        "Hopital_Actuel": hopital_actuel,
        "Hopitaux_Souhaites": serialize_hospitals(hopitaux_souhaites),
        "Statut": statut,
    }

    if update_demande_firestore(demande_id, update_fields):
        return Article(
            P("✅ Offre mise à jour avec succès dans Firestore !"),
            style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:0.75rem; margin-bottom:1rem;"
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
            style="background:#fef2f2; border:1px solid #fecaca; color:#991b1b; padding:1rem;"
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
                    H3("🔑 Connexion Étudiant"),
                    P("Accédez à vos correspondances privées et vos salons sécurisés."),
                    Div(id="login-feedback"),
                    Form(
                        Label("Email institutionnel", Input(name="email", type="email", placeholder="prenom.nom@student.uclouvain.be", required=True)),
                        Label("Code PIN (4 chiffres)", Input(name="pin", type="password", maxlength=4, placeholder="••••", required=True)),
                        Button("Se connecter", type="submit", cls="primary"),
                        hx_post="/login",
                        hx_target="#login-feedback",
                        hx_swap="innerHTML"
                    ),
                    A("Code PIN oublié ?", href="/forgot-pin-view", style="display:block; margin-top:0.75rem; font-size:0.85rem;"),
                ),
                Article(
                    H3("📝 Créer mon profil"),
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
                        Button("Créer mon compte étudiant", type="submit", cls="outline"),
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
        return Article(P("Email ou code PIN incorrect.", style="color:#b91c1c;"), cls="contrast")

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
            A("Accéder à mes matchs", href="/matchs", role="button", cls="primary"),
            style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:1rem;"
        )
    return Article(P("Email ou code PIN incorrect.", style="color:#b91c1c;"), cls="contrast")

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
            A("Déposer ma première offre", href="/deposer", role="button", cls="primary"),
            style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:1rem;"
        )
    return P("Erreur lors de la création du compte.", style="color:#b91c1c;")

@rt("/forgot-pin-view")
def get(session):
    return Main(
        render_header(session),
        Div(
            Article(
                H3("🔑 Récupération de code PIN"),
                P("Entrez votre adresse email étudiante pour recevoir instantanément votre code PIN par email."),
                Div(id="forgot-feedback"),
                Form(
                    Label("Email institutionnel", Input(name="email", type="email", required=True)),
                    Button("M'envoyer mon code PIN", type="submit", cls="primary"),
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
            A("Se connecter", href="/login-view", role="button", cls="outline"),
            style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:1rem;"
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
                    Strong(n["titre"], style="color:#1e3a8a; display:block; margin-bottom:0.3rem;"),
                    P(n["detail"], style="font-size:0.9rem; color:#334155; margin-bottom:0.5rem;"),
                    A("Ouvrir le salon correspondant", href="/matchs", role="button", cls="outline secondary", style="font-size:0.8rem; padding:0.3rem 0.6rem;"),
                    style="margin-bottom:0.75rem; border-left:4px solid #1d4ed8;"
                )
            )

    return Main(
        render_header(session),
        Div(
            H2("🔔 Centre de Notifications"),
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
                H3("🔒 Accès Administrateur"),
                P("Espace réservé à la coordination technique et facultaire."),
                Div(id="admin-feedback"),
                Form(
                    Label("Mot de passe secret administrateur", Input(name="password", type="password", required=True)),
                    Button("Déverrouiller l'Espace Administrateur", type="submit", cls="primary"),
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
            A("Ouvrir l'Espace Administrateur", href="/admin", role="button", cls="primary"),
            style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:1rem;"
        )
    return P("Mot de passe incorrect.", style="color:#b91c1c;")

@rt("/admin")
def get(session):
    if not session.get("is_admin", False):
        return RedirectResponse("/admin-login-view")

    df_users = load_users_data()
    df_demandes = load_demandes_data()
    df_messages = load_messages_data()
    all_bi = compute_bilateral_matches(df_demandes)
    all_tri = compute_triangular_matches(df_demandes)

    # Table des demandes avec bouton de suppression directe
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
                        Button("Supprimer", type="submit", cls="outline secondary", style="padding:0.25rem 0.5rem; font-size:0.75rem; color:#b91c1c; border-color:#b91c1c;"),
                        hx_post="/admin-delete-demande",
                        hx_target="#admin-feedback",
                        hx_swap="innerHTML"
                    )
                )
            )
        )

    # Table des utilisateurs avec suppression en cascade
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
                        Button("Supprimer", type="submit", cls="outline secondary", style="padding:0.25rem 0.5rem; font-size:0.75rem; color:#b91c1c; border-color:#b91c1c;"),
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
            H2("🛠️ Espace Administrateur (Supervision globale)"),
            Div(id="admin-feedback"),
            # Statistiques
            Div(
                Div(Div(str(len(df_users)), cls="stat-val"), Div("Comptes étudiants", cls="stat-lbl"), cls="stat-card"),
                Div(Div(str(len(df_demandes)), cls="stat-val"), Div("Offres actives", cls="stat-lbl"), cls="stat-card"),
                Div(Div(str(len(all_bi)), cls="stat-val"), Div("Matchs binômes", cls="stat-lbl"), cls="stat-card"),
                Div(Div(str(len(all_tri)), cls="stat-val"), Div("Boucles triangulaires", cls="stat-lbl"), cls="stat-card"),
                style="display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:1rem; margin-bottom:2rem;"
            ),
            # Collection demandes
            Article(
                H3(f"📋 Collection 'demandes' ({len(df_demandes)})"),
                Div(
                    A("📥 Télécharger CSV", href="/admin-export-demandes-csv", role="button", cls="outline", style="margin-bottom:1rem; padding:0.4rem 0.8rem; font-size:0.8rem;"),
                    Table(
                        Thead(Tr(Th("ID"), Th("Nom"), Th("Email"), Th("Période"), Th("Spécialité"), Th("Hôpital actuel"), Th("Statut"), Th("Action"))),
                        Tbody(*demandes_rows),
                        cls="striped"
                    ),
                    style="overflow-x:auto;"
                )
            ),
            # Collection users
            Article(
                H3(f"👥 Collection 'users' ({len(df_users)})"),
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
        return Article(P(f"Demande {demande_id} supprimée."), style="background:#fef2f2; color:#991b1b; padding:0.5rem;")
    return P("Erreur", style="color:#b91c1c;")

@rt("/admin-delete-user")
def post(session, user_id: str):
    if not session.get("is_admin", False):
        return P("Non autorisé", style="color:#b91c1c;")
    if delete_user_firestore(user_id):
        return Article(P(f"Utilisateur {user_id} et ses demandes supprimés."), style="background:#fef2f2; color:#991b1b; padding:0.5rem;")
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
# 9. DÉMARRAGE DU SERVEUR FASTHTML
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    serve()

