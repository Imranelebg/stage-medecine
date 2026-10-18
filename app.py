"""
PermutStage — Plateforme Collaborative d'Échange de Lieux de Stage (Médecine P3 à P8)
Architecture complète avec base de données Firebase Firestore (firebase-admin) :
- Comptes Étudiants (Collection 'users' + st.session_state['user'] + st.query_params['auth'])
- Offres de permutation (Collection 'demandes' avec écritures atomiques directes et statuts)
- Messagerie instantanée privée (Collection 'messages' par salon sécurisé)
- Confidentialité stricte des échanges (Matching Privé réservé aux étudiants impliqués)
- Alertes Email automatiques via SMTP (smtplib + email.mime + st.secrets['smtp'])
- Accès Administrateur discret (st.secrets['admin']['password'])
- Mode d'affichage clair strict verrouillé (aucun mode sombre)
"""

import os
import re
import uuid
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import pandas as pd
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ---------------------------------------------------------------------------
# 1. CONFIGURATION DE LA PAGE & STYLE ÉPURÉ (SANS LOGO, MODE CLAIR STRICT)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="PermutStage — Permutation de Stages Médecine",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    /* ==========================================================================
       1. RÉTABLISSEMENT & ACCESSIBILITÉ PERMANENTE DE LA BARRE LATÉRALE (SIDEBAR)
       ========================================================================== */
    header[data-testid="stHeader"] {
        background: transparent !important;
        color: #0f172a !important;
    }

    #MainMenu, footer, footer[data-testid="stFooter"] {
        visibility: hidden !important;
    }

    [data-testid="stToolbarActionButton"], [data-testid="stDecoration"], [data-testid="stStatusWidget"], [data-testid="manage-app-button"] {
        visibility: hidden !important; display: none !important;
    }

    [data-testid="collapsedControl"] {
        display: flex !important; visibility: visible !important; color: #0f172a !important; z-index: 999999 !important;
    }
    [data-testid="collapsedControl"] button {
        color: #0f172a !important; background-color: #f8fafc !important; border: 1px solid #cbd5e1 !important; border-radius: 8px !important;
    }
    [data-testid="collapsedControl"] svg {
        color: #0f172a !important; fill: currentColor !important;
    }

    /* ==========================================================================
       2. FORÇAGE DU MODE CLAIR PAR DÉFAUT (FOND #F8FAFC & TEXTE #1E293B)
       ========================================================================== */
    :root, [data-theme="dark"], [data-theme="light"], .dark, .theme--dark, .stApp, html, body {
        color-scheme: light !important;
        --background-color: #f8fafc !important;
        --secondary-background-color: #ffffff !important;
        --text-color: #1e293b !important;
        --primary-color: #1d4ed8 !important;
        background-color: #f8fafc !important;
        color: #1e293b !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    @media (prefers-color-scheme: dark) {
        :root, [data-theme="dark"], [data-theme="light"], .dark, .theme--dark, html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"], [data-testid="stSidebarContent"], section[data-testid="stSidebar"], .main, .block-container {
            color-scheme: light !important; --background-color: #f8fafc !important; --secondary-background-color: #ffffff !important; --text-color: #1e293b !important; --primary-color: #1d4ed8 !important; background-color: #f8fafc !important; color: #1e293b !important;
        }
        [data-testid="stSidebar"], [data-testid="stSidebar"] > div, [data-testid="stSidebarContent"], section[data-testid="stSidebar"] {
            background-color: #ffffff !important; color: #1e293b !important;
        }
    }

    [data-testid="stAppViewContainer"], .main, .block-container { background-color: #f8fafc !important; color: #1e293b !important; }
    [data-testid="stSidebar"], [data-testid="stSidebar"] > div, [data-testid="stSidebarContent"], section[data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0 !important; color: #1e293b !important; }

    h1, h2, h3, h4, h5, h6 { color: #0f172a !important; font-family: 'Plus Jakarta Sans', sans-serif !important; font-weight: 700 !important; }
    p, span, div, li, td, th { color: #1e293b; }
    .stMarkdown, .stMarkdown p, .stMarkdown li, [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li, [data-testid="stMarkdownContainer"] span { color: #1e293b !important; }
    label, [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] span { color: #0f172a !important; font-weight: 600 !important; font-size: 0.88rem !important; }
    .stCaption, [data-testid="stCaptionContainer"] p, [data-testid="stCaptionContainer"] span { color: #64748b !important; }
    input, textarea, [data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"] { background-color: #ffffff !important; color: #0f172a !important; border-color: #cbd5e1 !important; -webkit-text-fill-color: #0f172a !important; }
    input::placeholder, textarea::placeholder { color: #94a3b8 !important; -webkit-text-fill-color: #94a3b8 !important; }

    /* Menus déroulants */
    [data-baseweb="select"] > div { background-color: #ffffff !important; color: #0f172a !important; border: 1px solid #cbd5e1 !important; }
    [data-baseweb="select"] span { color: #0f172a !important; }
    [data-baseweb="popover"], [data-baseweb="menu"], [data-baseweb="menu"] * { background-color: #ffffff !important; color: #0f172a !important; }
    [data-baseweb="menu"] li:hover, [data-baseweb="menu"] li:hover * { background-color: #f1f5f9 !important; color: #1d4ed8 !important; }

    /* ==========================================================================
       TAGS MULTISELECT & BOUTONS - CORRECTION CONTRASTE (BLANC SUR BLEU)
       ========================================================================== */
    [data-baseweb="tag"] {
        background-color: #1d4ed8 !important;
        border-radius: 6px !important;
    }
    [data-baseweb="tag"] span,
    [data-baseweb="tag"] div,
    [data-baseweb="tag"] * {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        font-weight: 700 !important;
    }
    [data-baseweb="tag"] svg {
        fill: #FFFFFF !important;
        color: #FFFFFF !important;
    }

    button[kind="primary"],
    button[kind="primaryFormSubmit"],
    [data-testid="stFormSubmitButton"] > button,
    .stButton > button[type="submit"] {
        background-color: #1d4ed8 !important;
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        font-weight: 700 !important;
        border: none !important;
    }
    button[kind="primary"] *,
    button[kind="primaryFormSubmit"] *,
    [data-testid="stFormSubmitButton"] > button * {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }

    button[kind="secondary"], .stButton > button { background-color: #ffffff !important; color: #0f172a !important; border: 1px solid #cbd5e1 !important; font-weight: 500 !important; }
    button[kind="secondary"]:hover, .stButton > button:hover { background-color: #f8fafc !important; color: #1d4ed8 !important; border-color: #94a3b8 !important; }

    [data-testid="stExpander"] { background-color: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 10px !important; margin-bottom: 0.75rem !important; }
    [data-testid="stExpander"] summary { background-color: #ffffff !important; color: #0f172a !important; font-weight: 600 !important; }
    [data-testid="stExpander"] summary span, [data-testid="stExpander"] summary p { color: #0f172a !important; }
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] { background-color: #ffffff !important; color: #0f172a !important; }

    [data-baseweb="tab-list"] { background-color: transparent !important; border-bottom: 2px solid #e2e8f0 !important; }
    button[data-baseweb="tab"] { color: #64748b !important; font-weight: 600 !important; }
    button[data-baseweb="tab"][aria-selected="true"] { color: #1d4ed8 !important; font-weight: 700 !important; border-bottom-color: #1d4ed8 !important; }

    [data-testid="stChatMessage"] { background-color: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 10px !important; color: #0f172a !important; padding: 0.75rem 1rem !important; }
    [data-testid="stChatMessage"] p, [data-testid="stChatMessage"] span, [data-testid="stChatMessage"] div { color: #0f172a !important; }
    [data-testid="stDataFrame"], [data-testid="stTable"] { background-color: #ffffff !important; color: #0f172a !important; border: 1px solid #e2e8f0 !important; border-radius: 8px !important; }
    [data-testid="stDataFrame"] * { color: #0f172a !important; }

    /* ==========================================================================
       3. ISOLATION DE LA BANNIÈRE HERO BLEUE (.hero-card) — TEXTES BLANCS PURS
       ========================================================================== */
    .hero-card,
    .hero-card h1,
    .hero-card h2,
    .hero-card h3,
    .hero-card p,
    .hero-card span,
    .hero-card strong,
    .hero-card em,
    .hero-card div,
    [data-testid="stMarkdownContainer"] .hero-card,
    [data-testid="stMarkdownContainer"] .hero-card h1,
    [data-testid="stMarkdownContainer"] .hero-card h2,
    [data-testid="stMarkdownContainer"] .hero-card p,
    [data-testid="stMarkdownContainer"] .hero-card span {
        color: #FFFFFF !important;
    }

    .hero-card {
        background: linear-gradient(135deg, #1e3a8a 0%, #172554 100%) !important;
        color: #ffffff !important;
        padding: 2.2rem 2.4rem !important;
        border-radius: 14px !important;
        margin-bottom: 1.25rem !important;
        box-shadow: 0 4px 16px rgba(15, 23, 42, 0.14) !important;
        border: 1px solid rgba(59, 130, 246, 0.25) !important;
    }

    .hero-card h1 { font-size: 2.1rem !important; font-weight: 800 !important; line-height: 1.25 !important; margin: 0 0 0.5rem 0 !important; }
    .hero-card p { font-size: 1.02rem !important; line-height: 1.65 !important; margin: 0 0 1.25rem 0 !important; max-width: 860px !important; }

    .hero-card .hero-badge { display: inline-block !important; padding: 0.25rem 0.8rem !important; background: rgba(59, 130, 246, 0.25) !important; border: 1px solid rgba(147, 197, 253, 0.35) !important; border-radius: 9999px !important; font-size: 0.8rem !important; font-weight: 700 !important; letter-spacing: 0.05em !important; color: #BFDBFE !important; margin-bottom: 0.85rem !important; }
    .hero-card .hero-alpha-box { background: rgba(255, 255, 255, 0.1) !important; border: 1px solid rgba(255, 255, 255, 0.2) !important; border-radius: 10px !important; padding: 0.95rem 1.15rem !important; font-size: 0.88rem !important; line-height: 1.55 !important; color: #F8FAFC !important; }
    .hero-card .hero-alpha-box strong { color: #FDE047 !important; }
    .hero-card .hero-alpha-box em { color: #FFFFFF !important; }

    /* ==========================================================================
       4. REFONTE VISUELLE : CARTES D'OFFRES DE L'ONGLET 3
       ========================================================================== */
    .offer-card-new {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        padding: 1.25rem !important;
        margin-bottom: 1rem !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04) !important;
        color: #0F172A !important;
    }
    .offer-card-new * { color: #0F172A; }
    
    .badge-periode { background-color: #DBEAFE !important; color: #1E40AF !important; padding: 0.25rem 0.6rem !important; border-radius: 9999px !important; font-weight: 700 !important; font-size: 0.8rem !important; margin-right: 0.5rem; }
    .badge-specialite { background-color: #EDE9FE !important; color: #5B21B6 !important; padding: 0.25rem 0.6rem !important; border-radius: 9999px !important; font-weight: 700 !important; font-size: 0.8rem !important; margin-right: 0.5rem; }
    
    .badge-statut-dispo { background-color: #DCFCE7 !important; color: #166534 !important; padding: 0.25rem 0.6rem !important; border-radius: 9999px !important; font-weight: 700 !important; font-size: 0.8rem !important;}
    .badge-statut-discu { background-color: #FFEDD5 !important; color: #9A3412 !important; padding: 0.25rem 0.6rem !important; border-radius: 9999px !important; font-weight: 700 !important; font-size: 0.8rem !important;}
    .badge-statut-accord { background-color: #E2E8F0 !important; color: #334155 !important; padding: 0.25rem 0.6rem !important; border-radius: 9999px !important; font-weight: 700 !important; font-size: 0.8rem !important;}

    .zone-actuel { background-color: #FFFBEB !important; border: 1px solid #FEF3C7 !important; padding: 0.85rem !important; border-radius: 8px !important; margin-top: 1rem !important; margin-bottom: 0.75rem !important; }
    .zone-souhaites { background-color: #F8FAFC !important; border: 1px solid #F1F5F9 !important; padding: 0.85rem !important; border-radius: 8px !important; }
    
    .chip-hopital {
        display: inline-flex !important; align-items: center; background-color: #FFFFFF !important; border: 1px solid #CBD5E1 !important;
        padding: 0.35rem 0.6rem !important; border-radius: 6px !important; font-size: 0.85rem !important; font-weight: 600 !important;
        margin-right: 0.4rem !important; margin-bottom: 0.4rem !important; box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
    }

    .match-card { background-color: #f0fdf4 !important; border: 1px solid #86efac !important; border-radius: 10px !important; padding: 1.25rem !important; margin-bottom: 1rem !important; color: #14532d !important; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important; }
    .match-card * { color: #14532d !important; }
    .tri-card { background-color: #ecfdf5 !important; border: 1px solid #6ee7b7 !important; border-radius: 10px !important; padding: 1.25rem !important; margin-bottom: 1rem !important; color: #064e3b !important; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important; }
    .tri-card * { color: #064e3b !important; }
    .notif-card { background-color: #eff6ff !important; border: 1px solid #bfdbfe !important; border-radius: 8px !important; padding: 0.9rem 1.1rem !important; margin-bottom: 0.6rem !important; color: #1e3a8a !important; }
    .step-card { background-color: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 10px !important; padding: 1rem !important; min-height: 190px !important; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important; }
    .step-card strong { color: #0f172a !important; }
    .step-card p { color: #475569 !important; }
    </style>
    """,
    unsafe_allow_html=True,
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

# Liste alphabétique stricte et Flandre retirée
HOPITAUX_PAR_REGION = {
    "Brabant wallon": sorted([
        "CHIREC - Hôpital Braine-l'Alleud",
        "CHU HELORA - Hôpital de Nivelles-Tubize",
        "Centre William Lennox (Ottignies)",
        "Clinique Saint Pierre - Ottignies",
        "Hôpital psychiatrique La Petite Maison (Chastre)",
    ]),
    "Bruxelles": sorted([
        "CHIREC - Clinique Sainte Anne - Saint Remi",
        "Centre Hospitalier VALIDA",
        "Centre gériatrique Scheutbos Silva Médical",
        "Clinique Saint Jean - Bruxelles",
        "Clinique Sanatia",
        "Cliniques Universitaires Saint Luc",
        "Cliniques de l'Europe site Saint Michel",
        "Cliniques de l'Europe site Sainte Elisabeth",
        "EPSYLON - La Ramée-FOND'ROY - AREA+",
    ]),
    "Grand-Duché de Luxembourg": sorted([
        "Centre Hospitalier du Luxembourg",
        "Clinique Zitha-Hôpitaux Robert Schumann",
    ]),
    "Hainaut": sorted([
        "CHR Haute-Senne - Soignies",
        "CHU HELORA - Hôpital de La Louvière - Site Jolimont",
        "CHU HELORA - Hôpital de Lobbes",
        "CHU HELORA - Hôpital de Mons",
        "CHU HELORA - Hôpital de Mons - Site Kennedy",
        "CHwapi (Tournai)",
        "Centre Hospitalier de Mouscron",
        "Centre Psychiatrique Saint Bernard (Manage)",
        "Clinique N. Dame de Grâce Gosselies",
        "EPICURA - site du Grand Hornu",
        "GHdC - Centre Psychothérapeutique Charles Albert Frère (Marcinelle)",
        "GHdC - Les Viviers (Gilly)",
        "HUmani - Centre de Santé des Fagnes - Chimay",
    ]),
    "Liège": sorted([
        "CHR HUY",
        "CHR Verviers",
        "CHR de la Citadelle Site Citadelle",
        "Centre Hospitalier Reine Astrid - Malmédy",
        "Groupe Santé CHC MontLégia",
        "Hôpital Sint Nikolaus - Eupen",
    ]),
    "Luxembourg": sorted([
        "VIVALIA - Hôpital d'Arlon",
        "Vivalia - Hôpital de Libramont",
        "Vivalia - Hôpital de Marche",
    ]),
    "Namur": sorted([
        "CHU UCL NAMUR - Foyer Saint François",
        "CHU UCL NAMUR - Site Dinant",
        "CHU UCL NAMUR - Site Mont-Godinne (Yvoir)",
        "CHU UCL NAMUR - Site Sainte Elisabeth - Namur",
        "CNP Saint Martin (Dave)",
        "Centre Hospitalier Sambre & Meuse - Site Meuse",
        "Centre Hospitalier Sambre & Meuse - Site Sambre (Auvelais)",
        "Clinique Saint Luc - Bouge",
        "Hôpital Psychiatrique Le Beau Vallon (Saint-Servais)",
    ]),
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

# Noms des 3 collections Firebase Firestore
COLLECTION_USERS = "users"
COLLECTION_DEMANDES = "demandes"
COLLECTION_MESSAGES = "messages"

# Schémas de colonnes normalisés
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
    "Statut",  # NOUVEAU CHAMP : Statut de l'offre
]

COLONNES_MESSAGES = [
    "Message_ID",
    "Room_ID",
    "Sender_Email",
    "Sender_Name",
    "Timestamp",
    "Texte",
]

# ---------------------------------------------------------------------------
# 3. INITIALISATION DE LA SESSION UTILISATEUR & GESTION ADMIN
# ---------------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state["user"] = None
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False
if "notified_match_rooms" not in st.session_state:
    st.session_state["notified_match_rooms"] = set()


def check_admin_password(candidate_pwd: str) -> bool:
    try:
        secret = str(st.secrets["admin"]["password"]).strip()
        return bool(secret and candidate_pwd.strip() == secret)
    except Exception:
        return False


if hasattr(st, "dialog"):
    @st.dialog("Accès Administrateur")
    def dialog_admin_login():
        st.caption("Espace réservé à la coordination technique et administrative.")
        with st.form("form_dialog_admin_secret"):
            code_secret = st.text_input(
                "Code secret Administrateur",
                type="password",
                placeholder="••••••••",
            )
            btn_unlock = st.form_submit_button(
                "Déverrouiller l'Espace Administrateur",
                type="primary",
                use_container_width=True,
            )
            if btn_unlock:
                if check_admin_password(code_secret):
                    st.session_state["is_admin"] = True
                    st.success("Accès Administrateur accordé !")
                    st.rerun()
                else:
                    st.error("Code secret administrateur incorrect.")


# ---------------------------------------------------------------------------
# 4. INITIALISATION SÉCURISÉE & ACCÈS FIREBASE FIRESTORE (firebase-admin)
# ---------------------------------------------------------------------------
@st.cache_resource
def get_firestore_client():
    if not firebase_admin._apps:
        try:
            if "firebase" not in st.secrets:
                st.error("Configuration Firebase introuvable dans .streamlit/secrets.toml.")
                return None
            fb_creds_dict = dict(st.secrets["firebase"])
            if "private_key" in fb_creds_dict and isinstance(fb_creds_dict["private_key"], str):
                fb_creds_dict["private_key"] = fb_creds_dict["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(fb_creds_dict)
            firebase_admin.initialize_app(cred)
        except Exception as exc:
            st.error(f"Erreur d'initialisation du SDK Firebase Admin : {exc}")
            return None
    return firestore.client()


def normalize_pin_series(series: pd.Series) -> pd.Series:
    s = series.fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    return s.apply(lambda x: x.zfill(4) if (x.isdigit() and len(x) <= 4) else x)


@st.cache_data(ttl=15)
def load_utilisateurs() -> pd.DataFrame:
    db = get_firestore_client()
    if db is None: return pd.DataFrame(columns=COLONNES_UTILISATEURS)
    try:
        docs = db.collection(COLLECTION_USERS).stream()
        data = []
        for doc in docs:
            item = doc.to_dict() or {}
            item["User_ID"] = str(item.get("User_ID") or doc.id).strip()
            data.append(item)
        if not data: return pd.DataFrame(columns=COLONNES_UTILISATEURS)
        df = pd.DataFrame(data)
        for col in COLONNES_UTILISATEURS:
            if col not in df.columns: df[col] = ""
        df["PIN"] = normalize_pin_series(df["PIN"])
        for col in ["User_ID", "Nom", "Prenom", "Email", "Date_Inscription"]:
            df[col] = df[col].fillna("").astype(str).str.strip()
        return df[COLONNES_UTILISATEURS]
    except Exception as exc:
        st.error(f"Erreur de lecture '{COLLECTION_USERS}' : {exc}")
        return pd.DataFrame(columns=COLONNES_UTILISATEURS)


def create_user_firestore(user_dict: dict) -> bool:
    db = get_firestore_client()
    if db is None: return False
    try:
        db.collection(COLLECTION_USERS).document(user_dict["User_ID"]).set(user_dict)
        st.cache_data.clear()
        return True
    except Exception as exc:
        st.error(f"Erreur création compte : {exc}")
        return False


def delete_user_firestore(user_id: str, email: str) -> bool:
    """Supprime l'utilisateur ET toutes ses offres en cascade."""
    db = get_firestore_client()
    if db is None: return False
    try:
        # 1. Supprimer l'utilisateur
        db.collection(COLLECTION_USERS).document(user_id).delete()
        # 2. Supprimer en cascade ses annonces dans 'demandes'
        demandes_q = db.collection(COLLECTION_DEMANDES).where("Email", "==", email.strip().lower()).stream()
        for doc in demandes_q:
            doc.reference.delete()
        st.cache_data.clear()
        return True
    except Exception as exc:
        st.error(f"Erreur lors de la suppression de l'utilisateur : {exc}")
        return False


def update_user_pin_firestore(user_id: str, email: str, new_pin: str) -> bool:
    db = get_firestore_client()
    if db is None: return False
    try:
        pin_clean = str(new_pin).strip().zfill(4)
        db.collection(COLLECTION_USERS).document(user_id).update({"PIN": pin_clean})
        clean_email = email.strip().lower()
        demandes_query = db.collection(COLLECTION_DEMANDES).where("Email", "==", clean_email).stream()
        for doc in demandes_query:
            doc.reference.update({"PIN": pin_clean})
        st.cache_data.clear()
        return True
    except Exception as exc:
        st.error(f"Erreur de mise à jour PIN : {exc}")
        return False


@st.cache_data(ttl=15)
def load_demandes() -> pd.DataFrame:
    db = get_firestore_client()
    if db is None: return pd.DataFrame(columns=COLONNES_DEMANDES)
    try:
        docs = db.collection(COLLECTION_DEMANDES).stream()
        data = []
        for doc in docs:
            item = doc.to_dict() or {}
            item["Demande_ID"] = str(item.get("Demande_ID") or doc.id).strip()
            # Rétrocompatibilité du statut
            if "Statut" not in item:
                item["Statut"] = "Disponible"
            data.append(item)
        if not data: return pd.DataFrame(columns=COLONNES_DEMANDES)
        df = pd.DataFrame(data)
        for col in COLONNES_DEMANDES:
            if col not in df.columns: df[col] = "Disponible" if col == "Statut" else ""
        df["PIN"] = normalize_pin_series(df["PIN"])
        for col in ["Demande_ID", "Timestamp", "Nom", "Email", "Periode", "Specialite", "Hopital_Actuel", "Hopitaux_Souhaites", "Statut"]:
            df[col] = df[col].fillna("").astype(str).str.strip()
        return df[COLONNES_DEMANDES]
    except Exception as exc:
        st.error(f"Erreur de lecture '{COLLECTION_DEMANDES}' : {exc}")
        return pd.DataFrame(columns=COLONNES_DEMANDES)


def add_demande_firestore(demande_dict: dict) -> bool:
    db = get_firestore_client()
    if db is None: return False
    try:
        demande_id = demande_dict.get("Demande_ID") or f"DEM_{uuid.uuid4().hex[:10].upper()}"
        demande_dict["Demande_ID"] = demande_id
        if "Statut" not in demande_dict:
            demande_dict["Statut"] = "Disponible"
        db.collection(COLLECTION_DEMANDES).document(demande_id).set(demande_dict)
        st.cache_data.clear()
        return True
    except Exception as exc:
        st.error(f"Erreur de dépôt demande : {exc}")
        return False


def update_demande_firestore(demande_id: str, fields: dict) -> bool:
    db = get_firestore_client()
    if db is None: return False
    try:
        db.collection(COLLECTION_DEMANDES).document(demande_id).update(fields)
        st.cache_data.clear()
        return True
    except Exception as exc:
        st.error(f"Erreur de modification demande : {exc}")
        return False


def delete_demande_firestore(demande_id: str) -> bool:
    db = get_firestore_client()
    if db is None: return False
    try:
        db.collection(COLLECTION_DEMANDES).document(demande_id).delete()
        st.cache_data.clear()
        return True
    except Exception as exc:
        st.error(f"Erreur de suppression demande : {exc}")
        return False


@st.cache_data(ttl=15)
def load_messages() -> pd.DataFrame:
    db = get_firestore_client()
    if db is None: return pd.DataFrame(columns=COLONNES_MESSAGES)
    try:
        docs = db.collection(COLLECTION_MESSAGES).stream()
        data = []
        for doc in docs:
            item = doc.to_dict() or {}
            item["Message_ID"] = str(item.get("Message_ID") or doc.id).strip()
            data.append(item)
        if not data: return pd.DataFrame(columns=COLONNES_MESSAGES)
        df = pd.DataFrame(data)
        for col in COLONNES_MESSAGES:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].fillna("").astype(str).str.strip()
        if not df.empty and "Timestamp" in df.columns:
            df = df.sort_values(by="Timestamp", ascending=True).reset_index(drop=True)
        return df[COLONNES_MESSAGES]
    except Exception as exc:
        st.error(f"Erreur de lecture '{COLLECTION_MESSAGES}' : {exc}")
        return pd.DataFrame(columns=COLONNES_MESSAGES)


def append_message_firestore(room_id: str, sender_email: str, sender_name: str, texte: str) -> bool:
    db = get_firestore_client()
    if db is None: return False
    try:
        msg_id = f"MSG_{uuid.uuid4().hex[:10].upper()}"
        db.collection(COLLECTION_MESSAGES).document(msg_id).set({
            "Message_ID": msg_id,
            "Room_ID": room_id.strip(),
            "Sender_Email": sender_email.strip().lower(),
            "Sender_Name": sender_name.strip(),
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Texte": texte.strip(),
        })
        st.cache_data.clear()
        return True
    except Exception as exc:
        st.error(f"Erreur d'envoi message : {exc}")
        return False


def serialize_hospitals(hospitals: list[str]) -> str:
    return "; ".join([h.strip() for h in hospitals if h.strip()])


def parse_hospitals(raw_str: str) -> list[str]:
    if not raw_str or pd.isna(raw_str): return []
    return [h.strip() for h in str(raw_str).split(";") if h.strip()]


def build_room_id(periode: str, specialite: str, emails: list[str]) -> str:
    sorted_emails = sorted([e.strip().lower() for e in emails])
    return f"ROOM_{periode}_{specialite}_{'_'.join(sorted_emails)}"


# ---------------------------------------------------------------------------
# 5. SYSTÈME D'ALERTES PAR EMAIL (OPTION A)
# ---------------------------------------------------------------------------
def resolve_student_prenom(email: str, fallback_nom: str, df_users: pd.DataFrame) -> str:
    clean_email = (email or "").strip().lower()
    if df_users is not None and not df_users.empty and clean_email:
        rows = df_users[df_users["Email"].astype(str).str.strip().str.lower() == clean_email]
        if not rows.empty:
            prenom_val = str(rows.iloc[0].get("Prenom", "")).strip()
            if prenom_val: return prenom_val
    if fallback_nom and str(fallback_nom).strip():
        return str(fallback_nom).strip().split()[0]
    return "Étudiant(e)"


def send_match_notification_emails(participants: list[dict], periode: str, specialite: str, room_id: str, df_users: pd.DataFrame) -> int:
    if room_id in st.session_state["notified_match_rooms"]: return 0
    try:
        smtp_cfg = st.secrets["smtp"]
        smtp_server, smtp_port, smtp_user, smtp_password = str(smtp_cfg["server"]).strip(), int(smtp_cfg["port"]), str(smtp_cfg["username"]).strip(), str(smtp_cfg["password"])
    except Exception:
        return 0

    sujet = "[PermutStage] Un échange de stage est disponible pour vous !"
    sent_count = 0
    seen_dest = set()
    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.ehlo()
            if smtp_port in (587, 25): server.starttls(); server.ehlo()
            server.login(smtp_user, smtp_password)

            for participant in participants:
                dest_email = str(participant.get("Email", "")).strip().lower()
                if not dest_email or dest_email in seen_dest: continue
                seen_dest.add(dest_email)
                prenom = resolve_student_prenom(dest_email, participant.get("Nom", ""), df_users)
                corps = (
                    f"Bonjour {prenom},\n\n"
                    f"Une opportunité d'échange direct vient de se former pour votre stage de {specialite} ({periode}) !\n\n"
                    f"Un salon de discussion privé et sécurisé a été ouvert sur l'application. Connectez-vous dès maintenant :\n"
                    f"https://stages-medecine-ucl.streamlit.app/\n\n"
                    f"À très vite,\nL'équipe PermutStage"
                )
                try:
                    msg = MIMEText(corps, "plain", "utf-8")
                    msg["Subject"], msg["From"], msg["To"] = sujet, smtp_user, dest_email
                    server.send_message(msg)
                    sent_count += 1
                except Exception:
                    continue
        st.session_state["notified_match_rooms"].add(room_id)
        return sent_count
    except Exception:
        return sent_count


def trigger_new_match_emails(anciens_rooms: set[str], df_demandes_maj: pd.DataFrame, df_utilisateurs: pd.DataFrame, df_messages: pd.DataFrame) -> None:
    try:
        rooms_actifs = set(anciens_rooms) | set(st.session_state.get("notified_match_rooms", set()))
        if df_messages is not None and not df_messages.empty and "Room_ID" in df_messages.columns:
            rooms_actifs |= set(df_messages["Room_ID"].dropna().astype(str).str.strip().unique())

        nouveaux_bi = compute_bilateral_matches(df_demandes_maj)
        nouveaux_tri = compute_triangular_matches(df_demandes_maj)

        for m in nouveaux_bi:
            if m["room_id"] not in rooms_actifs:
                send_match_notification_emails(m["participants"], m["periode"], m["specialite"], m["room_id"], df_utilisateurs)
        for t in nouveaux_tri:
            if t["room_id"] not in rooms_actifs:
                send_match_notification_emails(t["participants"], t["periode"], t["specialite"], t["room_id"], df_utilisateurs)
    except Exception:
        pass


def send_pin_recovery_email(dest_email: str, prenom: str, pin: str) -> bool:
    try:
        smtp_cfg = st.secrets["smtp"]
        smtp_server, smtp_port, smtp_user, smtp_password = str(smtp_cfg["server"]).strip(), int(smtp_cfg["port"]), str(smtp_cfg["username"]).strip(), str(smtp_cfg["password"])
    except Exception:
        raise RuntimeError("Configuration SMTP introuvable.")

    sujet = "[PermutStage] Récupération de votre code PIN"
    corps = (
        f"Bonjour {prenom},\n\nVous avez demandé la récupération de votre code PIN pour accéder à PermutStage.\n\n"
        f"Votre code PIN de connexion est : {str(pin).strip().zfill(4)}\n\n"
        f"L'équipe PermutStage"
    )
    with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
        server.ehlo()
        if smtp_port in (587, 25): server.starttls(); server.ehlo()
        server.login(smtp_user, smtp_password)
        msg = MIMEText(corps, "plain", "utf-8")
        msg["Subject"], msg["From"], msg["To"] = sujet, smtp_user, dest_email.strip().lower()
        server.send_message(msg)
    return True


# ---------------------------------------------------------------------------
# 6. MOTEUR DE MATCHING & FILTRE DE CONFIDENTIALITÉ STRICTE
# ---------------------------------------------------------------------------
def compute_bilateral_matches(df: pd.DataFrame) -> list[dict]:
    matches = []
    if df.empty: return matches
    # RÈGLE DU STATUT : On ne matche que les annonces qui sont 'Disponible'
    df_dispo = df[df["Statut"] == "Disponible"]
    records = df_dispo.to_dict("records")
    n = len(records)

    for i in range(n):
        for j in range(i + 1, n):
            a, b = records[i], records[j]
            if a["Periode"] != b["Periode"] or a["Specialite"] != b["Specialite"] or a["Hopital_Actuel"] == b["Hopital_Actuel"]:
                continue
            souhaites_a = set(parse_hospitals(a["Hopitaux_Souhaites"]))
            souhaites_b = set(parse_hospitals(b["Hopitaux_Souhaites"]))
            if a["Hopital_Actuel"] in souhaites_b and b["Hopital_Actuel"] in souhaites_a:
                room_id = build_room_id(a["Periode"], a["Specialite"], [a["Email"], b["Email"]])
                matches.append({"room_id": room_id, "periode": a["Periode"], "specialite": a["Specialite"], "participants": [a, b], "emails": [a["Email"].strip().lower(), b["Email"].strip().lower()], "a": a, "b": b})
    return matches


def compute_triangular_matches(df: pd.DataFrame) -> list[dict]:
    matches = []
    if df.empty: return matches
    # RÈGLE DU STATUT : On ne matche que les annonces qui sont 'Disponible'
    df_dispo = df[df["Statut"] == "Disponible"]
    seen_cycles = set()
    records = df_dispo.to_dict("records")
    n = len(records)
    souhaites_map = {idx: set(parse_hospitals(rec["Hopitaux_Souhaites"])) for idx, rec in enumerate(records)}

    for i in range(n):
        for j in range(n):
            if i == j: continue
            a, b = records[i], records[j]
            if a["Periode"] != b["Periode"] or a["Specialite"] != b["Specialite"] or a["Hopital_Actuel"] == b["Hopital_Actuel"] or a["Hopital_Actuel"] not in souhaites_map[j]:
                continue
            for k in range(n):
                if k in (i, j): continue
                c = records[k]
                if c["Periode"] != a["Periode"] or c["Specialite"] != a["Specialite"] or c["Hopital_Actuel"] in (a["Hopital_Actuel"], b["Hopital_Actuel"]):
                    continue
                if b["Hopital_Actuel"] in souhaites_map[k] and c["Hopital_Actuel"] in souhaites_map[i]:
                    id_a, id_b, id_c = f"{a['Email'].lower()}_{a['Periode']}", f"{b['Email'].lower()}_{b['Periode']}", f"{c['Email'].lower()}_{c['Periode']}"
                    canonical = sorted([(id_a, id_b, id_c), (id_b, id_c, id_a), (id_c, id_a, id_b)])[0]
                    if canonical not in seen_cycles:
                        seen_cycles.add(canonical)
                        room_id = build_room_id(a["Periode"], a["Specialite"], [a["Email"], b["Email"], c["Email"]])
                        matches.append({"room_id": room_id, "periode": a["Periode"], "specialite": a["Specialite"], "participants": [a, b, c], "emails": [a["Email"].strip().lower(), b["Email"].strip().lower(), c["Email"].strip().lower()], "a": a, "b": b, "c": c})
    return matches


def filter_private_matches_for_user(user_email: str | None, all_bilateral: list[dict], all_triangular: list[dict]) -> tuple[list[dict], list[dict]]:
    if not user_email: return [], []
    clean_email = user_email.strip().lower()
    return [m for m in all_bilateral if clean_email in m["emails"]], [t for t in all_triangular if clean_email in t["emails"]]


def build_user_notifications(user_email: str | None, my_bi: list[dict], my_tri: list[dict], df_msgs: pd.DataFrame) -> list[dict]:
    if not user_email: return []
    clean_email = user_email.strip().lower()
    notifs, my_rooms = [], set()
    for m in my_bi:
        my_rooms.add(m["room_id"])
        notifs.append({"titre": f"Nouvelle proposition trouvée en {m['specialite']} !", "detail": "Match bilatéral disponible dans votre salon privé."})
    for t in my_tri:
        my_rooms.add(t["room_id"])
        notifs.append({"titre": f"Nouvelle proposition trouvée en {t['specialite']} !", "detail": "Salon d'échange triangulaire ouvert pour vous."})
    if not df_msgs.empty and my_rooms:
        msgs_for_me = df_msgs[(df_msgs["Room_ID"].isin(my_rooms)) & (df_msgs["Sender_Email"].str.lower() != clean_email)]
        for _, msg in msgs_for_me.iterrows():
            notifs.append({"titre": f"Nouveau message de {msg['Sender_Name']}", "detail": f"« {msg['Texte']} »"})
    return notifs


def render_private_chat_room(room_id: str, current_user: dict, df_msgs: pd.DataFrame, label_expander: str):
    messages_salon = df_msgs[df_msgs["Room_ID"] == room_id] if not df_msgs.empty else pd.DataFrame()
    with st.expander(f"💬 {label_expander} ({len(messages_salon)} message(s))", expanded=True):
        if messages_salon.empty: st.caption("Aucun message. Envoyez le premier message !")
        else:
            for _, msg in messages_salon.iterrows():
                is_me = msg["Sender_Email"].strip().lower() == current_user["Email"].strip().lower()
                with st.chat_message("user" if is_me else "assistant"):
                    st.markdown(f"**{msg['Sender_Name']}** · *{msg['Timestamp']}*\n\n{msg['Texte']}")
        nouveau_texte = st.chat_input("Écrire un message...", key=f"chat_input_{room_id}")
        if nouveau_texte and nouveau_texte.strip():
            if append_message_firestore(room_id, current_user["Email"].strip().lower(), f"{current_user['Prenom']} {current_user['Nom']}".strip(), nouveau_texte):
                st.rerun()


# ---------------------------------------------------------------------------
# 8. CHARGEMENT DES DONNÉES & PERSISTANCE DE SESSION
# ---------------------------------------------------------------------------
def get_auth_query_param() -> str | None:
    try:
        if hasattr(st, "query_params"): val = st.query_params.get("auth", None); return str(val).strip() if val else None
        elif hasattr(st, "experimental_get_query_params"):
            params = st.experimental_get_query_params()
            if "auth" in params and params["auth"]: return str(params["auth"][0]).strip()
    except Exception: pass
    return None

def set_auth_query_param(token: str):
    try:
        if hasattr(st, "query_params"): st.query_params["auth"] = token
        elif hasattr(st, "experimental_set_query_params"): st.experimental_set_query_params(auth=token)
    except Exception: pass

def clear_query_params():
    try:
        if hasattr(st, "query_params"): st.query_params.clear()
        elif hasattr(st, "experimental_set_query_params"): st.experimental_set_query_params()
    except Exception: pass

df_utilisateurs = load_utilisateurs()
df_demandes = load_demandes()
df_messages = load_messages()

auth_token = get_auth_query_param()
if auth_token and st.session_state.get("user") is None:
    target_clean = auth_token.strip().lower()
    match_users = pd.DataFrame()
    if not df_utilisateurs.empty:
        match_users = df_utilisateurs[(df_utilisateurs["Email"].astype(str).str.strip().str.lower() == target_clean) | (df_utilisateurs["User_ID"].astype(str).str.strip().str.lower() == target_clean)]
    if match_users.empty:
        try:
            db_fs = get_firestore_client()
            if db_fs:
                docs_by_email = db_fs.collection(COLLECTION_USERS).where("Email", "==", target_clean).limit(1).stream()
                for doc_u in docs_by_email:
                    u_data = doc_u.to_dict() or {}
                    u_data["User_ID"] = str(u_data.get("User_ID") or doc_u.id).strip()
                    match_users = pd.DataFrame([u_data])
        except Exception: pass

    if not match_users.empty:
        u_saved = match_users.iloc[0]
        pin_val = str(u_saved["PIN"]).strip()
        st.session_state["user"] = {
            "User_ID": str(u_saved["User_ID"]).strip(), "Nom": str(u_saved["Nom"]).strip(), "Prenom": str(u_saved["Prenom"]).strip(),
            "Email": str(u_saved["Email"]).strip().lower(), "PIN": pin_val.zfill(4) if pin_val.isdigit() else pin_val,
        }
        set_auth_query_param(str(u_saved["Email"]).strip().lower())
    else:
        clear_query_params()

all_matchs_binomes = compute_bilateral_matches(df_demandes)
all_matchs_triangulaires = compute_triangular_matches(df_demandes)

current_user = st.session_state.get("user")
current_user_email = current_user["Email"].strip().lower() if current_user else None

mes_matchs_binomes, mes_matchs_triangulaires = filter_private_matches_for_user(current_user_email, all_matchs_binomes, all_matchs_triangulaires)
mes_notifications = build_user_notifications(current_user_email, mes_matchs_binomes, mes_matchs_triangulaires, df_messages)

# ---------------------------------------------------------------------------
# 9. VOLET LATÉRAL (AUTHENTIFICATION & PROFIL ÉTUDIANT)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.subheader("Mon Compte Étudiant")

    if current_user is not None:
        st.success(f"Connecté : **{current_user['Prenom']} {current_user['Nom']}**\n\n`{current_user['Email']}`")
        with st.expander("🔒 Modifier mon code PIN", expanded=False):
            with st.form("sidebar_change_pin_form"):
                old_pin_val = st.text_input("Ancien code PIN", type="password", max_chars=4)
                new_pin_val = st.text_input("Nouveau code PIN (4 chiffres)", type="password", max_chars=4)
                confirm_pin_val = st.text_input("Confirmer le nouveau PIN", type="password", max_chars=4)
                if st.form_submit_button("Modifier mon PIN", type="primary", use_container_width=True):
                    if old_pin_val.strip() != str(current_user.get("PIN", "")).strip().zfill(4): st.error("Ancien PIN incorrect.")
                    elif not re.match(r"^\d{4}$", new_pin_val.strip()): st.error("Le nouveau PIN doit faire 4 chiffres.")
                    elif new_pin_val.strip() != confirm_pin_val.strip(): st.error("Confirmation non identique.")
                    else:
                        if update_user_pin_firestore(current_user["User_ID"], current_user_email, new_pin_val.strip()):
                            st.session_state["user"]["PIN"] = new_pin_val.strip()
                            st.success("PIN modifié !")
                            st.rerun()

        if st.button("Se déconnecter", use_container_width=True):
            clear_query_params(); st.session_state.clear(); st.session_state["user"] = None; st.session_state["is_admin"] = False; st.rerun()

    else:
        with st.form("login_form"):
            login_email = st.text_input("Email institutionnel", placeholder="prenom.nom@student.uclouvain.be")
            login_pin = st.text_input("Code PIN (4 chiffres)", type="password", max_chars=4)
            if st.form_submit_button("Se connecter", type="primary", use_container_width=True):
                em_clean, pin_clean = login_email.strip().lower(), login_pin.strip()
                if not em_clean or not pin_clean: st.error("Email ou PIN incorrect.")
                else:
                    user_rows = df_utilisateurs[df_utilisateurs["Email"].astype(str).str.strip().str.lower() == em_clean]
                    if user_rows.empty:
                        try:
                            db_fs = get_firestore_client()
                            if db_fs:
                                for doc_u in db_fs.collection(COLLECTION_USERS).where("Email", "==", em_clean).limit(1).stream():
                                    u_data = doc_u.to_dict() or {}; u_data["User_ID"] = str(u_data.get("User_ID") or doc_u.id).strip(); user_rows = pd.DataFrame([u_data])
                        except Exception: pass

                    if user_rows.empty: st.error("Email ou PIN incorrect.")
                    else:
                        u_row = user_rows.iloc[0]
                        pin_bdd = str(u_row["PIN"]).strip()
                        if pin_bdd.isdigit() and len(pin_bdd) <= 4: pin_bdd = pin_bdd.zfill(4)
                        pin_saisi_norm = pin_clean.zfill(4) if (pin_clean.isdigit() and len(pin_clean) <= 4) else pin_clean

                        if str(pin_saisi_norm) == str(pin_bdd):
                            user_session = { "User_ID": str(u_row["User_ID"]).strip(), "Nom": str(u_row["Nom"]).strip(), "Prenom": str(u_row["Prenom"]).strip(), "Email": str(u_row["Email"]).strip().lower(), "PIN": str(pin_bdd) }
                            st.session_state["user"] = user_session; st.query_params["auth"] = user_session["Email"]
                            st.success(f"Bienvenue {user_session['Prenom']}."); st.rerun()
                        else: st.error("Email ou PIN incorrect.")

        with st.expander("📝 Pas encore de compte ? Créer un profil", expanded=False):
            with st.form("sidebar_register_form"):
                reg_prenom = st.text_input("Prénom *")
                reg_nom = st.text_input("Nom *")
                reg_email = st.text_input("Email institutionnel *")
                reg_pin = st.text_input("Choisir PIN à 4 chiffres *", type="password", max_chars=4)
                if st.form_submit_button("Créer mon compte", type="primary", use_container_width=True):
                    errs = []
                    p_clean, n_clean, e_clean, pin_c = reg_prenom.strip(), reg_nom.strip(), reg_email.strip().lower(), reg_pin.strip()
                    if len(p_clean) < 2 or len(n_clean) < 2: errs.append("Nom/Prénom requis.")
                    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", e_clean): errs.append("Email invalide.")
                    if not re.match(r"^\d{4}$", pin_c): errs.append("PIN doit faire 4 chiffres.")
                    if not df_utilisateurs.empty and not df_utilisateurs[df_utilisateurs["Email"].astype(str).str.strip().str.lower() == e_clean].empty: errs.append("Email déjà utilisé.")
                    if errs:
                        for er in errs: st.error(er)
                    else:
                        new_u = { "User_ID": f"USR_{uuid.uuid4().hex[:8].upper()}", "Nom": n_clean, "Prenom": p_clean, "Email": e_clean, "PIN": pin_c.zfill(4), "Date_Inscription": datetime.now().strftime("%Y-%m-%d %H:%M:%S") }
                        if create_user_firestore(new_u):
                            st.session_state["user"] = new_u; st.query_params["auth"] = new_u["Email"]; st.success("Compte créé !"); st.rerun()

        with st.expander("🔑 Code PIN oublié ?", expanded=False):
            with st.form("sidebar_forgot_pin_form"):
                f_email = st.text_input("Email étudiant")
                if st.form_submit_button("M'envoyer mon code PIN", use_container_width=True):
                    f_email_c = f_email.strip().lower()
                    m_users = df_utilisateurs[df_utilisateurs["Email"].astype(str).str.strip().str.lower() == f_email_c]
                    if m_users.empty: st.warning("Compte introuvable.")
                    else:
                        u_t = m_users.iloc[0]
                        try:
                            send_pin_recovery_email(f_email_c, str(u_t.get("Prenom", "")).strip() or "étudiant", str(u_t["PIN"]).strip().zfill(4))
                            st.success("PIN envoyé !")
                        except Exception as err: st.error(f"Erreur envoi : {err}")

    st.divider()
    st.markdown("""<div style="text-align: center; color: #94a3b8; font-size: 0.8rem; padding: 0.5rem 0;">Développé par Imrane Machbaête</div>""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 10. EN-TÊTE ET ONGLET DE NOTIFICATIONS
# ---------------------------------------------------------------------------
# Notifications déplacées au-dessus des onglets (aligné à droite)
_, col_notif = st.columns([3, 1])
with col_notif:
    nb_notifs = len(mes_notifications)
    with st.expander(f"🔔 Notifications ({nb_notifs})", expanded=False):
        if current_user is None: st.caption("Connectez-vous pour voir vos alertes.")
        elif nb_notifs == 0: st.caption("Aucune notification.")
        else:
            for n_item in mes_notifications:
                st.markdown(f"""<div class="notif-card"><div style="font-size: 0.82rem; font-weight: 700; color: #1e3a8a;">{n_item['titre']}</div><div style="font-size: 0.78rem; color: #334155; margin-top: 0.2rem;">{n_item['detail']}</div></div>""", unsafe_allow_html=True)

# Espace Administrateur débloqué si authentifié en session
if st.session_state.get("is_admin", False):
    with st.expander("🛠️ Espace Administrateur (Supervision & Statistiques)", expanded=True):
        c_adm1, c_adm2 = st.columns([4, 1])
        with c_adm1: st.markdown("### 🛠️ Espace Administrateur Débloqué")
        with c_adm2:
            if st.button("🔒 Verrouiller", use_container_width=True): st.session_state["is_admin"] = False; st.rerun()

        st.markdown("#### 📊 Statistiques")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Comptes étudiants", len(df_utilisateurs))
        kpi2.metric("Offres actives déposées", len(df_demandes))
        kpi3.metric("Matchs directs binômes", len(all_matchs_binomes))
        kpi4.metric("Boucles triangulaires", len(all_matchs_triangulaires))

        st.markdown("#### ⚙️ Gestion des collections & Suppressions")
        adm_t1, adm_t2, adm_t3 = st.tabs(["Collection demandes (Offres)", "Collection users (Utilisateurs)", "Collection messages"])
        
        with adm_t1:
            if not df_demandes.empty:
                opt_del_dem = [f"{r['Demande_ID']} | {r['Periode']} - {r['Specialite']} | {r['Nom']} ({r['Email']}) — {r['Hopital_Actuel']}" for _, r in df_demandes.iterrows()]
                c_del_dem = st.selectbox("Sélectionner l'annonce à supprimer", opt_del_dem)
                if st.button("Supprimer cette offre (Admin)", type="primary"):
                    id_drop = c_del_dem.split(" | ")[0].strip()
                    if delete_demande_firestore(id_drop): st.success(f"Annonce {id_drop} supprimée."); st.rerun()
            st.dataframe(df_demandes, use_container_width=True, hide_index=True)

        with adm_t2:
            if not df_utilisateurs.empty:
                st.caption("Suppression d'un utilisateur ET suppression en cascade de toutes ses offres.")
                opt_del_user = [f"{r['User_ID']} | {r['Prenom']} {r['Nom']} ({r['Email']})" for _, r in df_utilisateurs.iterrows()]
                c_del_user = st.selectbox("Sélectionner l'utilisateur à supprimer", opt_del_user)
                if st.button("Supprimer cet utilisateur (Admin)", type="primary"):
                    uid_drop = c_del_user.split(" | ")[0].strip()
                    email_drop = c_del_user.split("(")[-1].replace(")", "").strip()
                    if delete_user_firestore(uid_drop, email_drop):
                        st.success(f"Utilisateur {uid_drop} et ses offres ont été supprimés."); st.rerun()
            st.dataframe(df_utilisateurs, use_container_width=True, hide_index=True)

        with adm_t3:
            st.dataframe(df_messages, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# 11. ONGLETS PRINCIPAUX DE L'APPLICATION
# ---------------------------------------------------------------------------
nb_mes_matchs = len(mes_matchs_binomes) + len(mes_matchs_triangulaires)

tab0, tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Accueil & Guide",
        "1. Déposer une demande",
        f"2. Matchs disponibles & Salons privés ({nb_mes_matchs})",
        f"3. Consulter toutes les offres ({len(df_demandes)})",
        "4. Gérer mon offre",
    ]
)

# ===========================================================================
# ONGLET 0 : ACCUEIL CHALEUREUX, GUIDE & RÈGLES
# ===========================================================================
with tab0:
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-badge">
                ✨ PROMOTION MÉDECINE 2028 · MASTER 2
            </div>
            <h1>Trouvez votre binôme de stage idéal en quelques clics</h1>
            <p>
                Bienvenue sur <strong>PermutStage</strong>, la plateforme pensée pour fluidifier, simplifier et centraliser
                les échanges de lieux de stages hospitaliers entre camarades de promotion. Vos souhaits sont analysés
                en temps réel par notre algorithme de permutation, dans le respect le plus strict de votre confidentialité.
            </p>
            <div class="hero-alpha-box">
                <strong>🤝 Statut du projet : Version Alpha / Concept Test</strong><br/>
                Cette plateforme est une initiative bénévole conçue <em>par et pour les étudiants</em>. Merci pour votre
                bienveillance et vos retours constructifs pour faire évoluer l'outil au service de toute la promotion !
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("🧭 Comment ça marche ? (Le parcours en 4 étapes simples)")
    col_e1, col_e2, col_e3, col_e4 = st.columns(4)
    with col_e1: st.markdown("""<div class="step-card"><div style="width: 32px; height: 32px; border-radius: 8px; background-color: #dbeafe; color: #1e40af; font-weight: 800; display: flex; align-items: center; justify-content: center; margin-bottom: 0.5rem;">1</div><strong>Créer son profil (30s)</strong><p>Renseignez nom, email et <strong>code PIN à 4 chiffres</strong>.</p></div>""", unsafe_allow_html=True)
    with col_e2: st.markdown("""<div class="step-card"><div style="width: 32px; height: 32px; border-radius: 8px; background-color: #e0e7ff; color: #3730a3; font-weight: 800; display: flex; align-items: center; justify-content: center; margin-bottom: 0.5rem;">2</div><strong>Déposer son offre</strong><p>Indiquez votre stage actuel et sélectionnez vos <strong>hôpitaux souhaités</strong>.</p></div>""", unsafe_allow_html=True)
    with col_e3: st.markdown("""<div class="step-card"><div style="width: 32px; height: 32px; border-radius: 8px; background-color: #f3e8ff; color: #6b21a8; font-weight: 800; display: flex; align-items: center; justify-content: center; margin-bottom: 0.5rem;">3</div><strong>Calcul des matchs</strong><p>L'algorithme détecte les <strong>échanges directs (A↔B)</strong> ou <strong>triangulaires (A→B→C→A)</strong>.</p></div>""", unsafe_allow_html=True)
    with col_e4: st.markdown("""<div class="step-card"><div style="width: 32px; height: 32px; border-radius: 8px; background-color: #dcfce7; color: #166534; font-weight: 800; display: flex; align-items: center; justify-content: center; margin-bottom: 0.5rem;">4</div><strong>Échanger en privé</strong><p>Une notification s'active pour ouvrir votre salon privé sécurisé.</p></div>""", unsafe_allow_html=True)

    st.write("")
    c_btn1, c_btn2, _ = st.columns([1.5, 1.5, 3])
    with c_btn1:
        if st.button("🚀 Déposer une demande", type="primary", use_container_width=True):
            st.info("Passez à l'onglet '1. Déposer une demande' juste au-dessus !")
    with c_btn2:
        if st.button("✉️ Mes correspondances", use_container_width=True):
            st.info("Passez à l'onglet '2. Matchs disponibles' juste au-dessus !")

# ===========================================================================
# ONGLET 1 : DÉPOSER UNE DEMANDE (SÉLECTION DYNAMIQUE HÔPITAL ACTUEL)
# ===========================================================================
with tab1:
    st.subheader("Déposer une nouvelle demande de permutation")

    if current_user is None:
        st.warning("🔒 Veuillez vous connecter ou créer un compte étudiant dans le menu latéral gauche pour déposer une demande.")
    else:
        nom_complet_verrouille = f"{current_user['Prenom']} {current_user['Nom']}".strip()
        email_verrouille = current_user["Email"].strip().lower()

        with st.form("form_depot_demande", clear_on_submit=False):
            st.markdown("#### 1. Votre affectation actuelle")
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("Nom & Prénom", value=nom_complet_verrouille, disabled=True)
                st.text_input("Email", value=email_verrouille, disabled=True)
            with col2:
                periode = st.selectbox("Période de stage *", options=PERIODES)
                specialite = st.selectbox("Spécialité *", options=SPECIALITES)
            
            reg1, reg2 = st.columns(2)
            with reg1:
                # Région pour filtrer l'hôpital actuel
                region_actuelle_filtre = st.selectbox("Région de l'hôpital actuel *", options=REGIONS)
            with reg2:
                # La liste des hôpitaux se met à jour selon la région choisie
                options_hopital_actuel = HOPITAUX_PAR_REGION[region_actuelle_filtre]
                hopital_actuel = st.selectbox("Hôpital actuel *", options=options_hopital_actuel)

            st.markdown("#### 2. Vos souhaits d'échange (Où souhaitez-vous aller ?)")
            st.caption("Vous pouvez sélectionner un ou plusieurs hôpitaux cibles à travers toutes les régions.")
            
            defaut_souhaites = [h for h in HOPITAUX_PAR_REGION[region_actuelle_filtre] if h != hopital_actuel]

            hopitaux_souhaites = st.multiselect(
                "Hôpitaux souhaités *",
                options=TOUS_LES_HOPITAUX,
                default=defaut_souhaites,
                format_func=lambda h: f"[{HOPITAL_VERS_REGION.get(h, '')}] {h}",
            )

            submitted = st.form_submit_button("🚀 Publier mon offre de permutation", type="primary", use_container_width=True)

            if submitted:
                erreurs = []
                if not hopitaux_souhaites: erreurs.append("Sélectionnez au moins un hôpital souhaité.")
                elif hopital_actuel in hopitaux_souhaites: erreurs.append("L'hôpital actuel ne peut pas être un hôpital souhaité.")
                if not df_demandes.empty:
                    doublon = df_demandes[(df_demandes["Email"].str.lower() == email_verrouille) & (df_demandes["Periode"] == periode)]
                    if not doublon.empty: erreurs.append(f"Vous avez déjà une demande active sur {periode}.")
                if erreurs:
                    for err in erreurs: st.error(err)
                else:
                    nouvelle_demande_dict = {
                        "Demande_ID": f"DEM_{uuid.uuid4().hex[:10].upper()}",
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Nom": nom_complet_verrouille, "Email": email_verrouille, "PIN": str(current_user.get("PIN", "")).strip(),
                        "Periode": periode, "Specialite": specialite, "Hopital_Actuel": hopital_actuel,
                        "Hopitaux_Souhaites": serialize_hospitals(hopitaux_souhaites),
                        "Statut": "Disponible" # Toujours "Disponible" lors du dépôt
                    }
                    if add_demande_firestore(nouvelle_demande_dict):
                        st.success(f"Votre demande pour {periode} a été publiée avec succès !")
                        st.rerun()

# ===========================================================================
# ONGLET 2 : MATCHS DISPONIBLES & SALONS PRIVÉS
# ===========================================================================
with tab2:
    st.subheader("Mes correspondances privées & Salons de discussion")

    if current_user is None:
        st.info("🔒 Connectez-vous à votre compte étudiant pour visualiser vos propositions d'échange et vos salons de discussion.")
    else:
        st.caption("Seuls les binômes et cycles à 3 dont vous faites partie intégrante apparaissent ici.")
        col_bi, col_tri = st.columns(2)

        with col_bi:
            st.markdown(f"### Mes Échanges Bilatéraux — Binômes ({len(mes_matchs_binomes)})")
            if not mes_matchs_binomes: st.info("Aucun match bilatéral ne vous concerne actuellement.")
            else:
                for m in mes_matchs_binomes:
                    a, b = m["a"], m["b"]
                    st.markdown(f"""<div class="match-card"><div style="font-weight: 700; margin-bottom: 0.4rem;">MATCH PRIVÉ BILATÉRAL · {m['periode']} · {m['specialite']}</div><p><strong>{a['Nom']}</strong> ({a['Hopital_Actuel']}) &nbsp;&lt;-&gt;&nbsp; <strong>{b['Nom']}</strong> ({b['Hopital_Actuel']})</p><p style="margin: 0.4rem 0 0 0; font-size: 0.85rem;">Coordonnées réservées : <a href="mailto:{a['Email']}">{a['Email']}</a> | <a href="mailto:{b['Email']}">{b['Email']}</a></p></div>""", unsafe_allow_html=True)
                    render_private_chat_room(m["room_id"], current_user, df_messages, f"Salon privé binôme ({m['periode']} · {m['specialite']})")

        with col_tri:
            st.markdown(f"### Mes Salons Triangulaires — Cycles à 3 ({len(mes_matchs_triangulaires)})")
            if not mes_matchs_triangulaires: st.info("Aucun cycle triangulaire ne vous concerne actuellement.")
            else:
                for t in mes_matchs_triangulaires:
                    a, b, c = t["a"], t["b"], t["c"]
                    st.markdown(f"""<div class="tri-card"><div style="font-weight: 700; margin-bottom: 0.4rem;">MATCH PRIVÉ TRIANGULAIRE · {t['periode']} · {t['specialite']}</div><p><strong>{a['Nom']}</strong> ({a['Hopital_Actuel']}) &nbsp;-&gt;&nbsp; <strong>{b['Nom']}</strong> ({b['Hopital_Actuel']}) &nbsp;-&gt;&nbsp; <strong>{c['Nom']}</strong> ({c['Hopital_Actuel']}) &nbsp;-&gt;&nbsp; <strong>{a['Nom']}</strong></p><p style="margin: 0.4rem 0 0 0; font-size: 0.85rem;">Coordonnées réservées : <a href="mailto:{a['Email']}">{a['Email']}</a> · <a href="mailto:{b['Email']}">{b['Email']}</a> · <a href="mailto:{c['Email']}">{c['Email']}</a></p></div>""", unsafe_allow_html=True)
                    render_private_chat_room(t["room_id"], current_user, df_messages, f"Salon privé triangulaire ({t['periode']} · {t['specialite']})")

# ===========================================================================
# ONGLET 3 : CONSULTER TOUTES LES OFFRES (REFONTE GRAPHIQUE)
# ===========================================================================
with tab3:
    st.subheader("Catalogue des offres de stage disponibles")
    st.caption("Pour garantir la confidentialité des échanges, seuls les lieux de stage proposés et souhaités sont affichés publiquement. Les identités et adresses email ne sont révélées qu'en cas de match mutuel dans votre onglet privé.")

    f_col0, f_col1, f_col2, f_col3, f_col4 = st.columns(5)
    with f_col0:
        filtre_statut = st.selectbox("Statut de l'offre", options=["Disponibles uniquement", "Toutes les offres"])
    with f_col1:
        filtre_periode = st.selectbox("Filtrer par Période", options=["Toutes"] + PERIODES)
    with f_col2:
        filtre_specialite = st.selectbox("Filtrer par Spécialité", options=["Toutes"] + SPECIALITES)
    with f_col3:
        filtre_region = st.selectbox("Région actuelle", options=["Toutes"] + REGIONS)
    with f_col4:
        filtre_recherche = st.text_input("Recherche libre", placeholder="Ex. Saint Luc...")

    df_filtre = df_demandes.copy()
    if filtre_statut == "Disponibles uniquement":
        df_filtre = df_filtre[df_filtre["Statut"] == "Disponible"]
    if filtre_periode != "Toutes": df_filtre = df_filtre[df_filtre["Periode"] == filtre_periode]
    if filtre_specialite != "Toutes": df_filtre = df_filtre[df_filtre["Specialite"] == filtre_specialite]
    if filtre_region != "Toutes":
        hopitaux_reg = set(HOPITAUX_PAR_REGION[filtre_region])
        df_filtre = df_filtre[df_filtre["Hopital_Actuel"].isin(hopitaux_reg)]
    if filtre_recherche.strip():
        q = filtre_recherche.strip().lower()
        df_filtre = df_filtre[df_filtre["Hopital_Actuel"].str.lower().str.contains(q, na=False) | df_filtre["Hopitaux_Souhaites"].str.lower().str.contains(q, na=False)]

    if df_filtre.empty:
        st.info("Aucune offre ne correspond aux critères sélectionnés.")
    else:
        for _, row in df_filtre.iterrows():
            souhaites_list = parse_hospitals(row["Hopitaux_Souhaites"])
            region_act = HOPITAL_VERS_REGION.get(row["Hopital_Actuel"], "Autre")
            
            statut = row.get("Statut", "Disponible")
            if statut == "Disponible": badge_statut = '<span class="badge-statut-dispo">🟢 Disponible</span>'
            elif statut == "En discussion": badge_statut = '<span class="badge-statut-discu">🟠 En discussion</span>'
            else: badge_statut = '<span class="badge-statut-accord">✅ Accord trouvé</span>'

            # Génération des pastilles/chips pour les hôpitaux souhaités
            chips_html = "".join([f'<span class="chip-hopital">🎯 {h}</span>' for h in souhaites_list])

            st.markdown(
                f"""
                <div class="offer-card-new">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span class="badge-periode">{row['Periode']}</span>
                            <span class="badge-specialite">{row['Specialite']}</span>
                            {badge_statut}
                        </div>
                        <span style="font-size:0.8rem; color:#64748b;">Mise à jour : {row['Timestamp']}</span>
                    </div>
                    
                    <div class="zone-actuel">
                        <strong>📍 Affectation actuelle :</strong> {row['Hopital_Actuel']} <span style="color:#64748b; font-size:0.9em;">(Région {region_act})</span>
                    </div>
                    
                    <div class="zone-souhaites">
                        <strong style="display:block; margin-bottom:0.5rem;">Vœux d'échange vers :</strong>
                        {chips_html}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ===========================================================================
# ONGLET 4 : GÉRER MON OFFRE (MODIFICATION PRÉ-REMPLIE, STATUT & SUPPRESSION)
# ===========================================================================
with tab4:
    st.subheader("Gérer mes annonces publiées (Modification & Suppression)")

    if current_user is None:
        st.warning("🔒 Connectez-vous à votre compte étudiant dans le menu latéral pour gérer vos offres.")
    else:
        df_mes_offres = df_demandes[df_demandes["Email"].str.lower() == current_user_email]

        if df_mes_offres.empty:
            st.info("Vous n'avez aucune annonce active pour le moment.")
        else:
            for idx, row in df_mes_offres.iterrows():
                demande_id_courante = str(row["Demande_ID"]).strip()
                periode_courante = row["Periode"]
                spec_courante = row["Specialite"]
                hop_actuel_courant = row["Hopital_Actuel"]
                statut_courant = row.get("Statut", "Disponible")
                souhaites_courants = [h for h in parse_hospitals(row["Hopitaux_Souhaites"]) if h in TOUS_LES_HOPITAUX]

                with st.expander(f"📌 Période {periode_courante} · {spec_courante} — Actuel : {hop_actuel_courant} (ID: {demande_id_courante})", expanded=True):
                    col_edit, col_del = st.columns([2, 1])

                    with col_edit:
                        st.markdown("##### Option 1 : Mettre à jour l'annonce")
                        with st.form(f"edit_form_{demande_id_courante}"):
                            # Ajout de la gestion du Statut
                            new_statut = st.radio(
                                "Statut de votre annonce",
                                options=["Disponible", "En discussion", "Accord trouvé"],
                                index=["Disponible", "En discussion", "Accord trouvé"].index(statut_courant) if statut_courant in ["Disponible", "En discussion", "Accord trouvé"] else 0,
                                horizontal=True,
                                help="Mettez l'offre 'En discussion' ou sur 'Accord trouvé' pour suspendre les suggestions de l'algorithme envers les autres étudiants."
                            )
                            
                            new_hop_actuel = st.selectbox(
                                "Hôpital actuel", options=TOUS_LES_HOPITAUX,
                                index=TOUS_LES_HOPITAUX.index(hop_actuel_courant) if hop_actuel_courant in TOUS_LES_HOPITAUX else 0,
                                key=f"edit_act_{demande_id_courante}",
                            )
                            new_souhaites = st.multiselect(
                                "Hôpitaux souhaités", options=TOUS_LES_HOPITAUX, default=souhaites_courants,
                                format_func=lambda h: f"[{HOPITAL_VERS_REGION.get(h, '')}] {h}",
                                key=f"edit_wish_{demande_id_courante}",
                            )
                            if st.form_submit_button("Enregistrer les modifications", type="primary", use_container_width=True):
                                if not new_souhaites: st.error("Conservez au moins un hôpital souhaité.")
                                elif new_hop_actuel in new_souhaites: st.error("L'hôpital actuel ne peut pas être souhaité.")
                                else:
                                    update_data = {
                                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "Hopital_Actuel": new_hop_actuel,
                                        "Hopitaux_Souhaites": serialize_hospitals(new_souhaites),
                                        "Statut": new_statut
                                    }
                                    if update_demande_firestore(demande_id_courante, update_data):
                                        st.success("Votre annonce a été mise à jour avec succès !")
                                        st.rerun()

                    with col_del:
                        st.markdown("##### Option 2 : Supprimer l'annonce")
                        confirm_check = st.checkbox("Je confirme vouloir supprimer définitivement cette offre", key=f"confirm_del_{demande_id_courante}")
                        if st.button("Confirmer la suppression", key=f"btn_del_{demande_id_courante}", type="secondary", disabled=not confirm_check, use_container_width=True):
                            if delete_demande_firestore(demande_id_courante):
                                st.success("Offre supprimée de Firestore.")
                                st.rerun()

    # -----------------------------------------------------------------------
    # ACCÈS ADMINISTRATEUR DISCRET
    # -----------------------------------------------------------------------
    st.write("")
    col_spacer, col_secret = st.columns([12, 1])
    with col_secret:
        if not st.session_state.get("is_admin", False):
            if hasattr(st, "dialog"):
                if st.button("🔒", key="btn_secret_admin_lock", help="Accès restreint"): dialog_admin_login()
            else:
                with st.expander("🔒", expanded=False):
                    with st.form("form_secret_admin_fallback"):
                        secret_in = st.text_input("Code secret", type="password")
                        if st.form_submit_button("Déverrouiller"):
                            if check_admin_password(secret_in): st.session_state["is_admin"] = True; st.rerun()
                            else: st.error("Accès refusé.")
        else:
            if st.button("🔓", help="Désactiver mode admin"): st.session_state["is_admin"] = False; st.rerun()

# ---------------------------------------------------------------------------
# 12. PIED DE PAGE (FOOTER GLOBAL)
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown("""<div style="text-align: center; color: #64748b; font-size: 0.82rem; padding: 1.25rem 0 0.5rem 0;">Plateforme conçue et développée par <strong>Imrane Machbaête</strong> — Version Alpha</div>""", unsafe_allow_html=True)
