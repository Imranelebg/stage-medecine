"""
PermutStage — Plateforme Collaborative d'Échange de Lieux de Stage (Médecine P3 à P8)
Version FastHTML (python-fasthtml) & Google Cloud Firebase Firestore (firebase-admin).

Architecture complète dans un fichier unique main.py avec persistance Firestore garantie :
- users : documents indexés par l'email étudiant (nom, prénom, code_pin, created_at, statut)
- demandes : documents indexés par id unique (email, nom, periode, specialite, hopital_actuel, hopitaux_souhaites, statut, timestamp)
- discussions : documents indexés par id de salon (participants, type_match, dernier_message, updated_at)
- messages : documents indexés par id auto-généré (room_id, sender_email, sender_name, message, timestamp)
"""

import os
import sys
import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

import pandas as pd
from fasthtml.common import *
from starlette.responses import RedirectResponse, Response

# ---------------------------------------------------------------------------
# CONFIGURATION DU LOGGING
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [PermutStage] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("PermutStage")

# ---------------------------------------------------------------------------
# 1. INITIALISATION DE L'APPLICATION FASTHTML & FEUILLE DE STYLE
# ---------------------------------------------------------------------------
CUSTOM_STYLE = Style("""
    :root {
        --pico-font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
        --pico-primary: #1d4ed8;
        --pico-primary-background: #1d4ed8;
        --pico-primary-hover: #1e40af;
        --pico-border-radius: 0.5rem;
    }
    body {
        background-color: #f8fafc;
        color: #0f172a;
    }
    .app-header {
        background: #ffffff;
        border-bottom: 1px solid #e2e8f0;
        padding: 0.75rem 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
    }
    .brand-title {
        font-weight: 800;
        font-size: 1.35rem;
        color: #1d4ed8;
        letter-spacing: -0.025em;
        margin: 0;
    }
    .brand-subtitle {
        font-size: 0.8rem;
        color: #64748b;
        font-weight: 600;
        margin-left: 0.5rem;
    }
    .nav-tabs {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-top: 0.75rem;
        border-top: 1px solid #f1f5f9;
        padding-top: 0.75rem;
    }
    .nav-tab-btn {
        padding: 0.45rem 0.9rem;
        font-size: 0.88rem;
        font-weight: 600;
        border-radius: 0.375rem;
        text-decoration: none;
        color: #475569;
        transition: all 0.15s ease-in-out;
        background: transparent;
        border: 1px solid transparent;
    }
    .nav-tab-btn:hover {
        background: #f1f5f9;
        color: #0f172a;
    }
    .nav-tab-btn.active {
        background: #eff6ff;
        color: #1d4ed8;
        border-color: #bfdbfe;
        font-weight: 700;
    }
    .hero-banner {
        background: linear-gradient(135deg, #1e3a8a 0%, #1d4ed8 50%, #3b82f6 100%);
        color: #ffffff;
        padding: 2.25rem 2rem;
        border-radius: 1rem;
        margin-bottom: 2rem;
        box-shadow: 0 10px 15px -3px rgba(29, 78, 216, 0.2);
    }
    .hero-banner h1 {
        color: #ffffff;
        font-weight: 800;
        font-size: 1.95rem;
        margin-bottom: 0.5rem;
    }
    .hero-banner p {
        color: #bfdbfe;
        font-size: 1.05rem;
        margin-bottom: 0;
    }
    .stat-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 0.75rem;
        padding: 1.25rem;
        text-align: center;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    }
    .stat-number {
        font-size: 2rem;
        font-weight: 800;
        color: #1d4ed8;
        line-height: 1;
        margin-bottom: 0.25rem;
    }
    .stat-label {
        font-size: 0.85rem;
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .match-card-bilateral {
        background: #ffffff;
        border: 2px solid #3b82f6;
        border-radius: 1rem;
        padding: 1.5rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.1);
    }
    .match-card-triangular {
        background: #ffffff;
        border: 2px solid #8b5cf6;
        border-radius: 1rem;
        padding: 1.5rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 4px 6px -1px rgba(139, 92, 246, 0.1);
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.025em;
    }
    .status-disponible { background: #dcfce7; color: #15803d; }
    .status-discussion { background: #fef3c7; color: #b45309; }
    .status-accord { background: #e0e7ff; color: #4338ca; }
    
    .chat-bubble {
        padding: 0.75rem 1rem;
        border-radius: 1rem;
        margin-bottom: 0.65rem;
        max-width: 80%;
        line-height: 1.4;
    }
    .chat-bubble-mine {
        background: #1d4ed8;
        color: #ffffff;
        margin-left: auto;
        border-bottom-right-radius: 0.2rem;
    }
    .chat-bubble-other {
        background: #f1f5f9;
        color: #0f172a;
        margin-right: auto;
        border-bottom-left-radius: 0.2rem;
    }

    /* Sélecteur moderne d'hôpitaux souhaités */
    .quick-region-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background: #ffffff;
        color: #1d4ed8;
        border: 1px solid #bfdbfe;
        border-radius: 9999px;
        padding: 0.3rem 0.75rem;
        font-size: 0.8rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.15s ease;
        user-select: none;
        line-height: 1.2;
    }
    .quick-region-badge:hover {
        background: #eff6ff;
        border-color: #3b82f6;
    }
    .quick-badge-reset {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background: #ffffff;
        color: #dc2626;
        border: 1px solid #fecaca;
        border-radius: 9999px;
        padding: 0.3rem 0.75rem;
        font-size: 0.8rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.15s ease;
        user-select: none;
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
        "CNP Saint Martin - Dave",
    ],
    "Hainaut": [
        "Centre Hospitalier de Jolimont (La Louvière)",
        "Centre Hospitalier de Lobbes",
        "Centre Hospitalier de Mouscron",
        "Centre Hospitalier de Wallonie Picarde (CHwapi - Tournai)",
        "Centre Hospitalier Universitaire de Charleroi (CHU Charleroi)",
        "Centre Hospitalier Universitaire Ambroise Paré (Mons)",
        "CHIREC - Hôpital de Chimay",
        "Clinique Notre Dame de Grâce (Gosselies)",
        "Groupe Hospitalier de Nivelles-Tubize - Tubize",
        "Grand Hôpital de Charleroi (GHdC)",
        "Hôpital de Warquignies (Boussu)",
        "Hôpital Psychiatrique Saint Jean de Dieu (Leuze-en-Hainaut)",
        "Hôpital de Braine-le-Comte",
    ],
    "Liège": [
        "Centre Hospitalier Régional de la Citadelle (CHR Liège)",
        "Centre Hospitalier Régional Huy (CHR Huy)",
        "Centre Hospitalier Régional Verviers (CHR Verviers)",
        "Centre Hospitalier Spécialisé l'Échappée (Liège)",
        "Centre Hospitalier Universitaire de Liège (CHU Liège)",
        "Clinique CHC Hermalle",
        "Clinique CHC Heusy",
        "Clinique CHC MontLégia (Liège)",
        "Clinique CHC Waremme",
    ],
    "Luxembourg": [
        "Hôpital d'Arlon (Vivalia)",
        "Hôpital de Bastogne (Vivalia)",
        "Hôpital de Libramont (Vivalia)",
        "Hôpital de Marche-en-Famenne (Vivalia)",
    ],
    "Grand-Duché de Luxembourg": [
        "Centre Hospitalier de Luxembourg (CHL)",
        "Hôpitaux Robert Schuman (HRS - Luxembourg)",
    ],
}

ALL_HOSPITALS = sorted(
    list({h for sublist in HOPITAUX_PAR_REGION.values() for h in sublist})
)

# ---------------------------------------------------------------------------
# 3. INITIALISATION GOOGLE CLOUD FIREBASE FIRESTORE
# ---------------------------------------------------------------------------
db = None
_local_db_path = os.path.join(os.path.dirname(__file__), ".permutstage_local_db.json")

def _init_local_db():
    if not os.path.exists(_local_db_path):
        initial = {
            "users": {},
            "demandes": {},
            "discussions": {},
            "messages": []
        }
        with open(_local_db_path, "w", encoding="utf-8") as f:
            json.dump(initial, f, indent=2, ensure_ascii=False)

def _read_local_db() -> Dict[str, Any]:
    _init_local_db()
    try:
        with open(_local_db_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erreur lecture DB locale: {e}")
        return {"users": {}, "demandes": {}, "discussions": {}, "messages": []}

def _write_local_db(data: Dict[str, Any]):
    try:
        with open(_local_db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Erreur écriture DB locale: {e}")

try:
    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        fb_creds_dict = None
        # 1. Variable d'environnement FIREBASE_CREDENTIALS
        if "FIREBASE_CREDENTIALS" in os.environ:
            try:
                fb_creds_dict = json.loads(os.environ["FIREBASE_CREDENTIALS"])
            except Exception as e:
                logger.warning(f"Erreur décodage JSON FIREBASE_CREDENTIALS: {e}")

        # 2. Variable GOOGLE_APPLICATION_CREDENTIALS (chemin de fichier)
        if not fb_creds_dict and "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
            cred_file = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
            if os.path.exists(cred_file):
                try:
                    with open(cred_file, "r", encoding="utf-8") as f:
                        fb_creds_dict = json.load(f)
                except Exception as e:
                    logger.warning(f"Erreur lecture cred_file: {e}")

        # 3. Fichier secrets.toml (Streamlit local ou Render)
        if not fb_creds_dict:
            try:
                import tomllib
            except ImportError:
                try:
                    import toml as tomllib
                except ImportError:
                    tomllib = None

            search_paths = [
                os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml"),
                os.path.join(os.path.dirname(__file__), "secrets.toml"),
            ]
            for p in search_paths:
                if os.path.exists(p) and tomllib:
                    try:
                        with open(p, "rb") as f:
                            sec = tomllib.load(f)
                            if "firebase" in sec:
                                fb_creds_dict = dict(sec["firebase"])
                                break
                    except Exception as e:
                        logger.warning(f"Erreur lecture {p}: {e}")

        if fb_creds_dict:
            cred = credentials.Certificate(fb_creds_dict)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            logger.info("Connexion à Google Cloud Firebase Firestore réussie.")
        else:
            try:
                firebase_admin.initialize_app()
                db = firestore.client()
                logger.info("Connexion Firebase par défaut (Default Credentials) réussie.")
            except Exception as e:
                logger.warning(f"Fallback DB locale active (Firebase non configuré: {e})")
                db = None
    else:
        db = firestore.client()
except Exception as exc:
    logger.warning(f"Bibliothèque firebase-admin non initialisée ({exc}). Mode repli local actif.")
    db = None

# ---------------------------------------------------------------------------
# 4. GESTION PERSISTANTE DE LA BASE DE DONNÉES (FIRESTORE AVEC REPLI LOCAL)
# ---------------------------------------------------------------------------

def save_user(email: str, nom: str, prenom: str, code_pin: str) -> bool:
    """Enregistre ou met à jour un utilisateur dans la collection Firestore 'users'."""
    clean_email = email.lower().strip()
    data = {
        "email": clean_email,
        "nom": nom.strip(),
        "prenom": prenom.strip(),
        "code_pin": str(code_pin).strip(),
        "created_at": datetime.now().isoformat(),
        "statut": "actif",
        "updated_at": datetime.now().isoformat()
    }
    if db is not None:
        try:
            db.collection("users").document(clean_email).set(data, merge=True)
            logger.info(f"Utilisateur {clean_email} persisté dans Firestore.")
            return True
        except Exception as e:
            logger.error(f"Erreur Firestore save_user: {e}")
    # Repli persistant local
    ldb = _read_local_db()
    ldb["users"][clean_email] = data
    _write_local_db(ldb)
    return True

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Récupère le profil complet d'un étudiant depuis Firestore."""
    clean_email = email.lower().strip()
    if db is not None:
        try:
            doc = db.collection("users").document(clean_email).get()
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            logger.error(f"Erreur Firestore get_user: {e}")
    ldb = _read_local_db()
    return ldb["users"].get(clean_email)

def verify_user_login(email: str, code_pin: str) -> Optional[Dict[str, Any]]:
    """Vérifie l'adresse email et le code PIN de l'étudiant."""
    user = get_user_by_email(email)
    if user:
        stored_pin = str(user.get("code_pin", user.get("PIN", ""))).strip()
        if stored_pin == str(code_pin).strip():
            return user
    return None

def update_user_pin(email: str, new_pin: str) -> bool:
    """Met à jour le code PIN d'un étudiant."""
    clean_email = email.lower().strip()
    if db is not None:
        try:
            db.collection("users").document(clean_email).update({
                "code_pin": str(new_pin).strip(),
                "updated_at": datetime.now().isoformat()
            })
            return True
        except Exception as e:
            logger.error(f"Erreur Firestore update_pin: {e}")
    ldb = _read_local_db()
    if clean_email in ldb["users"]:
        ldb["users"][clean_email]["code_pin"] = str(new_pin).strip()
        _write_local_db(ldb)
        return True
    return False

def delete_user_and_offers(email: str) -> bool:
    """Supprime un compte étudiant et toutes ses demandes associées."""
    clean_email = email.lower().strip()
    if db is not None:
        try:
            db.collection("users").document(clean_email).delete()
            # Supprimer ses demandes
            docs = db.collection("demandes").where("user_email", "==", clean_email).stream()
            for d in docs:
                db.collection("demandes").document(d.id).delete()
        except Exception as e:
            logger.error(f"Erreur Firestore delete_user_and_offers: {e}")
    ldb = _read_local_db()
    ldb["users"].pop(clean_email, None)
    demandes_to_delete = [
        k for k, v in ldb["demandes"].items()
        if str(v.get("user_email", v.get("Email", ""))).lower().strip() == clean_email
    ]
    for k in demandes_to_delete:
        ldb["demandes"].pop(k, None)
    _write_local_db(ldb)
    return True

def serialize_hospitals(hospitals: List[str]) -> str:
    """Sérialise la liste d'hôpitaux sous format canonique avec délimiteur |."""
    if not hospitals:
        return ""
    return " | ".join(sorted(list(set(hospitals))))

def parse_hospitals(serialized: Any) -> List[str]:
    """Désérialise la chaîne d'hôpitaux souhaités."""
    if isinstance(serialized, list):
        return [str(h).strip() for h in serialized if str(h).strip()]
    if not serialized or pd.isna(serialized):
        return []
    return [h.strip() for h in str(serialized).split("|") if h.strip()]

def load_demandes_data() -> pd.DataFrame:
    """Charge toutes les propositions de stage depuis Firestore."""
    rows = []
    if db is not None:
        try:
            docs = db.collection("demandes").stream()
            for doc in docs:
                d = doc.to_dict()
                d["id"] = doc.id
                rows.append(d)
        except Exception as e:
            logger.error(f"Erreur Firestore load_demandes: {e}")

    if not rows:
        ldb = _read_local_db()
        for k, v in ldb["demandes"].items():
            item = dict(v)
            item["id"] = k
            rows.append(item)

    if not rows:
        return pd.DataFrame(columns=[
            "id", "user_email", "Email", "nom_etudiant", "Nom", "prenom_etudiant", "Prenom",
            "periode", "Periode", "specialite", "Specialite", "hopital_actuel", "Hopital_Actuel",
            "hopitaux_souhaites", "Hopitaux_Souhaites", "statut", "Statut", "timestamp", "Timestamp"
        ])

    df = pd.DataFrame(rows)
    # Normalisation bilingue des colonnes
    if "user_email" not in df.columns and "Email" in df.columns:
        df["user_email"] = df["Email"]
    if "nom_etudiant" not in df.columns and "Nom" in df.columns:
        df["nom_etudiant"] = df["Nom"]
    if "prenom_etudiant" not in df.columns and "Prenom" in df.columns:
        df["prenom_etudiant"] = df["Prenom"]
    if "periode" not in df.columns and "Periode" in df.columns:
        df["periode"] = df["Periode"]
    if "specialite" not in df.columns and "Specialite" in df.columns:
        df["specialite"] = df["Specialite"]
    if "hopital_actuel" not in df.columns and "Hopital_Actuel" in df.columns:
        df["hopital_actuel"] = df["Hopital_Actuel"]
    if "hopitaux_souhaites" not in df.columns and "Hopitaux_Souhaites" in df.columns:
        df["hopitaux_souhaites"] = df["Hopitaux_Souhaites"]
    if "statut" not in df.columns and "Statut" in df.columns:
        df["statut"] = df["Statut"]
    if "timestamp" not in df.columns and "Timestamp" in df.columns:
        df["timestamp"] = df["Timestamp"]

    return df

def save_demande(
    user_email: str,
    nom: str,
    prenom: str,
    periode: str,
    specialite: str,
    hopital_actuel: str,
    hopitaux_souhaites: List[str],
    statut: str = "Disponible",
    demande_id: Optional[str] = None
) -> str:
    """Enregistre ou met à jour une offre de stage dans Firestore."""
    clean_email = user_email.lower().strip()
    serialized = serialize_hospitals(hopitaux_souhaites)
    now_str = datetime.now().isoformat()
    doc_id = demande_id or f"{clean_email}_{periode.lower()}"

    data = {
        "id": doc_id,
        "user_email": clean_email,
        "Email": clean_email,
        "nom_etudiant": nom.strip(),
        "Nom": nom.strip(),
        "prenom_etudiant": prenom.strip(),
        "Prenom": prenom.strip(),
        "periode": periode,
        "Periode": periode,
        "specialite": specialite,
        "Specialite": specialite,
        "hopital_actuel": hopital_actuel,
        "Hopital_Actuel": hopital_actuel,
        "hopitaux_souhaites": serialized,
        "Hopitaux_Souhaites": serialized,
        "statut": statut,
        "Statut": statut,
        "timestamp": now_str,
        "Timestamp": now_str,
    }

    if db is not None:
        try:
            db.collection("demandes").document(doc_id).set(data, merge=True)
            logger.info(f"Demande {doc_id} persistée dans Firestore.")
            return doc_id
        except Exception as e:
            logger.error(f"Erreur Firestore save_demande: {e}")

    ldb = _read_local_db()
    ldb["demandes"][doc_id] = data
    _write_local_db(ldb)
    return doc_id

def delete_demande(demande_id: str) -> bool:
    """Supprime une proposition de stage."""
    if db is not None:
        try:
            db.collection("demandes").document(demande_id).delete()
            return True
        except Exception as e:
            logger.error(f"Erreur Firestore delete_demande: {e}")
    ldb = _read_local_db()
    if demande_id in ldb["demandes"]:
        ldb["demandes"].pop(demande_id, None)
        _write_local_db(ldb)
        return True
    return False

def update_demande_statut(demande_id: str, nouveau_statut: str) -> bool:
    """Modifie le statut d'une proposition ("Disponible", "En discussion", "Accord trouvé")."""
    if db is not None:
        try:
            db.collection("demandes").document(demande_id).update({
                "statut": nouveau_statut,
                "Statut": nouveau_statut,
                "updated_at": datetime.now().isoformat()
            })
            return True
        except Exception as e:
            logger.error(f"Erreur Firestore update_statut: {e}")
    ldb = _read_local_db()
    if demande_id in ldb["demandes"]:
        ldb["demandes"][demande_id]["statut"] = nouveau_statut
        ldb["demandes"][demande_id]["Statut"] = nouveau_statut
        _write_local_db(ldb)
        return True
    return False

# ---------------------------------------------------------------------------
# 5. PERSISTANCE DES SALONS PRIVÉS ET MESSAGES DE DISCUSSION
# ---------------------------------------------------------------------------

def build_room_id(emails: List[str], periode: str) -> str:
    """Génère un identifiant déterministe et unique pour le salon privé."""
    cleaned = sorted([e.lower().strip() for e in emails])
    return f"{periode.lower()}_" + "_".join([e.replace("@", "_at_").replace(".", "_") for e in cleaned])

def load_messages_for_room(room_id: str) -> List[Dict[str, Any]]:
    """Récupère les messages d'un salon de discussion triés chronologiquement."""
    messages = []
    if db is not None:
        try:
            docs = (
                db.collection("messages")
                .where("room_id", "==", room_id)
                .order_by("timestamp")
                .stream()
            )
            for d in docs:
                item = d.to_dict()
                item["id"] = d.id
                messages.append(item)
            return messages
        except Exception as e:
            logger.warning(f"Erreur Firestore load_messages_for_room ({e}), tentative sans tri...")
            try:
                docs = db.collection("messages").where("room_id", "==", room_id).stream()
                for d in docs:
                    item = d.to_dict()
                    item["id"] = d.id
                    messages.append(item)
                messages.sort(key=lambda x: x.get("timestamp", ""))
                return messages
            except Exception as e2:
                logger.error(f"Erreur Firestore messages fallback: {e2}")

    ldb = _read_local_db()
    for m in ldb.get("messages", []):
        if m.get("room_id") == room_id:
            messages.append(m)
    messages.sort(key=lambda x: x.get("timestamp", ""))
    return messages

def save_chat_message(room_id: str, sender_email: str, sender_name: str, message: str) -> bool:
    """Enregistre un nouveau message de chat dans Firestore."""
    clean_email = sender_email.lower().strip()
    msg_data = {
        "room_id": room_id,
        "sender_email": clean_email,
        "sender_name": sender_name.strip(),
        "message": message.strip(),
        "timestamp": datetime.now().isoformat(),
        "is_read": False
    }
    if db is not None:
        try:
            db.collection("messages").add(msg_data)
            # Met à jour la collection discussions pour aperçu
            db.collection("discussions").document(room_id).set({
                "room_id": room_id,
                "dernier_message": message.strip(),
                "dernier_emetteur": sender_name.strip(),
                "updated_at": msg_data["timestamp"]
            }, merge=True)
            return True
        except Exception as e:
            logger.error(f"Erreur Firestore save_chat_message: {e}")

    ldb = _read_local_db()
    ldb.setdefault("messages", []).append(msg_data)
    _write_local_db(ldb)
    return True

# ---------------------------------------------------------------------------
# 6. MOTEUR DE MATCHING : CORRESPONDANCES BILATÉRALES ET TRIANGULAIRES
# ---------------------------------------------------------------------------

def compute_bilateral_matches(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Détecte toutes les correspondances parfaites à 2 étudiants (A <-> B)."""
    matches = []
    if df.empty or len(df) < 2:
        return matches

    # Ne considérer que les offres actives
    valid = df[df["statut"].isin(["Disponible", "En discussion"])].copy()
    grouped = valid.groupby(["periode", "specialite"])

    for (periode, spec), group in grouped:
        records = group.to_dict("records")
        n = len(records)
        for i in range(n):
            for j in range(i + 1, n):
                a = records[i]
                b = records[j]

                # Même personne ne peut permuter avec elle-même
                if a["user_email"].lower().strip() == b["user_email"].lower().strip():
                    continue

                a_wants = parse_hospitals(a["hopitaux_souhaites"])
                b_wants = parse_hospitals(b["hopitaux_souhaites"])

                # Condition bilatérale : A veut l'hôpital de B ET B veut l'hôpital de A
                if (b["hopital_actuel"] in a_wants) and (a["hopital_actuel"] in b_wants):
                    room_id = build_room_id([a["user_email"], b["user_email"]], periode)
                    matches.append({
                        "type": "bilateral",
                        "periode": periode,
                        "specialite": spec,
                        "room_id": room_id,
                        "etudiant_1": {
                            "email": a["user_email"],
                            "nom": a["nom_etudiant"],
                            "prenom": a.get("prenom_etudiant", ""),
                            "hopital_actuel": a["hopital_actuel"],
                            "statut": a["statut"],
                            "id": a["id"]
                        },
                        "etudiant_2": {
                            "email": b["user_email"],
                            "nom": b["nom_etudiant"],
                            "prenom": b.get("prenom_etudiant", ""),
                            "hopital_actuel": b["hopital_actuel"],
                            "statut": b["statut"],
                            "id": b["id"]
                        }
                    })
    return matches

def compute_triangular_matches(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Détecte les correspondances cycliques à 3 étudiants (A -> B -> C -> A)."""
    matches = []
    if df.empty or len(df) < 3:
        return matches

    valid = df[df["statut"].isin(["Disponible", "En discussion"])].copy()
    grouped = valid.groupby(["periode", "specialite"])

    for (periode, spec), group in grouped:
        records = group.to_dict("records")
        n = len(records)
        for i in range(n):
            for j in range(n):
                if i == j: continue
                for k in range(n):
                    if k == i or k == j: continue
                    a, b, c = records[i], records[j], records[k]

                    # 3 emails distincts
                    emails = {a["user_email"].lower().strip(), b["user_email"].lower().strip(), c["user_email"].lower().strip()}
                    if len(emails) < 3:
                        continue

                    a_wants = parse_hospitals(a["hopitaux_souhaites"])
                    b_wants = parse_hospitals(b["hopitaux_souhaites"])
                    c_wants = parse_hospitals(c["hopitaux_souhaites"])

                    # Cycle : A reçoit de B, B reçoit de C, C reçoit de A
                    if (b["hopital_actuel"] in a_wants) and (c["hopital_actuel"] in b_wants) and (a["hopital_actuel"] in c_wants):
                        room_id = build_room_id([a["user_email"], b["user_email"], c["user_email"]], periode)
                        # Pour éviter les doublons cycliques dans la liste, on vérifie si la pièce existe déjà
                        if not any(m["room_id"] == room_id for m in matches):
                            matches.append({
                                "type": "triangular",
                                "periode": periode,
                                "specialite": spec,
                                "room_id": room_id,
                                "cycle": [
                                    {
                                        "donneur": a["nom_etudiant"],
                                        "receveur": c["nom_etudiant"],
                                        "hopital": a["hopital_actuel"],
                                        "email": a["user_email"]
                                    },
                                    {
                                        "donneur": b["nom_etudiant"],
                                        "receveur": a["nom_etudiant"],
                                        "hopital": b["hopital_actuel"],
                                        "email": b["user_email"]
                                    },
                                    {
                                        "donneur": c["nom_etudiant"],
                                        "receveur": b["nom_etudiant"],
                                        "hopital": c["hopital_actuel"],
                                        "email": c["user_email"]
                                    },
                                ],
                                "participants": [
                                    {"email": a["user_email"], "nom": a["nom_etudiant"], "actuel": a["hopital_actuel"]},
                                    {"email": b["user_email"], "nom": b["nom_etudiant"], "actuel": b["hopital_actuel"]},
                                    {"email": c["user_email"], "nom": c["nom_etudiant"], "actuel": c["hopital_actuel"]},
                                ]
                            })
    return matches

# ---------------------------------------------------------------------------
# 7. NOTIFICATIONS SMTP & ALERTES DE CORRESPONDANCE
# ---------------------------------------------------------------------------

def send_smtp_email(to_email: str, subject: str, html_body: str) -> bool:
    """Envoi sécurisé d'emails via le serveur SMTP configuré."""
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_password = os.environ.get("SMTP_PASSWORD", "")

    if not smtp_user or not smtp_password:
        logger.warning(f"SMTP non configuré. Simulation d'envoi à {to_email}: {subject}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"PermutStage <{smtp_user}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to_email, msg.as_string())
        logger.info(f"Email envoyé avec succès à {to_email}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi SMTP à {to_email}: {e}")
        return False

def notify_match_participants(match: Dict[str, Any]):
    """Envoie une notification par email aux participants d'un nouveau match."""
    periode = match["periode"]
    spec = match["specialite"]
    if match["type"] == "bilateral":
        u1 = match["etudiant_1"]
        u2 = match["etudiant_2"]
        subj = f"🎉 PermutStage : Correspondance trouvée en {spec} ({periode}) !"
        body_1 = f"""
        <h3>Bonne nouvelle {u1['nom']} !</h3>
        <p>Une correspondance parfaite a été détectée avec <strong>{u2['nom']}</strong> pour la période <strong>{periode}</strong> en <strong>{spec}</strong>.</p>
        <p>Vous êtes actuellement à <strong>{u1['hopital_actuel']}</strong> et souhaitez aller à <strong>{u2['hopital_actuel']}</strong>.</p>
        <p>Connectez-vous sur PermutStage pour entrer dans le salon privé et échanger avec votre binôme.</p>
        """
        body_2 = f"""
        <h3>Bonne nouvelle {u2['nom']} !</h3>
        <p>Une correspondance parfaite a été détectée avec <strong>{u1['nom']}</strong> pour la période <strong>{periode}</strong> en <strong>{spec}</strong>.</p>
        <p>Vous êtes actuellement à <strong>{u2['hopital_actuel']}</strong> et souhaitez aller à <strong>{u1['hopital_actuel']}</strong>.</p>
        <p>Connectez-vous sur PermutStage pour entrer dans le salon privé et échanger avec votre binôme.</p>
        """
        send_smtp_email(u1["email"], subj, body_1)
        send_smtp_email(u2["email"], subj, body_2)

# ---------------------------------------------------------------------------
# 8. SÉLECTEUR MODERNE D'HÔPITAUX SOUHAITÉS (COMPOSANT FASTHTML)
# ---------------------------------------------------------------------------

def render_hospital_selector(current_selected: List[str] = None, current_offered: str = ""):
    """Génère le sélecteur moderne d'hôpitaux avec cases à cocher et sélection rapide par région."""
    selected_set = set(current_selected or [])
    count = len(selected_set)
    count_label = f"({count} sélectionné{'s' if count > 1 else ''})"

    # Badges de sélection rapide par région
    region_badges = []
    for reg, hospitals in HOPITAUX_PAR_REGION.items():
        escaped_list = json.dumps(hospitals)
        badge = Button(
            f"📍 {reg} ({len(hospitals)})",
            type="button",
            cls="quick-region-badge",
            onclick=f"toggleRegionHospitals({escaped_list}, true)",
            title=f"Sélectionner tous les hôpitaux de {reg}"
        )
        region_badges.append(badge)

    reset_btn = Button(
        "✕ Tout désélectionner",
        type="button",
        cls="quick-badge-reset",
        onclick="clearAllHospitals()",
        title="Désélectionner tous les hôpitaux"
    )

    # Liste des lignes d'hôpitaux
    hospital_rows = []
    for reg, hospitals in HOPITAUX_PAR_REGION.items():
        for h in hospitals:
            is_checked = h in selected_set
            is_current = (h == current_offered)
            row_id = f"chk_{abs(hash(h))}"

            checkbox = Input(
                type="checkbox",
                name="hopitaux_souhaites",
                value=h,
                id=row_id,
                checked=is_checked,
                disabled=is_current,
                cls="hospital-checkbox-custom",
                onchange="updateSelectedCounter()"
            )

            current_tag = Span(" [Votre lieu actuel]", cls="hospital-current-badge") if is_current else ""

            label_content = Label(
                Div(
                    Div(h, cls="hospital-name-text"),
                    Div(f"Région : {reg}", cls="hospital-reg-tag"),
                    current_tag,
                ),
                _for=row_id,
                style="margin:0; cursor:pointer; flex:1;"
            )

            row = Div(
                label_content,
                checkbox,
                cls=f"hospital-row-item {'is-current-hospital' if is_current else ''}",
            )
            hospital_rows.append(row)

    script_js = Script("""
        function updateSelectedCounter() {
            var checkboxes = document.querySelectorAll('input[name="hopitaux_souhaites"]:checked');
            var counterSpan = document.getElementById('selected-count-badge');
            if (counterSpan) {
                var c = checkboxes.length;
                counterSpan.textContent = '(' + c + ' sélectionné' + (c > 1 ? 's' : '') + ')';
            }
        }
        function toggleRegionHospitals(hospitalsList, select) {
            hospitalsList.forEach(function(h) {
                var inputs = document.querySelectorAll('input[name="hopitaux_souhaites"]');
                inputs.forEach(function(inp) {
                    if (inp.value === h && !inp.disabled) {
                        inp.checked = select;
                    }
                });
            });
            updateSelectedCounter();
        }
        function clearAllHospitals() {
            var inputs = document.querySelectorAll('input[name="hopitaux_souhaites"]');
            inputs.forEach(function(inp) {
                if (!inp.disabled) {
                    inp.checked = false;
                }
            });
            updateSelectedCounter();
        }
    """)

    return Div(
        Div(
            Label(
                Strong("Hôpitaux souhaités pour permutation *"),
                Span(f" {count_label}", id="selected-count-badge", style="color:#1d4ed8; font-weight:700; font-size:0.9rem;"),
                style="display:flex; align-items:center; margin-bottom:0.4rem;"
            ),
            Small("Cochez au moins un lieu de stage où vous accepteriez de permuter.", style="color:#64748b; margin-bottom:0.75rem; display:block;"),
        ),
        Div(
            Span("⚡ Sélection rapide par région :", style="font-weight:700; font-size:0.82rem; color:#1e3a8a; margin-right:0.5rem;"),
            *region_badges,
            reset_btn,
            style="display:flex; flex-wrap:wrap; gap:0.4rem; background:#eff6ff; border:1px solid #dbeafe; padding:0.75rem; border-radius:10px; margin-bottom:0.75rem; align-items:center;"
        ),
        Div(
            *hospital_rows,
            cls="hospital-scroll-container"
        ),
        script_js,
        style="margin-bottom:1.5rem;"
    )

# ---------------------------------------------------------------------------
# 9. COMPOSANTS DE MISE EN PAGE & NAVIGATION
# ---------------------------------------------------------------------------

def get_session_user(session, req: Request = None) -> Optional[Dict[str, Any]]:
    """Récupère l'utilisateur connecté via la session serveur."""
    user_email = session.get("user_email") or session.get("user_id") or session.get("email")

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
        "created_at": datetime.now().isoformat(),
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
    if is_admin:
        tabs.append(("admin", "🛠️ Administration", "/admin"))

    nav_items = [
        Li(A(label, href=url, cls=f"nav-tab-btn {'active' if key == active_tab else ''}"))
        for key, label, url in tabs
    ]

    if user_email:
        display_name = f"{user_prenom} {user_nom}".strip() or user_email
        auth_section = Div(
            Span(
                f"👤 {display_name}",
                cls="auth-connected-indicator",
                style="font-weight:700; font-size:0.85rem; color:#1e293b; background:#f1f5f9; padding:0.35rem 0.75rem; border-radius:9999px; margin-right:0.6rem; border:1px solid #e2e8f0;"
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
            Nav(
                Ul(*nav_items, style="margin:0; padding:0; list-style:none; display:flex; flex-wrap:wrap;"),
                cls="nav-tabs"
            ),
            cls="container-fluid"
        ),
        cls="app-header"
    )

def render_footer():
    """Pied de page institutionnel."""
    return Footer(
        Div(
            P(
                "PermutStage — Plateforme Indépendante d'Échange de Stages Hospitaliers • Master 2 Médecine",
                style="margin-bottom:0.25rem; font-weight:600; font-size:0.85rem; color:#475569;"
            ),
            Small(
                "Algorithmes de matching bilatéral et triangulaire certifiés conformes. Sauvegarde cloud Firestore.",
                style="color:#94a3b8; font-size:0.75rem;"
            ),
            style="text-align:center; padding:1.5rem 0; border-top:1px solid #e2e8f0; margin-top:3rem;"
        ),
        cls="container"
    )

# ---------------------------------------------------------------------------
# 10. ROUTES FASTHTML : PAGES PRINCIPALES ET PROCESSUS MÉTIER
# ---------------------------------------------------------------------------

# === VUE 1 : ACCUEIL & GUIDE D'UTILISATION ===
@rt("/")
def get(session, req: Request = None):
    df_demandes = load_demandes_data()
    total_demandes = len(df_demandes)
    total_disponibles = len(df_demandes[df_demandes["statut"] == "Disponible"]) if not df_demandes.empty else 0
    total_accords = len(df_demandes[df_demandes["statut"] == "Accord trouvé"]) if not df_demandes.empty else 0

    return Main(
        render_header(session, "accueil", req),
        Div(
            Div(
                H1("Échangez votre lieu de stage en toute sérénité"),
                P("Plateforme sécurisée pour étudiants en médecine de P3 à P8. Trouvez une permutation directe ou un échange triangulaire en quelques clics."),
                cls="hero-banner"
            ),
            # Grille de statistiques clés
            Div(
                Div(Div(str(total_demandes), cls="stat-number"), Div("Demandes déposées", cls="stat-label"), cls="stat-card"),
                Div(Div(str(total_disponibles), cls="stat-number"), Div("Places disponibles", cls="stat-label"), cls="stat-card"),
                Div(Div(str(total_accords), cls="stat-number"), Div("Accords trouvés", cls="stat-label"), cls="stat-card"),
                Div(Div("100%", cls="stat-number"), Div("Confidentiel & Gratuit", cls="stat-label"), cls="stat-card"),
                style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:1rem; margin-bottom:2rem;"
            ),
            # Guide pas-à-pas
            Article(
                H3("Comment fonctionne PermutStage ?", style="font-weight:800; color:#1e293b; margin-bottom:1.25rem;"),
                Div(
                    Div(
                        Strong("1. Déposez votre demande"),
                        P("Indiquez votre période (P3 à P8), votre spécialité, votre hôpital actuel et cochez un ou plusieurs hôpitaux souhaités.", style="font-size:0.9rem; color:#475569;"),
                        style="background:#f8fafc; border:1px solid #e2e8f0; padding:1rem; border-radius:8px;"
                    ),
                    Div(
                        Strong("2. L'algorithme calcule vos matchs"),
                        P("Dès qu'une opportunité bilatérale (A ⇄ B) ou triangulaire (A → B → C → A) apparaît, vous êtes immédiatement notifié.", style="font-size:0.9rem; color:#475569;"),
                        style="background:#f8fafc; border:1px solid #e2e8f0; padding:1rem; border-radius:8px;"
                    ),
                    Div(
                        Strong("3. Échangez dans votre salon privé"),
                        P("Discutez en direct avec vos binômes dans une messagerie dédiée sécurisée pour valider votre accord de permutation.", style="font-size:0.9rem; color:#475569;"),
                        style="background:#f8fafc; border:1px solid #e2e8f0; padding:1rem; border-radius:8px;"
                    ),
                    style="display:grid; grid-template-columns:repeat(auto-fit, minmax(250px, 1fr)); gap:1rem;"
                ),
                style="padding:1.5rem; border-radius:12px; margin-bottom:2rem;"
            ),
            cls="container"
        ),
        render_footer()
    )

# === VUE 2 : DÉPOSER UNE NOUVELLE DEMANDE ===
@rt("/deposer")
def get(session, req: Request = None):
    current_u = get_session_user(session, req)
    if not current_u:
        return Main(
            render_header(session, "deposer", req),
            Div(
                Article(
                    H3("🔒 Connexion requise", style="color:#1e3a8a; font-weight:800;"),
                    P("Pour déposer une proposition de permutation de stage, veuillez vous connecter ou créer votre compte étudiant."),
                    Div(
                        A("Se connecter / S'inscrire", href="/login-view", role="button", cls="primary", style="margin-right:0.5rem;"),
                        A("Consulter le catalogue public", href="/catalogue", role="button", cls="outline"),
                    ),
                    style="text-align:center; padding:2.5rem;"
                ),
                cls="container"
            ),
            render_footer()
        )

    user_email = current_u.get("email", "")
    nom = current_u.get("nom", "")
    prenom = current_u.get("prenom", "")

    hospital_options = [Option(h, value=h) for h in ALL_HOSPITALS]
    period_options = [Option(p, value=p) for p in PERIODES]
    spec_options = [Option(s, value=s) for s in SPECIALITES]

    form_content = Form(
        # Bloc d'identité
        Div(
            Div(
                Label("Prénom *", Input(type="text", name="prenom", value=prenom, required=True, readonly=bool(prenom))),
                cls="col"
            ),
            Div(
                Label("Nom *", Input(type="text", name="nom", value=nom, required=True, readonly=bool(nom))),
                cls="col"
            ),
            Div(
                Label("Email institutionnel *", Input(type="email", name="email", value=user_email, required=True, readonly=True)),
                cls="col"
            ),
            style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:1rem; margin-bottom:1rem;"
        ),
        # Bloc stage offert
        Div(
            Div(
                Label("Période de stage *", Select(*period_options, name="periode", required=True)),
                cls="col"
            ),
            Div(
                Label("Spécialité médicale *", Select(*spec_options, name="specialite", required=True)),
                cls="col"
            ),
            Div(
                Label("Lieu de stage actuellement attribué *", Select(*hospital_options, name="hopital_actuel", id="hopital_actuel_select", required=True)),
                cls="col"
            ),
            style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:1rem; margin-bottom:1.25rem;"
        ),
        # Sélecteur moderne d'hôpitaux souhaités
        render_hospital_selector(current_selected=[], current_offered=""),
        # Bouton de soumission
        Button(
            "🚀 Enregistrer et publier ma proposition de stage",
            type="submit",
            cls="primary",
            style="width:100%; font-weight:700; font-size:1.05rem; padding:0.85rem; border-radius:8px;"
        ),
        method="post",
        action="/sauvegarder-demande",
        hx_post="/sauvegarder-demande",
        hx_target="#deposer-feedback",
        hx_swap="innerHTML"
    )

    return Main(
        render_header(session, "deposer", req),
        Div(
            Div(id="deposer-feedback"),
            Article(
                H2("📝 Déposer une proposition de stage", style="font-weight:800; color:#1e293b; margin-bottom:0.25rem;"),
                P("Remplissez vos critères de stage. Notre algorithme cherchera automatiquement les permutations possibles.", style="color:#64748b; margin-bottom:1.5rem;"),
                form_content,
                style="padding:2rem; border-radius:12px; background:#ffffff; border:1px solid #e2e8f0;"
            ),
            cls="container"
        ),
        render_footer()
    )

@rt("/sauvegarder-demande")
async def post(req: Request, session):
    form_data = await req.form()
    current_u = get_session_user(session, req)
    if not current_u:
        return Article(
            P("Veuillez vous connecter pour enregistrer une demande.", style="color:#dc2626; font-weight:700;"),
            style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:8px;"
        )

    user_email = current_u.get("email")
    nom = form_data.get("nom", current_u.get("nom", ""))
    prenom = form_data.get("prenom", current_u.get("prenom", ""))
    periode = form_data.get("periode")
    specialite = form_data.get("specialite")
    hopital_actuel = form_data.get("hopital_actuel")

    # Récupération de la liste multiple des cases à cocher
    hopitaux_souhaites = form_data.getlist("hopitaux_souhaites")

    if not hopitaux_souhaites:
        return Article(
            P("⚠️ Veuillez sélectionner au moins un hôpital souhaité pour la permutation.", style="color:#b45309; font-weight:700; margin:0;"),
            style="background:#fffbeb; border:1px solid #fde68a; padding:1rem; border-radius:8px; margin-bottom:1rem;"
        )

    if hopital_actuel in hopitaux_souhaites:
        return Article(
            P("⚠️ Votre hôpital actuel ne peut pas figurer dans votre liste de souhaits.", style="color:#b45309; font-weight:700; margin:0;"),
            style="background:#fffbeb; border:1px solid #fde68a; padding:1rem; border-radius:8px; margin-bottom:1rem;"
        )

    try:
        doc_id = save_demande(
            user_email=user_email,
            nom=nom,
            prenom=prenom,
            periode=periode,
            specialite=specialite,
            hopital_actuel=hopital_actuel,
            hopitaux_souhaites=hopitaux_souhaites,
            statut="Disponible"
        )

        return Article(
            H4("🎉 Proposition enregistrée avec succès !", style="color:#15803d; font-weight:800; margin-bottom:0.4rem;"),
            P(f"Votre offre pour la période {periode} en {specialite} est désormais active et persistée dans Firestore."),
            Div(
                A("Voir mes correspondances", href="/matchs", role="button", cls="primary", style="margin-right:0.5rem;"),
                A("Consulter le catalogue", href="/catalogue", role="button", cls="outline"),
                style="margin-top:0.75rem;"
            ),
            style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:1.25rem; border-radius:8px; margin-bottom:1.5rem;"
        )
    except Exception as e:
        logger.error(f"Erreur sauvegarde demande: {e}")
        return Article(
            P(f"Erreur lors de l'enregistrement : {str(e)}", style="color:#dc2626; font-weight:700;"),
            style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:8px;"
        )

# === VUE 3 : MES MATCHS & SALONS PRIVÉS ===
@rt("/matchs")
def get(session, req: Request = None):
    current_u = get_session_user(session, req)
    if not current_u:
        return Main(
            render_header(session, "matchs", req),
            Div(
                Article(
                    H3("🔒 Espace Privé", style="color:#1e3a8a; font-weight:800;"),
                    P("Veuillez vous connecter pour visualiser les correspondances bilatérales et triangulaires calculées pour vos stages."),
                    A("Connexion / Inscription", href="/login-view", role="button", cls="primary"),
                    style="text-align:center; padding:2.5rem;"
                ),
                cls="container"
            ),
            render_footer()
        )

    user_email = current_u.get("email", "").lower().strip()
    df_demandes = load_demandes_data()
    bilateral_all = compute_bilateral_matches(df_demandes)
    triangular_all = compute_triangular_matches(df_demandes)

    # Filtrer strictement pour l'utilisateur connecté
    my_bilateral = [
        m for m in bilateral_all
        if m["etudiant_1"]["email"].lower().strip() == user_email or m["etudiant_2"]["email"].lower().strip() == user_email
    ]

    my_triangular = [
        m for m in triangular_all
        if any(p["email"].lower().strip() == user_email for p in m["participants"])
    ]

    bilateral_cards = []
    for m in my_bilateral:
        is_u1 = (m["etudiant_1"]["email"].lower().strip() == user_email)
        binome = m["etudiant_2"] if is_u1 else m["etudiant_1"]
        me = m["etudiant_1"] if is_u1 else m["etudiant_2"]

        card = Div(
            Div(
                Span(f"🔄 PERMUTATION DIRECTE • {m['periode']} • {m['specialite']}", style="font-weight:800; font-size:0.82rem; color:#1d4ed8; text-transform:uppercase; letter-spacing:0.05em;"),
                Span("Match parfait", cls="status-badge status-disponible"),
                style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;"
            ),
            Div(
                Div(
                    Div("Votre stage actuel :", style="font-size:0.8rem; color:#64748b; font-weight:600;"),
                    Div(me["hopital_actuel"], style="font-weight:700; color:#0f172a;"),
                    style="background:#f8fafc; padding:0.75rem; border-radius:8px; border:1px solid #e2e8f0;"
                ),
                Div(
                    Div(f"Stage de {binome['nom']} :", style="font-size:0.8rem; color:#64748b; font-weight:600;"),
                    Div(binome["hopital_actuel"], style="font-weight:700; color:#1d4ed8;"),
                    style="background:#eff6ff; padding:0.75rem; border-radius:8px; border:1px solid #bfdbfe;"
                ),
                style="display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-bottom:1.25rem;"
            ),
            Div(
                A("💬 Ouvrir le salon privé", href=f"/chat/{m['room_id']}", role="button", cls="primary", style="border-radius:8px; font-weight:700;"),
                style="display:flex; justify-content:flex-end;"
            ),
            cls="match-card-bilateral"
        )
        bilateral_cards.append(card)

    triangular_cards = []
    for m in my_triangular:
        cycle_items = []
        for step in m["cycle"]:
            item = Li(
                Strong(step["donneur"]), f" cède sa place à {step['hopital']} pour ", Strong(step["receveur"]),
                style="margin-bottom:0.35rem;"
            )
            cycle_items.append(item)

        card = Div(
            Div(
                Span(f"♻️ ÉCHANGE TRIANGULAIRE • {m['periode']} • {m['specialite']}", style="font-weight:800; font-size:0.82rem; color:#7c3aed; text-transform:uppercase; letter-spacing:0.05em;"),
                Span("Cycle à 3 étudiants", cls="status-badge status-accord"),
                style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;"
            ),
            Ol(*cycle_items, style="background:#faf5ff; padding:1rem 1.75rem; border-radius:8px; border:1px solid #e9d5ff; font-size:0.9rem; margin-bottom:1.25rem;"),
            Div(
                A("💬 Ouvrir le salon privé triangulaire", href=f"/chat/{m['room_id']}", role="button", style="background:#7c3aed; border-color:#7c3aed; border-radius:8px; font-weight:700;"),
                style="display:flex; justify-content:flex-end;"
            ),
            cls="match-card-triangular"
        )
        triangular_cards.append(card)

    has_matches = bool(bilateral_cards or triangular_cards)

    return Main(
        render_header(session, "matchs", req),
        Div(
            H2("🎯 Mes Correspondances de Stage", style="font-weight:800; color:#1e293b; margin-bottom:0.25rem;"),
            P("Consultez les résultats de matching calculés en temps réel à partir de vos vœux d'hôpitaux souhaités.", style="color:#64748b; margin-bottom:1.75rem;"),
            (
                Div(
                    H3(f"🤝 Correspondances bilatérales directes ({len(bilateral_cards)})", style="font-weight:700; color:#1e3a8a; margin-bottom:1rem;"),
                    *bilateral_cards if bilateral_cards else [P("Aucune permutation directe trouvée pour l'instant.", style="color:#64748b; font-style:italic; margin-bottom:2rem;")],
                    H3(f"♻️ Échanges triangulaires ({len(triangular_cards)})", style="font-weight:700; color:#6b21a8; margin-top:2rem; margin-bottom:1rem;"),
                    *triangular_cards if triangular_cards else [P("Aucun cycle triangulaire trouvé pour l'instant.", style="color:#64748b; font-style:italic;")],
                )
                if has_matches else
                Article(
                    H3("Aucune correspondance trouvée pour le moment", style="color:#1e3a8a; font-weight:800;"),
                    P("Dès qu'un autre étudiant dépose une offre compatible avec vos souhaits, la correspondance apparaîtra ici et vous recevrez une alerte."),
                    Div(
                        A("Élargir mes hôpitaux souhaités", href="/gerer", role="button", cls="primary", style="margin-right:0.5rem;"),
                        A("Déposer une autre période", href="/deposer", role="button", cls="outline"),
                    ),
                    style="text-align:center; padding:2.5rem; border-radius:12px;"
                )
            ),
            cls="container"
        ),
        render_footer()
    )

# === SALON PRIVÉ DE DISCUSSION (CHAT) ===
@rt("/chat/{room_id}")
def get(room_id: str, session, req: Request = None):
    current_u = get_session_user(session, req)
    if not current_u:
        return RedirectResponse("/login-view")

    user_email = current_u.get("email", "").lower().strip()
    user_name = f"{current_u.get('prenom', '')} {current_u.get('nom', '')}".strip() or user_email

    messages = load_messages_for_room(room_id)
    chat_elements = []

    for m in messages:
        sender_email = m.get("sender_email", "").lower().strip()
        is_me = (sender_email == user_email)
        bubble = Div(
            Div(
                Strong(m.get("sender_name", "Étudiant")),
                Span(f" • {m.get('timestamp', '')[:16].replace('T', ' ')}", style="font-size:0.72rem; opacity:0.8; margin-left:0.35rem;"),
                style="font-size:0.75rem; margin-bottom:0.25rem; font-weight:600;"
            ),
            Div(m.get("message", ""), style="word-break:break-word;"),
            cls=f"chat-bubble {'chat-bubble-mine' if is_me else 'chat-bubble-other'}"
        )
        chat_elements.append(bubble)

    return Main(
        render_header(session, "matchs", req),
        Div(
            Div(
                A("← Retour à mes correspondances", href="/matchs", style="text-decoration:none; font-weight:600; font-size:0.9rem; color:#1d4ed8; margin-bottom:1rem; display:inline-block;"),
                H2(f"💬 Salon Privé de Négociation", style="font-weight:800; color:#0f172a; margin-bottom:0.25rem;"),
                P("Échangez directement avec vos binômes pour confirmer votre volonté de permuter auprès des coordinations hospitalières.", style="color:#64748b; font-size:0.9rem; margin-bottom:1.5rem;"),
                # Zone des messages
                Div(
                    Div(*chat_elements if chat_elements else [P("Aucun message pour l'instant. Initiez la conversation !", style="color:#94a3b8; font-style:italic; text-align:center; padding:2rem;")]),
                    id="chat-messages-container",
                    style="max-height:450px; overflow-y:auto; background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:1.25rem; margin-bottom:1.25rem; display:flex; flex-direction:column;"
                ),
                # Formulaire d'envoi de message HTMX
                Form(
                    Input(type="hidden", name="room_id", value=room_id),
                    Input(type="hidden", name="sender_name", value=user_name),
                    Div(
                        Input(
                            type="text",
                            name="message",
                            id="chat-input-box",
                            placeholder="Écrivez votre message ici (ex: Je suis disponible pour permuter le planning...)...",
                            required=True,
                            autocomplete="off",
                            style="margin:0; flex:1;"
                        ),
                        Button("Envoyer", type="submit", cls="primary", style="margin:0; width:auto; font-weight:700;"),
                        style="display:flex; gap:0.5rem;"
                    ),
                    method="post",
                    action=f"/chat/{room_id}/send",
                    hx_post=f"/chat/{room_id}/send",
                    hx_target="#chat-messages-container",
                    hx_swap="innerHTML",
                    hx_on="htmx:afterRequest: document.getElementById('chat-input-box').value = ''; var c = document.getElementById('chat-messages-container'); c.scrollTop = c.scrollHeight;"
                ),
                style="background:#ffffff; padding:2rem; border-radius:12px; border:1px solid #e2e8f0; box-shadow:0 1px 3px rgba(0,0,0,0.05);"
            ),
            cls="container"
        ),
        render_footer()
    )

@rt("/chat/{room_id}/send")
async def post(room_id: str, req: Request, session):
    form_data = await req.form()
    current_u = get_session_user(session, req)
    if not current_u:
        return P("Session expirée. Veuillez vous reconnecter.")

    user_email = current_u.get("email", "").lower().strip()
    sender_name = form_data.get("sender_name") or f"{current_u.get('prenom', '')} {current_u.get('nom', '')}".strip() or user_email
    message = form_data.get("message", "").strip()

    if message:
        save_chat_message(room_id, user_email, sender_name, message)

    messages = load_messages_for_room(room_id)
    chat_elements = []
    for m in messages:
        s_email = m.get("sender_email", "").lower().strip()
        is_me = (s_email == user_email)
        bubble = Div(
            Div(
                Strong(m.get("sender_name", "Étudiant")),
                Span(f" • {m.get('timestamp', '')[:16].replace('T', ' ')}", style="font-size:0.72rem; opacity:0.8; margin-left:0.35rem;"),
                style="font-size:0.75rem; margin-bottom:0.25rem; font-weight:600;"
            ),
            Div(m.get("message", ""), style="word-break:break-word;"),
            cls=f"chat-bubble {'chat-bubble-mine' if is_me else 'chat-bubble-other'}"
        )
        chat_elements.append(bubble)

    return Div(*chat_elements)

# === VUE 4 : CATALOGUE PUBLIC DES OFFRES DISPONIBLES ===
@rt("/catalogue")
def get(session, periode: str = "", specialite: str = "", search: str = "", req: Request = None):
    df = load_demandes_data()

    # Application des filtres
    if not df.empty:
        if periode:
            df = df[df["periode"] == periode]
        if specialite:
            df = df[df["specialite"] == specialite]
        if search:
            s = search.lower().strip()
            df = df[
                df["hopital_actuel"].str.lower().str.contains(s) |
                df["hopitaux_souhaites"].str.lower().str.contains(s) |
                df["specialite"].str.lower().str.contains(s)
            ]

    period_options = [Option("Toutes les périodes", value="")] + [
        Option(p, value=p, selected=(p == periode)) for p in PERIODES
    ]
    spec_options = [Option("Toutes les spécialités", value="")] + [
        Option(s, value=s, selected=(s == specialite)) for s in SPECIALITES
    ]

    filter_bar = Form(
        Div(
            Div(Select(*period_options, name="periode", onchange="this.form.submit()")),
            Div(Select(*spec_options, name="specialite", onchange="this.form.submit()")),
            Div(Input(type="search", name="search", value=search, placeholder="Rechercher un hôpital...")),
            Div(Button("Filtrer", type="submit", cls="outline", style="width:100%;")),
            style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:0.75rem; margin-bottom:1.5rem;"
        ),
        method="get",
        action="/catalogue"
    )

    table_rows = []
    if not df.empty:
        for idx, row in df.iterrows():
            statut_val = row.get("statut", "Disponible")
            badge_cls = "status-disponible" if statut_val == "Disponible" else ("status-discussion" if statut_val == "En discussion" else "status-accord")

            souhaites_list = parse_hospitals(row.get("hopitaux_souhaites"))
            souhaites_rendered = ", ".join(souhaites_list[:3])
            if len(souhaites_list) > 3:
                souhaites_rendered += f" (+{len(souhaites_list)-3} autres)"

            tr = Tr(
                Td(Strong(row.get("periode", ""))),
                Td(row.get("specialite", "")),
                Td(Strong(row.get("hopital_actuel", ""), style="color:#1d4ed8;")),
                Td(souhaites_rendered or "Ouvert à proposition", style="font-size:0.85rem; color:#475569;"),
                Td(Span(statut_val, cls=f"status-badge {badge_cls}")),
                Td(row.get("timestamp", "")[:10], style="font-size:0.8rem; color:#94a3b8;")
            )
            table_rows.append(tr)

    return Main(
        render_header(session, "catalogue", req),
        Div(
            H2("📖 Catalogue Public des Stages", style="font-weight:800; color:#1e293b; margin-bottom:0.25rem;"),
            P("Consultez l'ensemble des propositions de permutation déposées par les étudiants pour les sessions P3 à P8.", style="color:#64748b; margin-bottom:1.5rem;"),
            filter_bar,
            Div(
                Table(
                    Thead(
                        Tr(
                            Th("Période"),
                            Th("Spécialité"),
                            Th("Lieu actuel proposé"),
                            Th("Lieux souhaités"),
                            Th("Statut"),
                            Th("Date")
                        )
                    ),
                    Tbody(*table_rows if table_rows else [Tr(Td("Aucune offre correspondant aux critères.", colspan=6, style="text-align:center; padding:2rem; color:#64748b;"))]),
                    cls="striped"
                ),
                style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; overflow-x:auto;"
            ),
            cls="container"
        ),
        render_footer()
    )

# === VUE 5 : GÉRER MON OFFRE DE STAGE ===
@rt("/gerer")
def get(session, req: Request = None):
    current_u = get_session_user(session, req)
    if not current_u:
        return Main(
            render_header(session, "gerer", req),
            Div(
                Article(
                    H3("🔒 Authentification requise", style="color:#1e3a8a; font-weight:800;"),
                    P("Connectez-vous pour modifier vos souhaits d'hôpitaux ou changer le statut de votre offre."),
                    A("Connexion / Inscription", href="/login-view", role="button", cls="primary"),
                    style="text-align:center; padding:2.5rem;"
                ),
                cls="container"
            ),
            render_footer()
        )

    user_email = current_u.get("email", "").lower().strip()
    df = load_demandes_data()
    my_demandes = df[df["user_email"].str.lower().str.strip() == user_email] if not df.empty else pd.DataFrame()

    cards = []
    if not my_demandes.empty:
        for idx, row in my_demandes.iterrows():
            d_id = row.get("id")
            cur_statut = row.get("statut", "Disponible")
            selected_wants = parse_hospitals(row.get("hopitaux_souhaites"))

            # Formulaire de modification
            card = Article(
                Div(
                    H3(f"Stage {row.get('periode')} • {row.get('specialite')}", style="font-weight:800; margin:0; color:#0f172a;"),
                    Span(cur_statut, cls=f"status-badge {'status-disponible' if cur_statut=='Disponible' else ('status-discussion' if cur_statut=='En discussion' else 'status-accord')}"),
                    style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;"
                ),
                P(Strong("Lieu actuel : "), row.get("hopital_actuel")),
                Form(
                    Input(type="hidden", name="demande_id", value=d_id),
                    Label(
                        "Modifier le statut de l'offre :",
                        Select(
                            Option("Disponible", value="Disponible", selected=(cur_statut=="Disponible")),
                            Option("En discussion", value="En discussion", selected=(cur_statut=="En discussion")),
                            Option("Accord trouvé", value="Accord trouvé", selected=(cur_statut=="Accord trouvé")),
                            name="nouveau_statut",
                            onchange="this.form.submit()"
                        ),
                        style="max-width:300px; margin-bottom:1.5rem;"
                    ),
                    method="post",
                    action="/gerer/changer-statut"
                ),
                H4("Mettre à jour mes hôpitaux souhaités", style="font-weight:700; margin-top:1rem;"),
                Form(
                    Input(type="hidden", name="demande_id", value=d_id),
                    Input(type="hidden", name="periode", value=row.get("periode")),
                    Input(type="hidden", name="specialite", value=row.get("specialite")),
                    Input(type="hidden", name="hopital_actuel", value=row.get("hopital_actuel")),
                    render_hospital_selector(current_selected=selected_wants, current_offered=row.get("hopital_actuel")),
                    Div(
                        Button("Enregistrer les modifications", type="submit", cls="primary", style="border-radius:8px; font-weight:700;"),
                        A("Supprimer cette offre", href=f"/gerer/supprimer/{d_id}", role="button", cls="secondary outline", onclick="return confirm('Confirmer la suppression de cette demande ?');", style="border-radius:8px; margin-left:0.5rem;"),
                        style="display:flex; justify-content:space-between; margin-top:1rem;"
                    ),
                    method="post",
                    action="/gerer/modifier-souhaits"
                ),
                style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:1.75rem; margin-bottom:2rem;"
            )
            cards.append(card)

    return Main(
        render_header(session, "gerer", req),
        Div(
            H2("⚙️ Gérer mon Offre de Stage", style="font-weight:800; color:#1e293b; margin-bottom:0.25rem;"),
            P("Ajustez votre liste de vœux d'hôpitaux ou mettez à jour votre statut de disponibilité.", style="color:#64748b; margin-bottom:1.75rem;"),
            *cards if cards else [
                Article(
                    H3("Vous n'avez aucune offre active pour le moment"),
                    P("Déposez dès maintenant votre première proposition de permutation de stage."),
                    A("Déposer une offre", href="/deposer", role="button", cls="primary"),
                    style="text-align:center; padding:2.5rem;"
                )
            ],
            cls="container"
        ),
        render_footer()
    )

@rt("/gerer/changer-statut")
async def post(req: Request, session):
    form_data = await req.form()
    demande_id = form_data.get("demande_id")
    nouveau_statut = form_data.get("nouveau_statut")
    if demande_id and nouveau_statut:
        update_demande_statut(demande_id, nouveau_statut)
    return RedirectResponse("/gerer", status_code=303)

@rt("/gerer/modifier-souhaits")
async def post(req: Request, session):
    form_data = await req.form()
    current_u = get_session_user(session, req)
    if not current_u:
        return RedirectResponse("/login-view")

    demande_id = form_data.get("demande_id")
    periode = form_data.get("periode")
    specialite = form_data.get("specialite")
    hopital_actuel = form_data.get("hopital_actuel")
    hopitaux_souhaites = form_data.getlist("hopitaux_souhaites")

    if demande_id and hopitaux_souhaites:
        save_demande(
            user_email=current_u["email"],
            nom=current_u.get("nom", ""),
            prenom=current_u.get("prenom", ""),
            periode=periode,
            specialite=specialite,
            hopital_actuel=hopital_actuel,
            hopitaux_souhaites=hopitaux_souhaites,
            demande_id=demande_id
        )
    return RedirectResponse("/gerer", status_code=303)

@rt("/gerer/supprimer/{demande_id}")
def get(demande_id: str, session):
    delete_demande(demande_id)
    return RedirectResponse("/gerer", status_code=303)

# ---------------------------------------------------------------------------
# 11. AUTHENTIFICATION & GESTION DE COMPTE (PERSISTANCE FIRESTORE)
# ---------------------------------------------------------------------------

@rt("/login-view")
def get(session, req: Request = None):
    return Main(
        render_header(session, "accueil", req),
        Div(
            Div(
                # Formulaire Connexion
                Article(
                    H3("🔐 Connexion Étudiant", style="font-weight:800; color:#1e293b; margin-bottom:0.25rem;"),
                    P("Accédez à vos correspondances et vos salons privés.", style="color:#64748b; font-size:0.9rem; margin-bottom:1.25rem;"),
                    Div(id="login-feedback"),
                    Form(
                        Label("Email universitaire (@student.* / @uclouvain.be / etc.) *", Input(type="email", name="email", placeholder="prenom.nom@student.uclouvain.be", required=True)),
                        Label("Code PIN secret (4 chiffres) *", Input(type="password", name="code_pin", pattern="[0-9]{4}", maxlength="4", placeholder="Ex: 1234", required=True)),
                        Button("Se connecter", type="submit", cls="primary", style="width:100%; font-weight:700; margin-top:0.75rem; border-radius:8px;"),
                        Div(
                            A("Code PIN oublié ?", href="/forgot-pin-view", style="font-size:0.85rem; color:#1d4ed8;"),
                            style="text-align:right; margin-top:0.5rem;"
                        ),
                        method="post",
                        action="/login",
                        hx_post="/login",
                        hx_target="#login-feedback",
                        hx_swap="innerHTML"
                    ),
                    style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:2rem;"
                ),
                # Formulaire Inscription
                Article(
                    H3("✨ Première Visite ? Inscription", style="font-weight:800; color:#1e293b; margin-bottom:0.25rem;"),
                    P("Créez votre profil étudiant en 30 secondes chrono.", style="color:#64748b; font-size:0.9rem; margin-bottom:1.25rem;"),
                    Div(id="register-feedback"),
                    Form(
                        Div(
                            Div(Label("Prénom *", Input(type="text", name="prenom", placeholder="Ex: Thomas", required=True))),
                            Div(Label("Nom *", Input(type="text", name="nom", placeholder="Ex: Dupont", required=True))),
                            style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem;"
                        ),
                        Label("Email universitaire *", Input(type="email", name="email", placeholder="votre.nom@student.uclouvain.be", required=True)),
                        Label("Choisissez un Code PIN (4 chiffres) *", Input(type="password", name="code_pin", pattern="[0-9]{4}", maxlength="4", placeholder="Ex: 5678", required=True)),
                        Button("Créer mon compte", type="submit", cls="outline", style="width:100%; font-weight:700; margin-top:0.75rem; border-radius:8px;"),
                        method="post",
                        action="/inscription",
                        hx_post="/inscription",
                        hx_target="#register-feedback",
                        hx_swap="innerHTML"
                    ),
                    style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:2rem;"
                ),
                style="display:grid; grid-template-columns:repeat(auto-fit, minmax(320px, 1fr)); gap:2rem; margin-top:1.5rem;"
            ),
            cls="container"
        ),
        render_footer()
    )

@rt("/login")
async def post(req: Request, session):
    form_data = await req.form()
    email = str(form_data.get("email", "")).strip().lower()
    code_pin = str(form_data.get("code_pin", "")).strip()

    user = verify_user_login(email, code_pin)
    if user:
        em_clean = user.get("email", email).strip().lower()
        session["user_id"] = em_clean
        session["user_email"] = em_clean
        session["email"] = em_clean
        session["nom"] = user.get("nom", user.get("Nom", ""))
        session["prenom"] = user.get("prenom", user.get("Prenom", ""))
        session["pin"] = user.get("code_pin", user.get("PIN", code_pin))

        display_name = f"{session['prenom']} {session['nom']}".strip() or em_clean

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
        P("Email ou code PIN incorrect. Veuillez réessayer.", style="color:#b91c1c; font-weight:600; margin:0;"),
        style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:10px; margin-bottom:1rem;"
    )

@rt("/inscription")
@rt("/register")
async def post(req: Request, session):
    form_data = await req.form()
    email = str(form_data.get("email", "")).strip().lower()
    nom = str(form_data.get("nom", "")).strip()
    prenom = str(form_data.get("prenom", "")).strip()
    code_pin = str(form_data.get("code_pin", "")).strip()

    if not email or "@" not in email:
        return Article(
            P("Veuillez saisir une adresse email valide.", style="color:#b91c1c; font-weight:600; margin:0;"),
            style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:10px; margin-bottom:1rem;"
        )

    if len(code_pin) != 4 or not code_pin.isdigit():
        return Article(
            P("Le code PIN doit comporter exactement 4 chiffres numériques.", style="color:#b91c1c; font-weight:600; margin:0;"),
            style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:10px; margin-bottom:1rem;"
        )

    existing = get_user_by_email(email)
    if existing:
        return Article(
            P("Un compte existe déjà avec cette adresse email. Veuillez vous connecter.", style="color:#b45309; font-weight:600; margin:0;"),
            style="background:#fffbeb; border:1px solid #fde68a; padding:1rem; border-radius:10px; margin-bottom:1rem;"
        )

    success = save_user(email, nom, prenom, code_pin)
    if success:
        e_clean = email.lower().strip()
        p_clean = prenom.strip()
        n_clean = nom.strip()
        session["user_id"] = e_clean
        session["user_email"] = e_clean
        session["email"] = e_clean
        session["nom"] = n_clean
        session["prenom"] = p_clean
        session["pin"] = code_pin

        return Article(
            H4(f"🎉 Compte créé et enregistré dans Firestore ! Bienvenue {p_clean}.", style="color:#14532d; font-weight:800; margin-bottom:0.4rem;"),
            P("Votre compte persiste désormais dans la collection 'users' de Firestore. Vous êtes automatiquement connecté."),
            Div(
                A("Déposer ma première offre", href="/deposer", role="button", cls="primary", style="margin-right:0.5rem; border-radius:8px;"),
                A("Consulter le catalogue", href="/catalogue", role="button", cls="outline", style="border-radius:8px;"),
                style="margin-top:0.75rem;"
            ),
            Script(f"""
                localStorage.setItem('permutstage_auth_email', '{e_clean}');
                sessionStorage.removeItem('permutstage_logged_out');
            """),
            style="background:#f0fdf4; border:1px solid #86efac; color:#14532d; padding:1.25rem; border-radius:12px; margin-bottom:1.5rem;"
        )

    return Article(
        P("Erreur lors de l'enregistrement du compte dans Firestore. Veuillez réessayer.", style="color:#b91c1c; font-weight:600; margin:0;"),
        style="background:#fef2f2; border:1px solid #fecaca; padding:1rem; border-radius:10px; margin-bottom:1rem;"
    )

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
                    Label("Adresse email étudiante *", Input(type="email", name="email", required=True)),
                    Button("M'envoyer mon code PIN", type="submit", cls="primary", style="width:100%; margin-top:0.75rem; border-radius:8px;"),
                    method="post",
                    action="/recuperer-pin",
                    hx_post="/recuperer-pin",
                    hx_target="#forgot-feedback",
                    hx_swap="innerHTML"
                ),
                style="max-width:500px; margin:2rem auto; background:#ffffff; padding:2rem; border-radius:12px; border:1px solid #e2e8f0;"
            ),
            cls="container"
        ),
        render_footer()
    )

@rt("/recuperer-pin")
async def post(req: Request):
    form_data = await req.form()
    email = str(form_data.get("email", "")).strip().lower()
    user = get_user_by_email(email)

    if not user:
        return Article(
            P("Aucun compte étudiant trouvé avec cette adresse email.", style="color:#dc2626; margin:0;"),
            style="background:#fef2f2; padding:1rem; border-radius:8px; margin-bottom:1rem;"
        )

    pin = user.get("code_pin", user.get("PIN", ""))
    nom = user.get("nom", user.get("prenom", "Étudiant"))
    body = f"""
    <h3>Bonjour {nom},</h3>
    <p>Vous avez demandé le rappel de votre code PIN pour la plateforme PermutStage.</p>
    <p style="font-size:1.25rem; font-weight:bold; color:#1d4ed8;">Votre code PIN : {pin}</p>
    <p>Conservez-le précieusement.</p>
    """
    send_smtp_email(email, "🔑 PermutStage : Rappel de votre code PIN", body)

    return Article(
        P(f"Votre code PIN a été envoyé à {email}. Vérifiez votre boîte de réception.", style="color:#15803d; font-weight:700; margin:0;"),
        style="background:#f0fdf4; border:1px solid #86efac; padding:1rem; border-radius:8px; margin-bottom:1rem;"
    )

# === CENTRE DE NOTIFICATIONS ===
@rt("/notifications")
def get(session, req: Request = None):
    current_u = get_session_user(session, req)
    if not current_u:
        return RedirectResponse("/login-view")

    user_email = current_u.get("email", "").lower().strip()
    df_demandes = load_demandes_data()
    bilateral_matches = compute_bilateral_matches(df_demandes)
    triangular_matches = compute_triangular_matches(df_demandes)

    my_b = [m for m in bilateral_matches if m["etudiant_1"]["email"].lower().strip() == user_email or m["etudiant_2"]["email"].lower().strip() == user_email]
    my_t = [m for m in triangular_matches if any(p["email"].lower().strip() == user_email for p in m["participants"])]

    cards = []
    for b in my_b:
        cards.append(Article(
            H4("🎉 Nouvelle correspondance bilatérale disponible !", style="color:#1d4ed8; margin-bottom:0.25rem;"),
            P(f"Une permutation directe est possible pour votre stage de {b['specialite']} ({b['periode']})."),
            A("Accéder au salon de discussion", href=f"/chat/{b['room_id']}", role="button", cls="primary", style="border-radius:8px;"),
            style="border-left:4px solid #1d4ed8; padding:1.25rem; margin-bottom:1rem; background:#ffffff;"
        ))

    for t in my_t:
        cards.append(Article(
            H4("♻️ Opportunité d'échange triangulaire !", style="color:#7c3aed; margin-bottom:0.25rem;"),
            P(f"Un cycle d'échange à 3 étudiants est complet pour {t['specialite']} ({t['periode']})."),
            A("Rejoindre le salon triangulaire", href=f"/chat/{t['room_id']}", role="button", style="background:#7c3aed; border-color:#7c3aed; border-radius:8px;"),
            style="border-left:4px solid #7c3aed; padding:1.25rem; margin-bottom:1rem; background:#ffffff;"
        ))

    if not cards:
        cards.append(Article(
            P("Aucune notification non lue. Vous êtes à jour !", style="color:#64748b; font-style:italic; text-align:center; padding:2rem;"),
            style="background:#ffffff; border:1px solid #e2e8f0; border-radius:8px;"
        ))

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
                Form(
                    Label("Mot de passe administrateur *", Input(type="password", name="admin_password", required=True)),
                    Button("Accéder au panneau d'administration", type="submit", cls="primary", style="margin-top:0.75rem;"),
                    method="post",
                    action="/admin-login"
                ),
                style="max-width:450px; margin:2rem auto; background:#ffffff; padding:2rem; border-radius:12px; border:1px solid #e2e8f0;"
            ),
            cls="container"
        ),
        render_footer()
    )

@rt("/admin-login")
async def post(req: Request, session):
    form_data = await req.form()
    pwd = form_data.get("admin_password")
    expected = os.environ.get("ADMIN_PASSWORD", "permutstage_admin_2026")
    if pwd == expected:
        session["is_admin"] = True
        return RedirectResponse("/admin", status_code=303)
    return RedirectResponse("/admin-login-view", status_code=303)

@rt("/admin")
def get(session, req: Request = None):
    if not session.get("is_admin", False):
        return RedirectResponse("/admin-login-view")

    df_demandes = load_demandes_data()
    ldb = _read_local_db()

    total_offres = len(df_demandes)
    total_users = 0
    if db is not None:
        try:
            total_users = len(list(db.collection("users").stream()))
        except Exception:
            total_users = len(ldb.get("users", {}))
    else:
        total_users = len(ldb.get("users", {}))

    return Main(
        render_header(session, "admin", req),
        Div(
            H2("🛠️ Panneau d'Administration PermutStage", style="font-weight:800;"),
            Div(
                Div(Div(str(total_users), cls="stat-number"), Div("Comptes étudiants", cls="stat-label"), cls="stat-card"),
                Div(Div(str(total_offres), cls="stat-number"), Div("Demandes actives", cls="stat-label"), cls="stat-card"),
                Div(Div("Firestore", cls="stat-number", style="font-size:1.4rem;"), Div("Moteur Base de données", cls="stat-label"), cls="stat-card"),
                style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:1rem; margin-bottom:2rem;"
            ),
            Article(
                H3("Export et Sauvegarde"),
                P("Téléchargez l'intégralité des données sous format tabulaire CSV."),
                A("Télécharger le CSV des demandes", href="/admin-export-demandes-csv", role="button", cls="outline"),
                style="background:#ffffff; padding:1.5rem; border-radius:10px; border:1px solid #e2e8f0;"
            ),
            cls="container"
        ),
        render_footer()
    )

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

# === ROUTE DE HEALTHCHECK CLOUD (RENDER / KUBERNETES) ===
@rt("/healthz")
@rt("/health")
def get():
    return Response("OK", media_type="text/plain")

# ---------------------------------------------------------------------------
# 12. DÉMARRAGE DU SERVEUR FASTHTML (COMPATIBLE RENDER & LOCAL MAC/LINUX)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    host = os.environ.get("HOST", "0.0.0.0")
    serve(host=host, port=port)
