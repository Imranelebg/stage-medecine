"""
PermutStage — Plateforme Collaborative d'Échange de Lieux de Stage (Médecine P3 à P8)
Architecture complète avec base de données Firebase Firestore (firebase-admin) :
- Comptes Étudiants (Collection 'users' + st.session_state['user'] + st.query_params['auth'])
- Offres de permutation (Collection 'demandes' avec écritures atomiques directes)
- Messagerie instantanée privée (Collection 'messages' par salon sécurisé)
- Confidentialité stricte des échanges (Matching Privé réservé aux étudiants impliqués)
- Centre de Notifications dynamique en haut à droite + Onglet Alertes
- Alertes Email automatiques via SMTP (smtplib + email.mime + st.secrets['smtp'])
- Gestion complète des offres (Modification pré-remplie + Suppression sécurisée)
- Code PIN oublié (renvoi automatique par email) et modification de PIN
- Accès Administrateur discret (st.secrets['admin']['password'])
- Mode d'affichage clair strict verrouillé (aucun mode sombre)

Exécution : streamlit run app.py
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

    /* Masquer uniquement le menu burger et le footer natif (ne jamais masquer le header complet) */
    #MainMenu {
        visibility: hidden !important;
    }

    footer,
    footer[data-testid="stFooter"] {
        visibility: hidden !important;
    }

    /* Masquer les boutons de statut superflus tout en préservant les contrôles */
    [data-testid="stToolbarActionButton"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    [data-testid="manage-app-button"] {
        visibility: hidden !important;
        display: none !important;
    }

    /* Force la visibilité et l'accessibilité permanente du bouton de déploiement de la sidebar */
    [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        color: #0f172a !important;
        z-index: 999999 !important;
    }

    [data-testid="collapsedControl"] button {
        color: #0f172a !important;
        background-color: #f8fafc !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
    }

    [data-testid="collapsedControl"] svg {
        color: #0f172a !important;
        fill: currentColor !important;
    }

    /* ==========================================================================
       2. FORÇAGE DU MODE CLAIR PAR DÉFAUT (FOND #F8FAFC & TEXTE #1E293B)
       ========================================================================== */
    :root,
    [data-theme="dark"],
    [data-theme="light"],
    .dark,
    .theme--dark,
    .stApp,
    html,
    body {
        color-scheme: light !important;
        --background-color: #f8fafc !important;
        --secondary-background-color: #ffffff !important;
        --text-color: #1e293b !important;
        --primary-color: #1d4ed8 !important;
        background-color: #f8fafc !important;
        color: #1e293b !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    /* Neutralisation absolue des préférences sombres du système / OS */
    @media (prefers-color-scheme: dark) {
        :root,
        [data-theme="dark"],
        [data-theme="light"],
        .dark,
        .theme--dark,
        html,
        body,
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stSidebar"],
        [data-testid="stSidebarContent"],
        section[data-testid="stSidebar"],
        .main,
        .block-container {
            color-scheme: light !important;
            --background-color: #f8fafc !important;
            --secondary-background-color: #ffffff !important;
            --text-color: #1e293b !important;
            --primary-color: #1d4ed8 !important;
            background-color: #f8fafc !important;
            color: #1e293b !important;
        }

        [data-testid="stSidebar"],
        [data-testid="stSidebar"] > div,
        [data-testid="stSidebarContent"],
        section[data-testid="stSidebar"] {
            background-color: #ffffff !important;
            color: #1e293b !important;
        }
    }

    /* Conteneur principal de l'application */
    [data-testid="stAppViewContainer"],
    .main,
    .block-container {
        background-color: #f8fafc !important;
        color: #1e293b !important;
    }

    /* Volet latéral (Sidebar) */
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div,
    [data-testid="stSidebarContent"],
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0 !important;
        color: #1e293b !important;
    }

    /* Typographie générale : titres, paragraphes, spans, listes */
    h1, h2, h3, h4, h5, h6 {
        color: #0f172a !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 700 !important;
    }

    p, span, div, li, td, th {
        color: #1e293b;
    }

    .stMarkdown,
    .stMarkdown p,
    .stMarkdown li,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] span {
        color: #1e293b !important;
    }

    /* Libellés de champs (Labels) bien sombres et lisibles */
    label,
    [data-testid="stWidgetLabel"],
    [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] span {
        color: #0f172a !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
    }

    /* Textes d'aide et légendes (Captions) */
    .stCaption,
    [data-testid="stCaptionContainer"] p,
    [data-testid="stCaptionContainer"] span {
        color: #64748b !important;
    }

    /* Champs de saisie (Inputs textuels, mots de passe, textareas) */
    input,
    textarea,
    [data-baseweb="input"],
    [data-baseweb="base-input"],
    [data-baseweb="textarea"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border-color: #cbd5e1 !important;
        -webkit-text-fill-color: #0f172a !important;
    }

    input::placeholder,
    textarea::placeholder {
        color: #94a3b8 !important;
        -webkit-text-fill-color: #94a3b8 !important;
    }

    /* Menus déroulants (Selectbox & Multiselect) */
    [data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
    }

    [data-baseweb="select"] span {
        color: #0f172a !important;
    }

    [data-baseweb="popover"],
    [data-baseweb="menu"],
    [data-baseweb="menu"] * {
        background-color: #ffffff !important;
        color: #0f172a !important;
    }

    [data-baseweb="menu"] li:hover,
    [data-baseweb="menu"] li:hover * {
        background-color: #f1f5f9 !important;
        color: #1d4ed8 !important;
    }

    /* Badges multiselects sélectionnés (Hôpitaux souhaités) */
    [data-baseweb="tag"] {
        background-color: #0056b3 !important;
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

    /* Boutons de commande primaires & soumission de formulaire ("Publier ma demande de permutation") */
    button[kind="primary"],
    button[kind="primaryFormSubmit"],
    [data-testid="stFormSubmitButton"] > button,
    .stButton > button[type="submit"] {
        background-color: #0056b3 !important;
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        border: none !important;
        font-weight: 700 !important;
    }

    button[kind="primary"] *,
    button[kind="primaryFormSubmit"] *,
    [data-testid="stFormSubmitButton"] > button *,
    .stButton > button[type="submit"] * {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        font-weight: 700 !important;
    }

    button[kind="primary"]:hover,
    button[kind="primaryFormSubmit"]:hover,
    [data-testid="stFormSubmitButton"] > button:hover,
    .stButton > button[type="submit"]:hover {
        background-color: #004494 !important;
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }

    button[kind="secondary"],
    .stButton > button {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        font-weight: 500 !important;
    }

    button[kind="secondary"]:hover,
    .stButton > button:hover {
        background-color: #f8fafc !important;
        color: #1d4ed8 !important;
        border-color: #94a3b8 !important;
    }

    /* Volets déroulants (Expanders) */
    [data-testid="stExpander"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        margin-bottom: 0.75rem !important;
    }

    [data-testid="stExpander"] summary {
        background-color: #ffffff !important;
        color: #0f172a !important;
        font-weight: 600 !important;
    }

    [data-testid="stExpander"] summary span,
    [data-testid="stExpander"] summary p {
        color: #0f172a !important;
    }

    [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
    }

    /* Onglets de navigation (Tabs) */
    [data-baseweb="tab-list"] {
        background-color: transparent !important;
        border-bottom: 2px solid #e2e8f0 !important;
    }

    button[data-baseweb="tab"] {
        color: #64748b !important;
        font-weight: 600 !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #1d4ed8 !important;
        font-weight: 700 !important;
        border-bottom-color: #1d4ed8 !important;
    }

    /* Indicateurs Métriques (KPIs) */
    [data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        padding: 0.85rem !important;
    }

    [data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-weight: 800 !important;
    }

    [data-testid="stMetricLabel"] {
        color: #475569 !important;
        font-weight: 600 !important;
    }

    /* Salons de discussion privés (Chat Messages) */
    [data-testid="stChatMessage"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        color: #0f172a !important;
        padding: 0.75rem 1rem !important;
    }

    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] span,
    [data-testid="stChatMessage"] div {
        color: #0f172a !important;
    }

    /* Tableaux et DataFrames */
    [data-testid="stDataFrame"],
    [data-testid="stTable"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
    }

    [data-testid="stDataFrame"] * {
        color: #0f172a !important;
    }

    /* Alertes Streamlit (info, success, warning, error) */
    [data-testid="stAlert"] * {
        color: #0f172a !important;
    }

    /* ==========================================================================
       3. ISOLATION DE LA BANNIÈRE HERO BLEUE (.hero-card / .hero-banner)
       ========================================================================== */
    .hero-card,
    .hero-banner,
    .hero-card h1, .hero-banner h1,
    .hero-card h2, .hero-banner h2,
    .hero-card h3, .hero-banner h3,
    .hero-card p, .hero-banner p,
    .hero-card span, .hero-banner span,
    .hero-card strong, .hero-banner strong,
    .hero-card em, .hero-banner em,
    .hero-card div, .hero-banner div,
    [data-testid="stMarkdownContainer"] .hero-card,
    [data-testid="stMarkdownContainer"] .hero-banner,
    [data-testid="stMarkdownContainer"] .hero-card h1,
    [data-testid="stMarkdownContainer"] .hero-banner h1,
    [data-testid="stMarkdownContainer"] .hero-card h2,
    [data-testid="stMarkdownContainer"] .hero-banner h2,
    [data-testid="stMarkdownContainer"] .hero-card h3,
    [data-testid="stMarkdownContainer"] .hero-banner h3,
    [data-testid="stMarkdownContainer"] .hero-card p,
    [data-testid="stMarkdownContainer"] .hero-banner p,
    [data-testid="stMarkdownContainer"] .hero-card span,
    [data-testid="stMarkdownContainer"] .hero-banner span,
    [data-testid="stMarkdownContainer"] .hero-card strong,
    [data-testid="stMarkdownContainer"] .hero-banner strong,
    [data-testid="stMarkdownContainer"] .hero-card em,
    [data-testid="stMarkdownContainer"] .hero-banner em,
    [data-testid="stMarkdownContainer"] .hero-card div,
    [data-testid="stMarkdownContainer"] .hero-banner div {
        color: #FFFFFF !important;
    }

    .hero-card,
    .hero-banner {
        background: linear-gradient(135deg, #1e3a8a 0%, #172554 100%) !important;
        color: #ffffff !important;
        padding: 2.2rem 2.4rem !important;
        border-radius: 14px !important;
        margin-bottom: 1.25rem !important;
        box-shadow: 0 4px 16px rgba(15, 23, 42, 0.14) !important;
        border: 1px solid rgba(59, 130, 246, 0.25) !important;
    }

    .hero-card h1,
    .hero-banner h1,
    [data-testid="stMarkdownContainer"] .hero-card h1,
    [data-testid="stMarkdownContainer"] .hero-banner h1 {
        font-size: 2.1rem !important;
        font-weight: 800 !important;
        line-height: 1.25 !important;
        margin: 0 0 0.5rem 0 !important;
        color: #FFFFFF !important;
    }

    .hero-card p,
    .hero-banner p,
    [data-testid="stMarkdownContainer"] .hero-card p,
    [data-testid="stMarkdownContainer"] .hero-banner p {
        font-size: 1.02rem !important;
        line-height: 1.65 !important;
        margin: 0 0 1.25rem 0 !important;
        max-width: 860px !important;
        color: #E2E8F0 !important;
    }

    .hero-card .hero-badge,
    .hero-banner .hero-badge,
    [data-testid="stMarkdownContainer"] .hero-card .hero-badge,
    [data-testid="stMarkdownContainer"] .hero-banner .hero-badge {
        display: inline-block !important;
        padding: 0.25rem 0.8rem !important;
        background: rgba(59, 130, 246, 0.25) !important;
        border: 1px solid rgba(147, 197, 253, 0.35) !important;
        border-radius: 9999px !important;
        font-size: 0.8rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.05em !important;
        color: #BFDBFE !important;
        margin-bottom: 0.85rem !important;
    }

    .hero-card .hero-alpha-box,
    .hero-banner .hero-alpha-box,
    [data-testid="stMarkdownContainer"] .hero-card .hero-alpha-box,
    [data-testid="stMarkdownContainer"] .hero-banner .hero-alpha-box {
        background: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 10px !important;
        padding: 0.95rem 1.15rem !important;
        font-size: 0.88rem !important;
        line-height: 1.55 !important;
        color: #F8FAFC !important;
    }

    .hero-card .hero-alpha-box strong,
    .hero-banner .hero-alpha-box strong,
    [data-testid="stMarkdownContainer"] .hero-card .hero-alpha-box strong,
    [data-testid="stMarkdownContainer"] .hero-banner .hero-alpha-box strong {
        color: #FDE047 !important;
    }

    .hero-card .hero-alpha-box em,
    .hero-banner .hero-alpha-box em,
    [data-testid="stMarkdownContainer"] .hero-card .hero-alpha-box em,
    [data-testid="stMarkdownContainer"] .hero-banner .hero-alpha-box em {
        color: #FFFFFF !important;
    }

    /* ==========================================================================
       4. STYLES DES COMPOSANTS ET CARTES MÉTIER PERSONNALISÉES (LIGHT)
       ========================================================================== */
    .permut-banner {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        color: #0f172a !important;
        padding: 1.25rem 1.75rem !important;
        border-radius: 10px !important;
        margin-bottom: 1.25rem !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    }

    .match-card {
        background-color: #f0fdf4 !important;
        border: 1px solid #86efac !important;
        border-radius: 10px !important;
        padding: 1.25rem !important;
        margin-bottom: 1rem !important;
        color: #14532d !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    }

    .match-card * {
        color: #14532d !important;
    }

    .match-card a {
        color: #15803d !important;
        text-decoration: underline !important;
        font-weight: 600 !important;
    }

    .tri-card {
        background-color: #ecfdf5 !important;
        border: 1px solid #6ee7b7 !important;
        border-radius: 10px !important;
        padding: 1.25rem !important;
        margin-bottom: 1rem !important;
        color: #064e3b !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    }

    .tri-card * {
        color: #064e3b !important;
    }

    .tri-card a {
        color: #047857 !important;
        text-decoration: underline !important;
        font-weight: 600 !important;
    }

    .offer-card {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        padding: 1.15rem !important;
        margin-bottom: 0.75rem !important;
        color: #0f172a !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    }

    .offer-card p,
    .offer-card div,
    .offer-card strong,
    .offer-card span {
        color: #0f172a;
    }

    .notif-card {
        background-color: #eff6ff !important;
        border: 1px solid #bfdbfe !important;
        border-radius: 8px !important;
        padding: 0.9rem 1.1rem !important;
        margin-bottom: 0.6rem !important;
        color: #1e3a8a !important;
    }

    .step-card {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        padding: 1rem !important;
        min-height: 190px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    }

    .step-card strong {
        color: #0f172a !important;
    }

    .step-card p {
        color: #475569 !important;
    }
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
# Données mock initiales (vidées définitivement pour fonctionnement 100% Firestore réel)
# ---------------------------------------------------------------------------
USERS_INITIAUX_MOCK: list = []
DEMANDES_INITIALES_MOCK: list = []
MESSAGES_INITIAUX_MOCK: list = []

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
    """Vérifie le code secret administrateur par rapport à st.secrets['admin']['password']."""
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
    """
    Initialise l'application Firebase Admin de façon protégée (anti-réinitialisation multiple)
    en utilisant les credentials stockés dans st.secrets['firebase'].
    Retourne l'instance client Firestore.
    """
    if not firebase_admin._apps:
        try:
            if "firebase" not in st.secrets:
                st.error(
                    "Configuration Firebase introuvable. Veuillez définir [firebase] dans .streamlit/secrets.toml."
                )
                return None

            fb_creds_dict = dict(st.secrets["firebase"])

            # Gestion robuste du retour à la ligne dans la clé privée RSA
            if "private_key" in fb_creds_dict and isinstance(fb_creds_dict["private_key"], str):
                fb_creds_dict["private_key"] = fb_creds_dict["private_key"].replace("\\n", "\n")

            cred = credentials.Certificate(fb_creds_dict)
            firebase_admin.initialize_app(cred)
        except Exception as exc:
            st.error(f"Erreur d'initialisation du SDK Firebase Admin : {exc}")
            return None

    return firestore.client()


def normalize_pin_series(series: pd.Series) -> pd.Series:
    """Nettoie et force le format 4 chiffres pour une colonne de codes PIN."""
    s = (
        series.fillna("")
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
    )
    return s.apply(lambda x: x.zfill(4) if (x.isdigit() and len(x) <= 4) else x)


@st.cache_data(ttl=15)
def load_users_data() -> pd.DataFrame:
    """
    Lit l'ensemble des documents de la collection 'users' dans Firestore.
    Si la base Firestore est vide ou inaccessible, retourne un DataFrame vide
    avec les colonnes COLONNES_UTILISATEURS (aucun profil de démonstration).
    """
    db = get_firestore_client()
    if db is None:
        return pd.DataFrame(columns=COLONNES_UTILISATEURS)

    try:
        docs = db.collection(COLLECTION_USERS).stream()
        data = []
        for doc in docs:
            item = doc.to_dict() or {}
            item["User_ID"] = str(item.get("User_ID") or doc.id).strip()
            data.append(item)

        if not data:
            return pd.DataFrame(columns=COLONNES_UTILISATEURS)

        df = pd.DataFrame(data)
        for col in COLONNES_UTILISATEURS:
            if col not in df.columns:
                df[col] = ""

        df["PIN"] = normalize_pin_series(df["PIN"])
        for col in ["User_ID", "Nom", "Prenom", "Email", "Date_Inscription"]:
            df[col] = df[col].fillna("").astype(str).str.strip()

        return df[COLONNES_UTILISATEURS]
    except Exception as exc:
        st.error(f"Erreur lors de la lecture de la collection '{COLLECTION_USERS}' : {exc}")
        return pd.DataFrame(columns=COLONNES_UTILISATEURS)


# Alias pour rétro-compatibilité
load_utilisateurs = load_users_data


def create_user_firestore(user_dict: dict) -> bool:
    """
    Crée un document utilisateur directement dans la collection 'users' de Firestore
    sans risque de collision, puis purge le cache de lecture.
    """
    db = get_firestore_client()
    if db is None:
        return False

    try:
        user_id = user_dict["User_ID"]
        db.collection(COLLECTION_USERS).document(user_id).set(user_dict)
        st.cache_data.clear()
        return True
    except Exception as exc:
        st.error(f"Erreur lors de la création du compte dans Firestore : {exc}")
        return False


def update_user_pin_firestore(user_id: str, email: str, new_pin: str) -> bool:
    """
    Met à jour atomiquement le code PIN d'un utilisateur dans 'users'
    et synchronise ses offres actives dans 'demandes', puis purge le cache.
    """
    db = get_firestore_client()
    if db is None:
        return False

    try:
        pin_clean = str(new_pin).strip().zfill(4)
        db.collection(COLLECTION_USERS).document(user_id).update({"PIN": pin_clean})

        # Mettre à jour en cascade le PIN dans les annonces publiées par cet email
        clean_email = email.strip().lower()
        demandes_query = db.collection(COLLECTION_DEMANDES).where("Email", "==", clean_email).stream()
        for doc in demandes_query:
            doc.reference.update({"PIN": pin_clean})

        st.cache_data.clear()
        return True
    except Exception as exc:
        st.error(f"Erreur lors de la mise à jour du code PIN : {exc}")
        return False


@st.cache_data(ttl=15)
def load_demandes_data() -> pd.DataFrame:
    """
    Lit l'ensemble des offres de la collection 'demandes' dans Firestore.
    Si la base Firestore est vide ou inaccessible, retourne un DataFrame vide
    avec les colonnes COLONNES_DEMANDES (aucun profil de démonstration).
    """
    db = get_firestore_client()
    if db is None:
        return pd.DataFrame(columns=COLONNES_DEMANDES)

    try:
        docs = db.collection(COLLECTION_DEMANDES).stream()
        data = []
        for doc in docs:
            item = doc.to_dict() or {}
            item["Demande_ID"] = str(item.get("Demande_ID") or doc.id).strip()
            data.append(item)

        if not data:
            return pd.DataFrame(columns=COLONNES_DEMANDES)

        df = pd.DataFrame(data)
        for col in COLONNES_DEMANDES:
            if col not in df.columns:
                df[col] = ""

        df["PIN"] = normalize_pin_series(df["PIN"])
        for col in ["Demande_ID", "Timestamp", "Nom", "Email", "Periode", "Specialite", "Hopital_Actuel", "Hopitaux_Souhaites"]:
            df[col] = df[col].fillna("").astype(str).str.strip()

        return df[COLONNES_DEMANDES]
    except Exception as exc:
        st.error(f"Erreur lors de la lecture de la collection '{COLLECTION_DEMANDES}' : {exc}")
        return pd.DataFrame(columns=COLONNES_DEMANDES)


# Alias pour rétro-compatibilité
load_demandes = load_demandes_data


def add_demande_firestore(demande_dict: dict) -> bool:
    """
    Publie une nouvelle demande dans 'demandes' avec écriture directe Firestore
    et actualisation immédiate du cache.
    """
    db = get_firestore_client()
    if db is None:
        return False

    try:
        demande_id = demande_dict.get("Demande_ID") or f"DEM_{uuid.uuid4().hex[:10].upper()}"
        demande_dict["Demande_ID"] = demande_id
        db.collection(COLLECTION_DEMANDES).document(demande_id).set(demande_dict)
        st.cache_data.clear()
        return True
    except Exception as exc:
        st.error(f"Erreur lors du dépôt de la demande dans Firestore : {exc}")
        return False


def update_demande_firestore(demande_id: str, fields: dict) -> bool:
    """
    Modifie une demande existante dans 'demandes' via son identifiant de document Firestore.
    """
    db = get_firestore_client()
    if db is None:
        return False

    try:
        db.collection(COLLECTION_DEMANDES).document(demande_id).update(fields)
        st.cache_data.clear()
        return True
    except Exception as exc:
        st.error(f"Erreur lors de la modification de l'offre dans Firestore : {exc}")
        return False


def delete_demande_firestore(demande_id: str) -> bool:
    """
    Supprime définitivement un document de la collection 'demandes'.
    """
    db = get_firestore_client()
    if db is None:
        return False

    try:
        db.collection(COLLECTION_DEMANDES).document(demande_id).delete()
        st.cache_data.clear()
        return True
    except Exception as exc:
        st.error(f"Erreur lors de la suppression de l'offre dans Firestore : {exc}")
        return False


def delete_user_firestore(user_id: str) -> bool:
    """
    Supprime le document dans la collection 'users' ET supprime également en cascade
    toutes les offres liées à cet email dans la collection 'demandes'.
    """
    db = get_firestore_client()
    if db is None:
        return False

    try:
        clean_user_id = str(user_id).strip()
        user_ref = db.collection(COLLECTION_USERS).document(clean_user_id)
        user_snap = user_ref.get()
        user_email = ""
        if user_snap.exists:
            u_data = user_snap.to_dict() or {}
            user_email = str(u_data.get("Email", "")).strip().lower()
        else:
            q = db.collection(COLLECTION_USERS).where("User_ID", "==", clean_user_id).stream()
            for doc in q:
                u_data = doc.to_dict() or {}
                user_email = str(u_data.get("Email", "")).strip().lower()
                doc.reference.delete()

        # Supprimer le document utilisateur
        user_ref.delete()

        # Supprimer en cascade toutes les offres liées à cet email dans 'demandes'
        if user_email:
            demandes_query = db.collection(COLLECTION_DEMANDES).where("Email", "==", user_email).stream()
            for doc_demande in demandes_query:
                doc_demande.reference.delete()

        st.cache_data.clear()
        return True
    except Exception as exc:
        st.error(f"Erreur lors de la suppression de l'utilisateur dans Firestore : {exc}")
        return False


@st.cache_data(ttl=15)
def load_messages_data() -> pd.DataFrame:
    """
    Lit l'ensemble des messages de la collection 'messages' dans Firestore.
    Si la base Firestore est vide ou inaccessible, retourne un DataFrame vide
    avec les colonnes COLONNES_MESSAGES (aucun profil de démonstration).
    """
    db = get_firestore_client()
    if db is None:
        return pd.DataFrame(columns=COLONNES_MESSAGES)

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
        for col in COLONNES_MESSAGES:
            if col not in df.columns:
                df[col] = ""
            df[col] = df[col].fillna("").astype(str).str.strip()

        # Tri chronologique des messages
        if not df.empty and "Timestamp" in df.columns:
            df = df.sort_values(by="Timestamp", ascending=True).reset_index(drop=True)

        return df[COLONNES_MESSAGES]
    except Exception as exc:
        st.error(f"Erreur lors de la lecture de la collection '{COLLECTION_MESSAGES}' : {exc}")
        return pd.DataFrame(columns=COLONNES_MESSAGES)


# Alias pour rétro-compatibilité
load_messages = load_messages_data


def append_message_firestore(
    room_id: str,
    sender_email: str,
    sender_name: str,
    texte: str,
) -> bool:
    """
    Écrit un nouveau message directement dans la collection 'messages' de Firestore
    sans bloquer les autres salons, puis purge le cache.
    """
    db = get_firestore_client()
    if db is None:
        return False

    try:
        msg_id = f"MSG_{uuid.uuid4().hex[:10].upper()}"
        nouveau_msg = {
            "Message_ID": msg_id,
            "Room_ID": room_id.strip(),
            "Sender_Email": sender_email.strip().lower(),
            "Sender_Name": sender_name.strip(),
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Texte": texte.strip(),
        }
        db.collection(COLLECTION_MESSAGES).document(msg_id).set(nouveau_msg)
        st.cache_data.clear()
        return True
    except Exception as exc:
        st.error(f"Erreur lors de l'envoi du message : {exc}")
        return False


def serialize_hospitals(hospitals: list[str]) -> str:
    return "; ".join([h.strip() for h in hospitals if h.strip()])


def parse_hospitals(raw_str: str) -> list[str]:
    if not raw_str or pd.isna(raw_str):
        return []
    return [h.strip() for h in str(raw_str).split(";") if h.strip()]


def build_room_id(periode: str, specialite: str, emails: list[str]) -> str:
    sorted_emails = sorted([e.strip().lower() for e in emails])
    return f"ROOM_{periode}_{specialite}_{'_'.join(sorted_emails)}"


# ---------------------------------------------------------------------------
# 5. SYSTÈME D'ALERTES PAR EMAIL (OPTION A : DÉCLENCHÉ SUR MATCH DIRECT)
# ---------------------------------------------------------------------------
def resolve_student_prenom(
    email: str, fallback_nom: str, df_utilisateurs: pd.DataFrame
) -> str:
    """Récupère le prénom de l'étudiant depuis le profil 'users' ou depuis son nom complet."""
    clean_email = (email or "").strip().lower()
    if df_utilisateurs is not None and not df_utilisateurs.empty and clean_email:
        rows = df_utilisateurs[
            df_utilisateurs["Email"].astype(str).str.strip().str.lower() == clean_email
        ]
        if not rows.empty:
            prenom_val = str(rows.iloc[0].get("Prenom", "")).strip()
            if prenom_val:
                return prenom_val
    if fallback_nom and str(fallback_nom).strip():
        return str(fallback_nom).strip().split()[0]
    return "Étudiant(e)"


def send_match_notification_emails(
    participants: list[dict],
    periode: str,
    specialite: str,
    room_id: str,
    df_utilisateurs: pd.DataFrame,
) -> int:
    """
    Option A stricte : Envoie un email individuel personnalisé uniquement aux 2 ou 3 étudiants
    faisant partie intégrante d'un nouveau cycle complet (bilatéral ou triangulaire).
    Anti-plantage absolu (try/except) et anti-doublon par Room_ID.
    """
    if room_id in st.session_state["notified_match_rooms"]:
        return 0

    try:
        smtp_cfg = st.secrets["smtp"]
        smtp_server = str(smtp_cfg["server"]).strip()
        smtp_port = int(smtp_cfg["port"])
        smtp_user = str(smtp_cfg["username"]).strip()
        smtp_password = str(smtp_cfg["password"])
    except Exception:
        # Si les secrets SMTP ne sont pas configurés, l'enregistrement Firestore reste prioritaire
        return 0

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

                prenom = resolve_student_prenom(
                    dest_email, participant.get("Nom", ""), df_utilisateurs
                )
                corps = (
                    f"Bonjour {prenom},\n\n"
                    f"Une opportunité d'échange direct vient de se former pour votre stage de {specialite} ({periode}) !\n\n"
                    f"Un salon de discussion privé et sécurisé a été ouvert sur l'application. Connectez-vous dès maintenant sur PermutStage avec votre adresse étudiante et votre code PIN pour consulter les détails du match et finaliser l'échange :\n"
                    f"https://stages-medecine-ucl.streamlit.app/\n\n"
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

        st.session_state["notified_match_rooms"].add(room_id)
        return sent_count
    except Exception:
        return sent_count


def trigger_new_match_emails(
    anciens_rooms: set[str],
    df_demandes_maj: pd.DataFrame,
    df_utilisateurs: pd.DataFrame,
    df_messages: pd.DataFrame,
) -> None:
    """
    Vérifie automatiquement après un ajout ou une modification dans 'demandes' si un nouveau
    cycle complet (bilatéral A<->B ou triangulaire A->B->C->A) vient de se former.
    N'envoie jamais d'email pour une offre isolée ou un match déjà existant.
    """
    try:
        rooms_deja_actifs = set(anciens_rooms) | set(
            st.session_state.get("notified_match_rooms", set())
        )
        if df_messages is not None and not df_messages.empty and "Room_ID" in df_messages.columns:
            rooms_deja_actifs |= set(
                df_messages["Room_ID"].dropna().astype(str).str.strip().unique()
            )

        nouveaux_bi = compute_bilateral_matches(df_demandes_maj)
        nouveaux_tri = compute_triangular_matches(df_demandes_maj)

        for m in nouveaux_bi:
            if m["room_id"] not in rooms_deja_actifs:
                send_match_notification_emails(
                    participants=m["participants"],
                    periode=m["periode"],
                    specialite=m["specialite"],
                    room_id=m["room_id"],
                    df_utilisateurs=df_utilisateurs,
                )

        for t in nouveaux_tri:
            if t["room_id"] not in rooms_deja_actifs:
                send_match_notification_emails(
                    participants=t["participants"],
                    periode=t["periode"],
                    specialite=t["specialite"],
                    room_id=t["room_id"],
                    df_utilisateurs=df_utilisateurs,
                )
    except Exception:
        pass


def send_pin_recovery_email(dest_email: str, prenom: str, pin: str) -> bool:
    """
    Envoie le code PIN par email via SMTP en cas d'oubli de l'étudiant.
    Respecte l'objet et le corps de message personnalisés.
    """
    try:
        smtp_cfg = st.secrets["smtp"]
        smtp_server = str(smtp_cfg["server"]).strip()
        smtp_port = int(smtp_cfg["port"])
        smtp_user = str(smtp_cfg["username"]).strip()
        smtp_password = str(smtp_cfg["password"])
    except Exception:
        raise RuntimeError("Configuration SMTP introuvable dans st.secrets['smtp'].")

    pin_formatte = str(pin).strip().zfill(4)
    sujet = "[PermutStage] Récupération de votre code PIN"
    corps = (
        f"Bonjour {prenom},\n\n"
        f"Vous avez demandé la récupération de votre code PIN pour accéder à PermutStage.\n\n"
        f"Votre code PIN de connexion est : {pin_formatte}\n\n"
        f"Vous pouvez désormais vous connecter directement sur la plateforme :\n"
        f"https://stages-medecine-ucl.streamlit.app/\n\n"
        f"Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet email ou modifier votre PIN depuis votre profil.\n\n"
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
# 6. MOTEUR DE MATCHING & FILTRE DE CONFIDENTIALITÉ STRICTE
# ---------------------------------------------------------------------------
def compute_bilateral_matches(df: pd.DataFrame) -> list[dict]:
    """Détecte tous les échanges bilatéraux (A <-> B) pour même période et même spécialité."""
    matches = []
    if df.empty:
        return matches
    records = df.to_dict("records")
    n = len(records)

    for i in range(n):
        for j in range(i + 1, n):
            a, b = records[i], records[j]
            if a["Periode"] != b["Periode"] or a["Specialite"] != b["Specialite"]:
                continue
            if a["Hopital_Actuel"] == b["Hopital_Actuel"]:
                continue

            souhaites_a = set(parse_hospitals(a["Hopitaux_Souhaites"]))
            souhaites_b = set(parse_hospitals(b["Hopitaux_Souhaites"]))

            if (
                a["Hopital_Actuel"] in souhaites_b
                and b["Hopital_Actuel"] in souhaites_a
            ):
                room_id = build_room_id(
                    a["Periode"], a["Specialite"], [a["Email"], b["Email"]]
                )
                matches.append(
                    {
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
                    }
                )
    return matches


def compute_triangular_matches(df: pd.DataFrame) -> list[dict]:
    """Détecte tous les cycles à 3 personnes (A donne à B, B donne à C, C donne à A)."""
    matches = []
    if df.empty:
        return matches
    seen_cycles = set()
    records = df.to_dict("records")
    n = len(records)

    souhaites_map = {
        idx: set(parse_hospitals(rec["Hopitaux_Souhaites"]))
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
                    rotations = sorted(
                        [
                            (id_a, id_b, id_c),
                            (id_b, id_c, id_a),
                            (id_c, id_a, id_b),
                        ]
                    )
                    canonical = rotations[0]
                    if canonical not in seen_cycles:
                        seen_cycles.add(canonical)
                        room_id = build_room_id(
                            a["Periode"],
                            a["Specialite"],
                            [a["Email"], b["Email"], c["Email"]],
                        )
                        matches.append(
                            {
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
                            }
                        )
    return matches


def filter_private_matches_for_user(
    user_email: str | None,
    all_bilateral: list[dict],
    all_triangular: list[dict],
) -> tuple[list[dict], list[dict]]:
    """
    RÈGLE ABSOLUE DE CONFIDENTIALITÉ :
    Ne retourne QUE les matchs impliquant directement l'étudiant connecté.
    Un visiteur non connecté ou un étudiant tiers ne voit aucun match.
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
    """Construit la liste des alertes (matchs actifs et messages reçus) pour l'étudiant connecté."""
    if not user_email:
        return []
    clean_email = user_email.strip().lower()
    notifs = []
    my_rooms = set()

    for m in my_bi:
        my_rooms.add(m["room_id"])
        notifs.append(
            {
                "titre": f"Nouvelle proposition d'échange trouvée pour votre stage de {m['specialite']} en {m['periode']} !",
                "detail": "Match bilatéral (binôme) disponible dans votre salon privé.",
                "room_id": m["room_id"],
            }
        )

    for t in my_tri:
        my_rooms.add(t["room_id"])
        notifs.append(
            {
                "titre": f"Nouvelle proposition d'échange trouvée pour votre stage de {t['specialite']} en {t['periode']} !",
                "detail": "Salon d'échange triangulaire (cycle à 3 personnes) ouvert pour vous.",
                "room_id": t["room_id"],
            }
        )

    if not df_messages.empty and my_rooms:
        msgs_for_me = df_messages[
            (df_messages["Room_ID"].isin(my_rooms))
            & (df_messages["Sender_Email"].str.lower() != clean_email)
        ]
        for _, msg in msgs_for_me.iterrows():
            notifs.append(
                {
                    "titre": f"Nouveau message de {msg['Sender_Name']} ({msg['Timestamp']})",
                    "detail": f"« {msg['Texte']} »",
                    "room_id": msg["Room_ID"],
                }
            )

    return notifs


# ---------------------------------------------------------------------------
# 7. COMPOSANT DE SALON DE CHAT PRIVÉ (RÉSERVÉ AUX PARTICIPANTS DU MATCH)
# ---------------------------------------------------------------------------
def render_private_chat_room(
    room_id: str,
    current_user: dict,
    df_messages: pd.DataFrame,
    label_expander: str,
):
    """Salon de discussion privé avec persistance Firestore par document unique."""
    messages_salon = df_messages[df_messages["Room_ID"] == room_id] if not df_messages.empty else pd.DataFrame()
    nb_msg = len(messages_salon)
    user_email = current_user["Email"].strip().lower()
    user_full_name = f"{current_user['Prenom']} {current_user['Nom']}".strip()

    with st.expander(f"💬 {label_expander} ({nb_msg} message(s))", expanded=True):
        if messages_salon.empty:
            st.caption("Aucun message dans ce salon privé. Envoyez le premier message à vos collègues !")
        else:
            for _, msg in messages_salon.iterrows():
                is_me = msg["Sender_Email"].strip().lower() == user_email
                role = "user" if is_me else "assistant"
                with st.chat_message(role):
                    st.markdown(
                        f"**{msg['Sender_Name']}** · *{msg['Timestamp']}*\n\n{msg['Texte']}"
                    )

        nouveau_texte = st.chat_input(
            "Écrire un message dans ce salon privé...",
            key=f"chat_input_{room_id}",
        )
        if nouveau_texte and nouveau_texte.strip():
            if append_message_firestore(
                room_id, user_email, user_full_name, nouveau_texte
            ):
                st.rerun()


# ---------------------------------------------------------------------------
# 8. CHARGEMENT DES DONNÉES & PERSISTANCE DE SESSION VIA ST.QUERY_PARAMS
# ---------------------------------------------------------------------------
def get_auth_query_param() -> str | None:
    """Récupère l'identifiant de session stocké dans l'URL (st.query_params)."""
    try:
        if hasattr(st, "query_params"):
            val = st.query_params.get("auth", None)
            return str(val).strip() if val else None
        elif hasattr(st, "experimental_get_query_params"):
            params = st.experimental_get_query_params()
            if "auth" in params and params["auth"]:
                return str(params["auth"][0]).strip()
    except Exception:
        pass
    return None


def set_auth_query_param(token: str):
    """Enregistre le jeton de session dans l'URL (st.query_params['auth'] = user_id)."""
    try:
        if hasattr(st, "query_params"):
            st.query_params["auth"] = token
        elif hasattr(st, "experimental_set_query_params"):
            st.experimental_set_query_params(auth=token)
    except Exception:
        pass


def clear_query_params():
    """Efface complètement les paramètres d'URL lors de la déconnexion."""
    try:
        if hasattr(st, "query_params"):
            st.query_params.clear()
        elif hasattr(st, "experimental_set_query_params"):
            st.experimental_set_query_params()
    except Exception:
        pass


df_utilisateurs = load_users_data()
df_demandes = load_demandes_data()
df_messages = load_messages_data()

# Reconnexion automatique et transparente si 'auth' est présent dans l'URL (F5 / réveil smartphone)
auth_token = get_auth_query_param()
if auth_token and st.session_state.get("user") is None:
    target_clean = auth_token.strip().lower()
    match_users = pd.DataFrame()
    if not df_utilisateurs.empty:
        match_users = df_utilisateurs[
            (df_utilisateurs["Email"].astype(str).str.strip().str.lower() == target_clean)
            | (df_utilisateurs["User_ID"].astype(str).str.strip().str.lower() == target_clean)
        ]

    # Si absent du cache local, interroger directement Firestore
    if match_users.empty:
        try:
            db_fs = get_firestore_client()
            if db_fs:
                docs_by_email = (
                    db_fs.collection(COLLECTION_USERS)
                    .where("Email", "==", target_clean)
                    .limit(1)
                    .stream()
                )
                for doc_u in docs_by_email:
                    u_data = doc_u.to_dict() or {}
                    u_data["User_ID"] = str(u_data.get("User_ID") or doc_u.id).strip()
                    match_users = pd.DataFrame([u_data])
        except Exception:
            pass

    if not match_users.empty:
        u_saved = match_users.iloc[0]
        pin_val = str(u_saved["PIN"]).strip()
        st.session_state["user"] = {
            "User_ID": str(u_saved["User_ID"]).strip(),
            "Nom": str(u_saved["Nom"]).strip(),
            "Prenom": str(u_saved["Prenom"]).strip(),
            "Email": str(u_saved["Email"]).strip().lower(),
            "PIN": pin_val.zfill(4) if pin_val.isdigit() else pin_val,
        }
        set_auth_query_param(str(u_saved["Email"]).strip().lower())
    else:
        clear_query_params()

all_matchs_binomes = compute_bilateral_matches(df_demandes)
all_matchs_triangulaires = compute_triangular_matches(df_demandes)

current_user = st.session_state.get("user")
current_user_email = current_user["Email"].strip().lower() if current_user else None

mes_matchs_binomes, mes_matchs_triangulaires = filter_private_matches_for_user(
    current_user_email, all_matchs_binomes, all_matchs_triangulaires
)
mes_notifications = build_user_notifications(
    current_user_email, mes_matchs_binomes, mes_matchs_triangulaires, df_messages
)

# ---------------------------------------------------------------------------
# 9. VOLET LATÉRAL (AUTHENTIFICATION & PROFIL ÉTUDIANT)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.subheader("Mon Compte Étudiant")

    if current_user is not None:
        # 4. Affichage conditionnel : encart profil connecté
        st.success(
            f"Connecté : **{current_user['Prenom']} {current_user['Nom']}**\n\n`{current_user['Email']}`"
        )

        with st.expander("🔒 Modifier mon code PIN", expanded=False):
            with st.form("sidebar_change_pin_form"):
                old_pin_val = st.text_input(
                    "Ancien code PIN", type="password", max_chars=4
                )
                new_pin_val = st.text_input(
                    "Nouveau code PIN (4 chiffres)", type="password", max_chars=4
                )
                confirm_pin_val = st.text_input(
                    "Confirmer le nouveau code PIN", type="password", max_chars=4
                )
                btn_save_new_pin = st.form_submit_button(
                    "Modifier mon code PIN", type="primary", use_container_width=True
                )

                if btn_save_new_pin:
                    o_clean = old_pin_val.strip()
                    n_clean = new_pin_val.strip()
                    c_clean = confirm_pin_val.strip()
                    current_pin = str(current_user.get("PIN", "")).strip().zfill(4)

                    if o_clean != current_pin:
                        st.error("L'ancien code PIN saisi est incorrect.")
                    elif not re.match(r"^\d{4}$", n_clean):
                        st.error("Le nouveau code PIN doit comporter exactement 4 chiffres.")
                    elif n_clean != c_clean:
                        st.error("La confirmation ne correspond pas au nouveau code PIN.")
                    else:
                        if update_user_pin_firestore(
                            current_user["User_ID"], current_user_email, n_clean
                        ):
                            st.session_state["user"]["PIN"] = n_clean
                            st.success("Votre code PIN a été modifié avec succès dans Firestore !")
                            st.rerun()

        # Bouton Se déconnecter qui vide st.session_state et st.query_params avant st.rerun()
        if st.button("Se déconnecter", use_container_width=True, key="btn_sidebar_logout"):
            clear_query_params()
            st.session_state.clear()
            st.session_state["user"] = None
            st.session_state["is_admin"] = False
            st.rerun()

    else:
        # 1. Structure du formulaire : with st.sidebar.form("login_form")
        with st.form("login_form"):
            login_email = st.text_input(
                "Email institutionnel",
                placeholder="prenom.nom@student.uclouvain.be",
                key="login_email_input",
            )
            login_pin = st.text_input(
                "Code PIN (4 chiffres)",
                type="password",
                max_chars=4,
                key="login_pin_input",
            )
            btn_login = st.form_submit_button(
                "Se connecter",
                type="primary",
                use_container_width=True,
            )

            if btn_login:
                em_clean = login_email.strip().lower()
                pin_clean = login_pin.strip()

                if not em_clean or not pin_clean:
                    st.sidebar.error("Email ou code PIN incorrect.")
                else:
                    # 2. Vérification Firestore
                    user_rows = df_utilisateurs[
                        df_utilisateurs["Email"].astype(str).str.strip().str.lower() == em_clean
                    ]

                    # Si pas encore dans le cache, interroger Firestore directement
                    if user_rows.empty:
                        try:
                            db_fs = get_firestore_client()
                            if db_fs:
                                query_u = (
                                    db_fs.collection(COLLECTION_USERS)
                                    .where("Email", "==", em_clean)
                                    .limit(1)
                                    .stream()
                                )
                                for doc_u in query_u:
                                    u_data = doc_u.to_dict() or {}
                                    u_data["User_ID"] = str(u_data.get("User_ID") or doc_u.id).strip()
                                    user_rows = pd.DataFrame([u_data])
                        except Exception:
                            pass

                    if user_rows.empty:
                        st.sidebar.error("Email ou code PIN incorrect.")
                    else:
                        u_row = user_rows.iloc[0]
                        pin_bdd = str(u_row["PIN"]).strip()
                        if pin_bdd.isdigit() and len(pin_bdd) <= 4:
                            pin_bdd = pin_bdd.zfill(4)
                        pin_saisi_norm = pin_clean.zfill(4) if (pin_clean.isdigit() and len(pin_clean) <= 4) else pin_clean

                        # Comparaison sous forme de chaîne de caractères préservant les zéros initiaux
                        if str(pin_saisi_norm) == str(pin_bdd):
                            # 3. Mise à jour de la session et persistance
                            user_session = {
                                "User_ID": str(u_row["User_ID"]).strip(),
                                "Nom": str(u_row["Nom"]).strip(),
                                "Prenom": str(u_row["Prenom"]).strip(),
                                "Email": str(u_row["Email"]).strip().lower(),
                                "PIN": str(pin_bdd),
                            }
                            st.session_state["user"] = user_session
                            st.query_params["auth"] = user_session["Email"]
                            st.sidebar.success(f"Connexion réussie ! Bienvenue {user_session['Prenom']}.")
                            st.rerun()
                        else:
                            st.sidebar.error("Email ou code PIN incorrect.")

        # Accès direct aux options secondaires : Créer un compte & Code PIN oublié
        with st.expander("📝 Pas encore de compte ? Créer un profil", expanded=False):
            with st.form("sidebar_register_form"):
                reg_prenom = st.text_input("Prénom *", key="reg_prenom_input")
                reg_nom = st.text_input("Nom *", key="reg_nom_input")
                reg_email = st.text_input(
                    "Email institutionnel *",
                    placeholder="prenom.nom@student.uclouvain.be",
                    key="reg_email_input",
                )
                reg_pin = st.text_input(
                    "Choisir un Code PIN à 4 chiffres *",
                    type="password",
                    max_chars=4,
                    key="reg_pin_input",
                )
                btn_reg = st.form_submit_button(
                    "Créer mon compte", type="primary", use_container_width=True
                )

                if btn_reg:
                    errs = []
                    p_clean = reg_prenom.strip()
                    n_clean = reg_nom.strip()
                    e_clean = reg_email.strip().lower()
                    pin_c = reg_pin.strip()

                    if len(p_clean) < 2 or len(n_clean) < 2:
                        errs.append("Veuillez renseigner votre Prénom et votre Nom.")
                    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", e_clean):
                        errs.append("Format d'email institutionnel invalide.")
                    if not re.match(r"^\d{4}$", pin_c):
                        errs.append("Le code PIN doit contenir exactement 4 chiffres.")
                    if (
                        not df_utilisateurs.empty
                        and not df_utilisateurs[
                            df_utilisateurs["Email"].astype(str).str.strip().str.lower() == e_clean
                        ].empty
                    ):
                        errs.append("Un compte existe déjà avec cette adresse email.")

                    if errs:
                        for er in errs:
                            st.error(er)
                    else:
                        new_user_dict = {
                            "User_ID": f"USR_{uuid.uuid4().hex[:8].upper()}",
                            "Nom": n_clean,
                            "Prenom": p_clean,
                            "Email": e_clean,
                            "PIN": pin_c.zfill(4),
                            "Date_Inscription": datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                        }
                        if create_user_firestore(new_user_dict):
                            st.session_state["user"] = new_user_dict
                            st.query_params["auth"] = new_user_dict["Email"]
                            st.success("Compte créé avec succès dans Firestore !")
                            st.rerun()

        with st.expander("🔑 Code PIN oublié ?", expanded=False):
            st.caption("Recevez immédiatement votre code PIN sur votre adresse email institutionnelle.")
            with st.form("sidebar_forgot_pin_form"):
                forgot_email_input = st.text_input(
                    "Entrez votre adresse email étudiante",
                    placeholder="prenom.nom@student.uclouvain.be",
                    key="forgot_email_input",
                )
                btn_send_forgot_pin = st.form_submit_button(
                    "M'envoyer mon code PIN", use_container_width=True
                )

                if btn_send_forgot_pin:
                    fem_clean = forgot_email_input.strip().lower()
                    if not fem_clean:
                        st.error("Veuillez entrer votre adresse email.")
                    else:
                        matched_users = df_utilisateurs[
                            df_utilisateurs["Email"].astype(str).str.strip().str.lower() == fem_clean
                        ]
                        if matched_users.empty:
                            st.warning("Aucun compte associé à cette adresse email.")
                        else:
                            u_target = matched_users.iloc[0]
                            pin_to_send = str(u_target["PIN"]).strip().zfill(4)
                            prenom_to_send = str(u_target.get("Prenom", "")).strip() or "étudiant"
                            try:
                                send_pin_recovery_email(
                                    fem_clean, prenom_to_send, pin_to_send
                                )
                                st.success(
                                    f"Votre code PIN a été envoyé avec succès à l'adresse {fem_clean} !"
                                )
                            except Exception as err:
                                st.error(
                                    f"Impossible d'envoyer l'email de récupération : {err}"
                                )

    st.divider()
    st.markdown(
        """
        <div style="text-align: center; color: #94a3b8; font-size: 0.8rem; padding: 0.5rem 0;">
            Développé par Imrane Machbaête
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# 10. CENTRE DE NOTIFICATIONS (EN HAUT À DROITE)
# ---------------------------------------------------------------------------
_, header_col_right = st.columns([3, 1])

with header_col_right:
    nb_notifs = len(mes_notifications)
    with st.expander(f"🔔 Notifications ({nb_notifs})", expanded=False):
        if current_user is None:
            st.caption("Connectez-vous à votre compte étudiant pour voir vos alertes d'échange.")
        elif nb_notifs == 0:
            st.caption("Aucune nouvelle notification pour le moment.")
        else:
            for n_item in mes_notifications:
                st.markdown(
                    f"""
                    <div class="notif-card">
                        <div style="font-size: 0.82rem; font-weight: 700; color: #1e3a8a;">
                            {n_item['titre']}
                        </div>
                        <div style="font-size: 0.78rem; color: #334155; margin-top: 0.2rem;">
                            {n_item['detail']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

# Espace Administrateur débloqué si authentifié en session
if st.session_state.get("is_admin", False):
    with st.expander("🛠️ Espace Administrateur (Supervision globale & Statistiques)", expanded=True):
        col_adm_head, col_adm_logout = st.columns([4, 1])
        with col_adm_head:
            st.markdown("### 🛠️ Espace Administrateur Débloqué")
            st.caption("Supervision complète des offres, gestion des collections Firestore et statistiques de promotion.")
        with col_adm_logout:
            if st.button("🔒 Verrouiller l'accès", use_container_width=True, help="Quitter le mode administrateur"):
                st.session_state["is_admin"] = False
                st.rerun()

        # 1. Indicateurs et Statistiques de la plateforme
        st.markdown("#### 📊 Statistiques de la plateforme")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1:
            st.metric("Comptes étudiants", len(df_utilisateurs))
        with kpi2:
            st.metric("Offres actives déposées", len(df_demandes))
        with kpi3:
            st.metric("Matchs directs binômes", len(all_matchs_binomes))
        with kpi4:
            st.metric("Boucles triangulaires", len(all_matchs_triangulaires))

        # 2. Vue globale sur l'ensemble des demandes & Export CSV
        st.markdown("#### 📋 Vue globale sur la collection `demandes`")
        csv_bytes = df_demandes.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Télécharger l'état complet des demandes (.CSV)",
            data=csv_bytes,
            file_name=f"permutstage_demandes_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )
        st.dataframe(df_demandes, use_container_width=True, hide_index=True)

        # 3. Gestion des collections
        st.markdown("#### ⚙️ Gestion des collections Firestore & Suppression administrative")
        adm_t1, adm_t2, adm_t3 = st.tabs(["Supprimer une demande", "Collection users", "Collection messages"])
        with adm_t1:
            if not df_demandes.empty:
                st.caption("Suppression administrative directe d'un document Firestore (sans code PIN).")
                options_suppression = [
                    f"{row['Demande_ID']} | {row['Periode']} - {row['Specialite']} | {row['Nom']} ({row['Email']}) — {row['Hopital_Actuel']}"
                    for _, row in df_demandes.iterrows()
                ]
                choix_admin_del = st.selectbox(
                    "Sélectionner l'annonce à supprimer", options=options_suppression, key="admin_del_select_box"
                )
                if st.button("Supprimer définitivement cette offre (Admin)", type="primary", key="btn_admin_del_submit"):
                    id_to_drop = choix_admin_del.split(" | ")[0].strip()
                    if delete_demande_firestore(id_to_drop):
                        st.success(f"Annonce {id_to_drop} supprimée avec succès de Firestore.")
                        st.rerun()
            else:
                st.info("Aucune annonce active dans la collection des demandes.")

        with adm_t2:
            st.dataframe(df_utilisateurs, use_container_width=True, hide_index=True)
            if not df_utilisateurs.empty:
                st.markdown("---")
                st.markdown("##### 🗑️ Suppression d'un utilisateur (Admin)")
                st.caption(
                    "Cette action supprime le compte de la collection 'users' et supprime également en cascade toutes les offres liées à cet email dans la collection 'demandes'."
                )
                options_user_del = [
                    f"{row['User_ID']} | {row['Prenom']} {row['Nom']} ({row['Email']})"
                    for _, row in df_utilisateurs.iterrows()
                ]
                choix_user_del = st.selectbox(
                    "Sélectionner l'utilisateur à supprimer",
                    options=options_user_del,
                    key="admin_del_user_select_box",
                )
                confirm_del_user = st.checkbox(
                    "Je confirme vouloir supprimer définitivement cet utilisateur et toutes ses offres associées",
                    key="confirm_del_user_check",
                )
                if st.button(
                    "Supprimer définitivement cet utilisateur (Admin)",
                    type="primary",
                    key="btn_admin_del_user_submit",
                    disabled=not confirm_del_user,
                ):
                    uid_to_drop = choix_user_del.split(" | ")[0].strip()
                    if delete_user_firestore(uid_to_drop):
                        st.success(f"Utilisateur {uid_to_drop} et ses demandes ont été supprimés avec succès.")
                        st.rerun()
            else:
                st.info("Aucun utilisateur enregistré dans la collection 'users'.")

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
# ONGLET 0 : ACCUEIL CHALEUREUX, GUIDE & RÈGLES DU CONCEPT TEST
# ===========================================================================
with tab0:
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-badge">
                ✨ PROMOTION MÉDECINE 2028 · MASTER 2
            </div>
            <h1>
                Trouvez votre binôme de stage idéal en quelques clics
            </h1>
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

    # Boutons d'accès rapide rétablis
    col_act1, col_act2, col_act3 = st.columns(3)
    with col_act1:
        if st.button("📝 Déposer une demande", key="btn_hero_deposer", type="primary", use_container_width=True):
            st.components.v1.html(
                """
                <script>
                const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
                if (tabs && tabs.length > 1) {
                    tabs[1].click();
                }
                </script>
                """,
                height=0,
            )
    with col_act2:
        if st.button(f"🎯 Voir mes correspondances ({nb_mes_matchs})", key="btn_hero_matchs", type="secondary", use_container_width=True):
            st.components.v1.html(
                """
                <script>
                const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
                if (tabs && tabs.length > 2) {
                    tabs[2].click();
                }
                </script>
                """,
                height=0,
            )
    with col_act3:
        if st.button(f"🔍 Consulter toutes les offres ({len(df_demandes)})", key="btn_hero_offres", type="secondary", use_container_width=True):
            st.components.v1.html(
                """
                <script>
                const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
                if (tabs && tabs.length > 3) {
                    tabs[3].click();
                }
                </script>
                """,
                height=0,
            )
    st.write("")

    # Fonctionnement pas-à-pas
    st.subheader("🧭 Comment ça marche ? (Le parcours en 4 étapes simples)")
    col_e1, col_e2, col_e3, col_e4 = st.columns(4)

    with col_e1:
        st.markdown(
            """
            <div class="step-card">
                <div style="width: 32px; height: 32px; border-radius: 8px; background-color: #dbeafe; color: #1e40af; font-weight: 800; display: flex; align-items: center; justify-content: center; margin-bottom: 0.5rem;">1</div>
                <strong style="color: #0f172a; font-size: 0.95rem;">Créer son profil (30s)</strong>
                <p style="color: #475569; font-size: 0.82rem; margin-top: 0.35rem; line-height: 1.4;">
                    Renseignez vos nom, prénom, email institutionnel et un <strong>code PIN à 4 chiffres</strong>.
                    Pas de mot de passe complexe à mémoriser.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_e2:
        st.markdown(
            """
            <div class="step-card">
                <div style="width: 32px; height: 32px; border-radius: 8px; background-color: #e0e7ff; color: #3730a3; font-weight: 800; display: flex; align-items: center; justify-content: center; margin-bottom: 0.5rem;">2</div>
                <strong style="color: #0f172a; font-size: 0.95rem;">Déposer son offre</strong>
                <p style="color: #475569; font-size: 0.82rem; margin-top: 0.35rem; line-height: 1.4;">
                    Indiquez votre stage actuel (période P3 à P8, spécialité, hôpital) et sélectionnez vos <strong>hôpitaux souhaités</strong> par région.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_e3:
        st.markdown(
            """
            <div class="step-card">
                <div style="width: 32px; height: 32px; border-radius: 8px; background-color: #f3e8ff; color: #6b21a8; font-weight: 800; display: flex; align-items: center; justify-content: center; margin-bottom: 0.5rem;">3</div>
                <strong style="color: #0f172a; font-size: 0.95rem;">Calcul des matchs</strong>
                <p style="color: #475569; font-size: 0.82rem; margin-top: 0.35rem; line-height: 1.4;">
                    L'algorithme détecte en continu les <strong>échanges directs à deux (A ↔ B)</strong> ou les <strong>boucles triangulaires (A → B → C → A)</strong>.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_e4:
        st.markdown(
            """
            <div class="step-card">
                <div style="width: 32px; height: 32px; border-radius: 8px; background-color: #dcfce7; color: #166534; font-weight: 800; display: flex; align-items: center; justify-content: center; margin-bottom: 0.5rem;">4</div>
                <strong style="color: #0f172a; font-size: 0.95rem;">Échanger en privé</strong>
                <p style="color: #475569; font-size: 0.82rem; margin-top: 0.35rem; line-height: 1.4;">
                    Dès qu'un cycle se forme, une notification cloche et un <strong>email d'alerte</strong> s'activent pour ouvrir votre salon privé sécurisé.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    col_regles, col_rgpd = st.columns(2)

    with col_regles:
        st.subheader("⚖️ Les Règles & Conditions d'Échange")
        st.markdown(
            """
            * **Même période obligatoire :** Une permutation n'est possible qu'au sein d'une même tranche chronologique (ex. P3 contre P3, P4 contre P4).
            * **Même spécialité obligatoire :** Condition sine qua non : Pédiatrie contre Pédiatrie, Chirurgie contre Chirurgie, etc. Seul l'hôpital d'affectation change.
            * **Validation facultaire ultérieure :** PermutStage permet de trouver et finaliser un accord mutuel de principe. Une fois votre binôme ou triangle confirmé dans le salon privé, la démarche officielle auprès de la **coordination / commission des stages** demeure requise selon le règlement facultaire.
            """
        )

    with col_rgpd:
        st.subheader("🔒 Confidentialité & Respect de la Vie Privée")
        st.markdown(
            """
            * **Authentification minimale par code PIN :** Pas de stockage de mots de passe complexes. Vos coordonnées sont protégées par votre email institutionnel et un PIN personnel à 4 chiffres.
            * **Minimisation stricte des données :** Seules les informations strictement indispensables à la logistique de permutation sont traitées.
            * **Matching 100 % privé et hermétique :** Les autres camarades de promotion ne voient **jamais** qui permute avec qui. Seuls les étudiants directement concernés par un cycle complet ont accès aux coordonnées et aux salons de discussion.
            """
        )

    st.write("")
    st.divider()

    st.markdown("### 🚀 Prêt(e) à trouver votre permutation ?")
    c_btn1, c_btn2, _ = st.columns([1.5, 1.5, 3])
    with c_btn1:
        if current_user is None:
            st.info("👈 Créez votre profil ou connectez-vous dans la barre latérale pour démarrer.")
        else:
            st.success(f"Connecté en tant que {current_user['Prenom']} {current_user['Nom']}. Déposez votre offre dans l'onglet 1 !")

# ===========================================================================
# ONGLET 1 : DÉPOSER UNE DEMANDE (COORDONNÉES VERROUILLÉES SUR LE COMPTE)
# ===========================================================================
with tab1:
    st.subheader("Déposer une nouvelle demande de permutation")

    if current_user is None:
        st.warning(
            "🔒 Veuillez vous connecter ou créer un compte étudiant dans le menu latéral gauche pour déposer une demande de permutation."
        )
    else:
        nom_complet_verrouille = f"{current_user['Prenom']} {current_user['Nom']}".strip()
        email_verrouille = current_user["Email"].strip().lower()

        st.markdown("##### Sélection géographique par région")
        reg_col1, reg_col2 = st.columns(2)
        with reg_col1:
            region_actuel_filtre = st.selectbox(
                "Filtrer la liste de l'hôpital actuel par région",
                options=["Toutes les régions"] + REGIONS,
            )
        with reg_col2:
            regions_souhaitees_auto = st.multiselect(
                "Pré-sélectionner tous les hôpitaux souhaités d'une ou plusieurs régions",
                options=REGIONS,
            )

        options_hopital_actuel = (
            TOUS_LES_HOPITAUX
            if region_actuel_filtre == "Toutes les régions"
            else HOPITAUX_PAR_REGION[region_actuel_filtre]
        )

        hopitaux_preselectionnes = []
        for reg in regions_souhaitees_auto:
            for h in HOPITAUX_PAR_REGION[reg]:
                if h not in hopitaux_preselectionnes:
                    hopitaux_preselectionnes.append(h)

        with st.form("form_depot_demande", clear_on_submit=False):
            col1, col2 = st.columns(2)
            with col1:
                st.text_input(
                    "Nom & Prénom (verrouillé sur votre profil)",
                    value=nom_complet_verrouille,
                    disabled=True,
                )
                st.text_input(
                    "Email institutionnel (verrouillé sur votre profil)",
                    value=email_verrouille,
                    disabled=True,
                )

            with col2:
                periode = st.selectbox("Période de stage *", options=PERIODES)
                specialite = st.selectbox("Spécialité *", options=SPECIALITES)
                hopital_actuel = st.selectbox(
                    "Hôpital actuel *", options=options_hopital_actuel
                )

            defaut_souhaites = [
                h for h in hopitaux_preselectionnes if h != hopital_actuel
            ]

            hopitaux_souhaites = st.multiselect(
                "Hôpitaux souhaités *",
                options=TOUS_LES_HOPITAUX,
                default=defaut_souhaites,
                format_func=lambda h: f"[{HOPITAL_VERS_REGION.get(h, '')}] {h}",
            )

            submitted = st.form_submit_button(
                "Publier ma demande de permutation",
                type="primary",
                use_container_width=True,
            )

            if submitted:
                erreurs = []
                if not hopitaux_souhaites:
                    erreurs.append("Veuillez sélectionner au moins un hôpital souhaité.")
                elif hopital_actuel in hopitaux_souhaites:
                    erreurs.append(
                        "Validation refusée : votre hôpital actuel ne peut pas figurer dans la liste des hôpitaux souhaités."
                    )

                if not df_demandes.empty:
                    doublon = df_demandes[
                        (df_demandes["Email"].str.lower() == email_verrouille)
                        & (df_demandes["Periode"] == periode)
                    ]
                    if not doublon.empty:
                        erreurs.append(
                            f"Vous avez déjà une demande active sur la période {periode}. "
                            "Modifiez-la ou supprimez-la dans l'onglet 'Gérer mon offre'."
                        )

                if erreurs:
                    for err in erreurs:
                        st.error(err)
                else:
                    anciens_rooms = {
                        m["room_id"] for m in all_matchs_binomes
                    } | {t["room_id"] for t in all_matchs_triangulaires}

                    nouvelle_demande_dict = {
                        "Demande_ID": f"DEM_{uuid.uuid4().hex[:10].upper()}",
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Nom": nom_complet_verrouille,
                        "Email": email_verrouille,
                        "PIN": str(current_user.get("PIN", "")).strip(),
                        "Periode": periode,
                        "Specialite": specialite,
                        "Hopital_Actuel": hopital_actuel,
                        "Hopitaux_Souhaites": serialize_hospitals(hopitaux_souhaites),
                    }

                    if add_demande_firestore(nouvelle_demande_dict):
                        df_maj = pd.concat(
                            [df_demandes, pd.DataFrame([nouvelle_demande_dict])],
                            ignore_index=True,
                        )
                        trigger_new_match_emails(
                            anciens_rooms=anciens_rooms,
                            df_demandes_maj=df_maj,
                            df_utilisateurs=df_utilisateurs,
                            df_messages=df_messages,
                        )

                        st.success(
                            f"Votre demande pour la période {periode} ({specialite}) a été publiée avec succès !"
                        )
                        st.rerun()

# ===========================================================================
# ONGLET 2 : MATCHS DISPONIBLES & SALONS PRIVÉS (CONFIDENTIALITÉ STRICTE)
# ===========================================================================
with tab2:
    st.subheader("Mes correspondances privées & Salons de discussion")

    if current_user is None:
        st.info(
            "🔒 **Confidentialité stricte des échanges** : Vous devez être connecté à votre compte étudiant "
            "pour visualiser vos propositions d'échange et accéder à vos salons de discussion privés. "
            "Aucun étudiant tiers ne peut voir les échanges des autres."
        )
    else:
        st.caption(
            f"Affichage strictement filtré pour **{current_user['Prenom']} {current_user['Nom']}** (`{current_user['Email']}`). "
            "Seuls les binômes et cycles à 3 dont vous faites partie intégrante apparaissent ici."
        )

        col_bi, col_tri = st.columns(2)

        with col_bi:
            st.markdown(
                f"### Mes Échanges Bilatéraux — Binômes ({len(mes_matchs_binomes)})"
            )
            if not mes_matchs_binomes:
                st.info("Aucun match bilatéral ne vous concerne actuellement.")
            else:
                for m in mes_matchs_binomes:
                    a, b = m["a"], m["b"]
                    st.markdown(
                        f"""
                        <div class="match-card">
                            <div style="font-weight: 700; color: #166534; margin-bottom: 0.4rem;">
                                MATCH PRIVÉ BILATÉRAL · {m['periode']} · {m['specialite']}
                            </div>
                            <p style="margin: 0.25rem 0;">
                                <strong>{a['Nom']}</strong> ({a['Hopital_Actuel']})
                                &nbsp;&lt;-&gt;&nbsp;
                                <strong>{b['Nom']}</strong> ({b['Hopital_Actuel']})
                            </p>
                            <p style="margin: 0.4rem 0 0 0; font-size: 0.85rem; color: #15803d;">
                                Coordonnées réservées aux participants :
                                <a href="mailto:{a['Email']}">{a['Email']}</a> |
                                <a href="mailto:{b['Email']}">{b['Email']}</a>
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    render_private_chat_room(
                        room_id=m["room_id"],
                        current_user=current_user,
                        df_messages=df_messages,
                        label_expander=f"Salon privé binôme ({m['periode']} · {m['specialite']})",
                    )

        with col_tri:
            st.markdown(
                f"### Mes Salons Triangulaires — Cycles à 3 ({len(mes_matchs_triangulaires)})"
            )
            if not mes_matchs_triangulaires:
                st.info("Aucun cycle triangulaire à 3 personnes ne vous concerne actuellement.")
            else:
                for t in mes_matchs_triangulaires:
                    a, b, c = t["a"], t["b"], t["c"]
                    st.markdown(
                        f"""
                        <div class="tri-card">
                            <div style="font-weight: 700; color: #065f46; margin-bottom: 0.4rem;">
                                MATCH PRIVÉ TRIANGULAIRE · {t['periode']} · {t['specialite']}
                            </div>
                            <p style="margin: 0.35rem 0; font-size: 0.92rem; line-height: 1.5;">
                                <strong>{a['Nom']}</strong> ({a['Hopital_Actuel']})
                                &nbsp;-&gt;&nbsp;
                                <strong>{b['Nom']}</strong> ({b['Hopital_Actuel']})
                                &nbsp;-&gt;&nbsp;
                                <strong>{c['Nom']}</strong> ({c['Hopital_Actuel']})
                                &nbsp;-&gt;&nbsp;
                                <strong>{a['Nom']}</strong>
                            </p>
                            <p style="margin: 0.4rem 0 0 0; font-size: 0.85rem; color: #047857;">
                                Coordonnées réservées au cycle :
                                <a href="mailto:{a['Email']}">{a['Email']}</a> ·
                                <a href="mailto:{b['Email']}">{b['Email']}</a> ·
                                <a href="mailto:{c['Email']}">{c['Email']}</a>
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    render_private_chat_room(
                        room_id=t["room_id"],
                        current_user=current_user,
                        df_messages=df_messages,
                        label_expander=f"Salon privé triangulaire ({t['periode']} · {t['specialite']})",
                    )

# ===========================================================================
# ONGLET 3 : CONSULTER TOUTES LES OFFRES (ANONYMISÉES PAR CONFIDENTIALITÉ)
# ===========================================================================
with tab3:
    st.subheader("Catalogue des offres de stage disponibles")
    st.caption(
        "Pour garantir la confidentialité des échanges, seuls les lieux de stage proposés et souhaités sont affichés publiquement. "
        "Les identités et adresses email ne sont révélées qu'en cas de match mutuel dans votre onglet privé."
    )

    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    with f_col1:
        filtre_periode = st.selectbox(
            "Filtrer par Période", options=["Toutes"] + PERIODES
        )
    with f_col2:
        filtre_specialite = st.selectbox(
            "Filtrer par Spécialité", options=["Toutes"] + SPECIALITES
        )
    with f_col3:
        filtre_region = st.selectbox(
            "Filtrer par Région (Hôpital actuel)", options=["Toutes"] + REGIONS
        )
    with f_col4:
        filtre_recherche = st.text_input(
            "Recherche par hôpital", placeholder="Ex. Saint Luc, Citadelle..."
        )

    df_filtre = df_demandes.copy()
    if filtre_periode != "Toutes":
        df_filtre = df_filtre[df_filtre["Periode"] == filtre_periode]
    if filtre_specialite != "Toutes":
        df_filtre = df_filtre[df_filtre["Specialite"] == filtre_specialite]
    if filtre_region != "Toutes":
        hopitaux_reg = set(HOPITAUX_PAR_REGION[filtre_region])
        df_filtre = df_filtre[df_filtre["Hopital_Actuel"].isin(hopitaux_reg)]
    if filtre_recherche.strip():
        q = filtre_recherche.strip().lower()
        df_filtre = df_filtre[
            df_filtre["Hopital_Actuel"].str.lower().str.contains(q, na=False)
            | df_filtre["Hopitaux_Souhaites"].str.lower().str.contains(q, na=False)
        ]

    if df_filtre.empty:
        st.info("Aucune offre ne correspond aux critères sélectionnés.")
    else:
        for _, row in df_filtre.iterrows():
            souhaites_liste = ", ".join(parse_hospitals(row["Hopitaux_Souhaites"]))
            region_act = HOPITAL_VERS_REGION.get(row["Hopital_Actuel"], "Autre")
            st.markdown(
                f"""
                <div class="offer-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; color:#1e3a8a;">
                            {row['Periode']} · {row['Specialite']} — Région {region_act}
                        </span>
                        <span style="font-size:0.8rem; color:#64748b;">
                            Mise à jour : {row['Timestamp']}
                        </span>
                    </div>
                    <div style="margin-top:0.4rem; font-size:0.9rem;">
                        <strong>Hôpital actuel proposé :</strong> {row['Hopital_Actuel']}<br/>
                        <strong>Hôpitaux souhaités :</strong> {souhaites_liste}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ===========================================================================
# ONGLET 4 : GÉRER MON OFFRE (MODIFICATION PRÉ-REMPLIE & SUPPRESSION SÉCURISÉE)
# ===========================================================================
with tab4:
    st.subheader("Gérer mes annonces publiées (Modification & Suppression)")

    if current_user is None:
        st.warning(
            "🔒 Connectez-vous à votre compte étudiant dans le menu latéral pour modifier ou supprimer vos offres."
        )
    else:
        mes_offres_mask = df_demandes["Email"].str.lower() == current_user_email
        df_mes_offres = df_demandes[mes_offres_mask]

        if df_mes_offres.empty:
            st.info(
                "Vous n'avez aucune annonce active pour le moment. Rendez-vous dans l'onglet '1. Déposer une demande'."
            )
        else:
            for idx, row in df_mes_offres.iterrows():
                demande_id_courante = str(row["Demande_ID"]).strip()
                periode_courante = row["Periode"]
                spec_courante = row["Specialite"]
                hop_actuel_courant = row["Hopital_Actuel"]
                souhaites_courants = [
                    h
                    for h in parse_hospitals(row["Hopitaux_Souhaites"])
                    if h in TOUS_LES_HOPITAUX
                ]

                with st.expander(
                    f"📌 Période {periode_courante} · {spec_courante} — Actuel : {hop_actuel_courant} (ID: {demande_id_courante})",
                    expanded=True,
                ):
                    col_edit, col_del = st.columns([2, 1])

                    # OPTION 1 : MODIFIER L'ANNONCE
                    with col_edit:
                        st.markdown("##### Option 1 : Modifier l'annonce")
                        with st.form(f"edit_form_{demande_id_courante}"):
                            new_periode = st.selectbox(
                                "Période",
                                options=PERIODES,
                                index=PERIODES.index(periode_courante)
                                if periode_courante in PERIODES
                                else 0,
                                key=f"edit_per_{demande_id_courante}",
                            )
                            new_spec = st.selectbox(
                                "Spécialité",
                                options=SPECIALITES,
                                index=SPECIALITES.index(spec_courante)
                                if spec_courante in SPECIALITES
                                else 0,
                                key=f"edit_spec_{demande_id_courante}",
                            )
                            new_hop_actuel = st.selectbox(
                                "Hôpital actuel",
                                options=TOUS_LES_HOPITAUX,
                                index=TOUS_LES_HOPITAUX.index(hop_actuel_courant)
                                if hop_actuel_courant in TOUS_LES_HOPITAUX
                                else 0,
                                key=f"edit_act_{demande_id_courante}",
                            )
                            new_souhaites = st.multiselect(
                                "Hôpitaux souhaités",
                                options=TOUS_LES_HOPITAUX,
                                default=souhaites_courants,
                                format_func=lambda h: f"[{HOPITAL_VERS_REGION.get(h, '')}] {h}",
                                key=f"edit_wish_{demande_id_courante}",
                            )
                            btn_save_edit = st.form_submit_button(
                                "Enregistrer les modifications",
                                type="primary",
                                use_container_width=True,
                            )

                            if btn_save_edit:
                                edit_errs = []
                                if not new_souhaites:
                                    edit_errs.append(
                                        "Veuillez conserver au moins un hôpital souhaité."
                                    )
                                elif new_hop_actuel in new_souhaites:
                                    edit_errs.append(
                                        "L'hôpital actuel ne peut pas faire partie des hôpitaux souhaités."
                                    )

                                # Vérifier unicité si changement de période
                                if new_periode != periode_courante:
                                    conflit = df_demandes[
                                        (df_demandes["Demande_ID"] != demande_id_courante)
                                        & (
                                            df_demandes["Email"].str.lower()
                                            == current_user_email
                                        )
                                        & (df_demandes["Periode"] == new_periode)
                                    ]
                                    if not conflit.empty:
                                        edit_errs.append(
                                            f"Vous avez déjà une autre offre sur la période {new_periode}."
                                        )

                                if edit_errs:
                                    for e in edit_errs:
                                        st.error(e)
                                else:
                                    anciens_rooms_avant_modif = {
                                        m["room_id"] for m in all_matchs_binomes
                                    } | {
                                        t["room_id"] for t in all_matchs_triangulaires
                                    }

                                    update_data = {
                                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "Periode": new_periode,
                                        "Specialite": new_spec,
                                        "Hopital_Actuel": new_hop_actuel,
                                        "Hopitaux_Souhaites": serialize_hospitals(new_souhaites),
                                    }

                                    if update_demande_firestore(demande_id_courante, update_data):
                                        df_maj = df_demandes.copy()
                                        mask = df_maj["Demande_ID"] == demande_id_courante
                                        for k, v in update_data.items():
                                            df_maj.loc[mask, k] = v

                                        trigger_new_match_emails(
                                            anciens_rooms=anciens_rooms_avant_modif,
                                            df_demandes_maj=df_maj,
                                            df_utilisateurs=df_utilisateurs,
                                            df_messages=df_messages,
                                        )
                                        st.success(
                                            "Votre annonce a été mise à jour avec succès dans Firestore !"
                                        )
                                        st.rerun()

                    # OPTION 2 : SUPPRIMER L'ANNONCE AVEC CONFIRMATION EXPLICITE
                    with col_del:
                        st.markdown("##### Option 2 : Supprimer l'annonce")
                        st.caption(
                            "Cette action retirera définitivement votre offre de la base Firestore et fermera les salons associés."
                        )
                        confirm_check = st.checkbox(
                            "Je confirme vouloir supprimer définitivement cette offre",
                            key=f"confirm_del_{demande_id_courante}",
                        )
                        if st.button(
                            "Confirmer la suppression",
                            key=f"btn_del_{demande_id_courante}",
                            type="secondary",
                            disabled=not confirm_check,
                            use_container_width=True,
                        ):
                            if delete_demande_firestore(demande_id_courante):
                                st.success(
                                    f"Votre offre pour la période {periode_courante} a été supprimée de Firestore."
                                )
                                st.rerun()

    # -----------------------------------------------------------------------
    # ACCÈS ADMINISTRATEUR DISCRET (TOUT EN BAS À DROITE DE L'ONGLET)
    # -----------------------------------------------------------------------
    st.write("")
    st.write("")
    col_spacer, col_secret = st.columns([12, 1])
    with col_secret:
        if not st.session_state.get("is_admin", False):
            if hasattr(st, "dialog"):
                if st.button("🔒", key="btn_secret_admin_lock", help="Accès restreint"):
                    dialog_admin_login()
            else:
                with st.expander("🔒", expanded=False):
                    with st.form("form_secret_admin_fallback"):
                        secret_in = st.text_input(
                            "Code secret Administrateur", type="password"
                        )
                        if st.form_submit_button("Déverrouiller"):
                            if check_admin_password(secret_in):
                                st.session_state["is_admin"] = True
                                st.success("Accès Administrateur accordé !")
                                st.rerun()
                            else:
                                st.error("Accès refusé.")
        else:
            if st.button(
                "🔓",
                key="btn_secret_admin_unlock",
                help="Mode Administrateur activé (cliquer pour verrouiller)",
            ):
                st.session_state["is_admin"] = False
                st.rerun()


# ---------------------------------------------------------------------------
# 12. PIED DE PAGE (FOOTER GLOBAL)
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #64748b; font-size: 0.82rem; padding: 1.25rem 0 0.5rem 0;">
        Plateforme conçue et développée par <strong>Imrane Machbaête</strong> — Version Alpha
    </div>
    """,
    unsafe_allow_html=True,
)
