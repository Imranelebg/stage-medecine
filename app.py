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
- Mode d'affichage clair strict verrouillé (accessibilité permanente de la sidebar)

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

    /* Badges multiselects sélectionnés */
    [data-baseweb="tag"] {
        background-color: #e2e8f0 !important;
        color: #0f172a !important;
        border-radius: 6px !important;
    }

    [data-baseweb="tag"] span {
        color: #0f172a !important;
    }

    /* Boutons de commande */
    button[kind="primary"],
    .stButton > button[type="submit"] {
        background-color: #1d4ed8 !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 600 !important;
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
       3. CARTE D'EN-TÊTE BLEU NUIT / DÉGRADÉ SOMBRE (HERO BANNER)
       Style préservé explicitement avec contraste blanc/or garanti
       ========================================================================== */
    .hero-banner {
        background: linear-gradient(135deg, #1e3a8a 0%, #172554 100%) !important;
        color: #ffffff !important;
        padding: 2rem 2.2rem !important;
        border-radius: 14px !important;
        margin-bottom: 1.5rem !important;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.12) !important;
    }

    .hero-banner * {
        color: #ffffff;
    }

    .hero-banner h1 {
        color: #ffffff !important;
        font-size: 2rem !important;
        font-weight: 800 !important;
        line-height: 1.2 !important;
        margin: 0 0 0.5rem 0 !important;
    }

    .hero-banner p {
        color: #e2e8f0 !important;
        font-size: 1rem !important;
        line-height: 1.6 !important;
        margin: 0 0 1.25rem 0 !important;
        max-width: 850px !important;
    }

    .hero-banner p strong {
        color: #ffffff !important;
    }

    .hero-banner .hero-badge {
        display: inline-block !important;
        padding: 0.25rem 0.75rem !important;
        background: rgba(59, 130, 246, 0.25) !important;
        border: 1px solid rgba(147, 197, 253, 0.35) !important;
        border-radius: 9999px !important;
        font-size: 0.78rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.05em !important;
        color: #bfdbfe !important;
        margin-bottom: 0.75rem !important;
    }

    .hero-banner .hero-alpha-box {
        background: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 10px !important;
        padding: 0.9rem 1.1rem !important;
        font-size: 0.88rem !important;
        color: #f8fafc !important;
        line-height: 1.5 !important;
    }

    .hero-banner .hero-alpha-box strong {
        color: #fde047 !important;
    }

    .hero-banner .hero-alpha-box em {
        color: #ffffff !important;
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
        "CHU HELORA - Hôpital de Warquignies",
        "CHU HELORA - Pôle Hospitalier Jolimont Lobbes",
        "CHU HELORA - Pôle Hospitalier Mons-Borinage",
        "Clinique Notre Dame de Grâce - Gosselies",
        "Grand Hôpital de Charleroi (Les Viviers)",
        "Hôpital de Jour Pédiatrique La Traversée (Manage)",
        "Hôpital de Warquignies",
        "Hôpital Psychiatrique Saint Jean de Dieu (Leuze-en-Hainaut)",
    ],
    "Luxembourg": [
        "Centre Hospitalier de l'Ardenne - Libramont",
        "Clinique d'Arlon (Vivalia)",
    ],
    "Liège": [
        "Centre Hospitalier Peltzer La Tourelle - Verviers",
        "CHR Verviers East Belgium",
        "Clinique CHC Hermalle",
        "Clinique CHC Heusy",
        "Clinique CHC MontLégia",
        "Clinique CHC Waremme",
    ],
    "Flandre": [
        "Algemeen Ziekenhuis Sint-Jan Brugge-Oostende AV",
        "AZ Groeninge - Courtrai",
        "AZ Sint-Elisabeth - Zottegem",
        "AZ Sint-Lucas - Gand",
    ],
}

HOPITAL_VERS_REGION = {}
for reg, hops in HOPITAUX_PAR_REGION.items():
    for h in hops:
        HOPITAL_VERS_REGION[h] = reg

COLLECTION_USERS = "users"
COLLECTION_DEMANDES = "demandes"
COLLECTION_MESSAGES = "messages"

COLUMNS_DEMANDES = [
    "Demande_ID",
    "Timestamp",
    "Nom",
    "Email",
    "Periode",
    "Specialite",
    "Hopital_Actuel",
    "Hopitaux_Souhaites",
]

COLUMNS_MESSAGES = ["Message_ID", "Room_ID", "Timestamp", "Auteur", "Texte"]

COLUMNS_UTILISATEURS = ["User_ID", "Nom", "Prenom", "Email", "PIN", "Date_Inscription"]

DEMANDES_INITIALES_MOCK = [
    {
        "Demande_ID": "DEM_INIT_001",
        "Timestamp": "2025-05-10 10:15:00",
        "Nom": "Camille Vandenberghe",
        "Email": "camille.vandenberghe@student.uclouvain.be",
        "Periode": "P3",
        "Specialite": "Pédiatrie",
        "Hopital_Actuel": "Cliniques Universitaires Saint Luc",
        "Hopitaux_Souhaites": "Clinique Saint Jean - Bruxelles | Centre Hospitalier Sambre & Meuse - Site Meuse",
    },
    {
        "Demande_ID": "DEM_INIT_002",
        "Timestamp": "2025-05-10 11:20:00",
        "Nom": "Alexandre Dupont",
        "Email": "alexandre.dupont@student.uclouvain.be",
        "Periode": "P3",
        "Specialite": "Pédiatrie",
        "Hopital_Actuel": "Clinique Saint Jean - Bruxelles",
        "Hopitaux_Souhaites": "Cliniques Universitaires Saint Luc | Clinique Saint Pierre - Ottignies",
    },
    {
        "Demande_ID": "DEM_INIT_003",
        "Timestamp": "2025-05-11 09:00:00",
        "Nom": "Sarah Benali",
        "Email": "sarah.benali@student.uclouvain.be",
        "Periode": "P4",
        "Specialite": "Chirurgie",
        "Hopital_Actuel": "Clinique Saint Pierre - Ottignies",
        "Hopitaux_Souhaites": "CHIREC - Clinique Sainte Anne - Saint Remi | CHIREC - Hôpital Braine-l'Alleud",
    },
    {
        "Demande_ID": "DEM_INIT_004",
        "Timestamp": "2025-05-11 14:45:00",
        "Nom": "Lucas Martin",
        "Email": "lucas.martin@student.uclouvain.be",
        "Periode": "P4",
        "Specialite": "Chirurgie",
        "Hopital_Actuel": "CHIREC - Clinique Sainte Anne - Saint Remi",
        "Hopitaux_Souhaites": "CHU UCL NAMUR - Site Mont-Godinne (Yvoir) | Clinique Saint Luc - Bouge",
    },
    {
        "Demande_ID": "DEM_INIT_005",
        "Timestamp": "2025-05-12 08:30:00",
        "Nom": "Emma Lambert",
        "Email": "emma.lambert@student.uclouvain.be",
        "Periode": "P4",
        "Specialite": "Chirurgie",
        "Hopital_Actuel": "CHU UCL NAMUR - Site Mont-Godinne (Yvoir)",
        "Hopitaux_Souhaites": "Clinique Saint Pierre - Ottignies | CHIREC - Hôpital Braine-l'Alleud",
    },
]

USERS_INITIAUX_MOCK = [
    {
        "User_ID": "USR_001",
        "Nom": "Vandenberghe",
        "Prenom": "Camille",
        "Email": "camille.vandenberghe@student.uclouvain.be",
        "PIN": "1234",
        "Date_Inscription": "2025-05-01 10:00:00",
    },
    {
        "User_ID": "USR_002",
        "Nom": "Dupont",
        "Prenom": "Alexandre",
        "Email": "alexandre.dupont@student.uclouvain.be",
        "PIN": "5678",
        "Date_Inscription": "2025-05-01 11:30:00",
    },
    {
        "User_ID": "USR_003",
        "Nom": "Benali",
        "Prenom": "Sarah",
        "Email": "sarah.benali@student.uclouvain.be",
        "PIN": "4321",
        "Date_Inscription": "2025-05-02 09:15:00",
    },
    {
        "User_ID": "USR_004",
        "Nom": "Martin",
        "Prenom": "Lucas",
        "Email": "lucas.martin@student.uclouvain.be",
        "PIN": "8765",
        "Date_Inscription": "2025-05-02 14:00:00",
    },
    {
        "User_ID": "USR_005",
        "Nom": "Lambert",
        "Prenom": "Emma",
        "Email": "emma.lambert@student.uclouvain.be",
        "PIN": "2468",
        "Date_Inscription": "2025-05-03 16:45:00",
    },
]

MESSAGES_INITIAUX_MOCK = [
    {
        "Message_ID": "MSG_001",
        "Room_ID": "ROOM_P3_PEDIATRIE_2B8F1A",
        "Timestamp": "2025-05-10 11:30:00",
        "Auteur": "Camille Vandenberghe",
        "Texte": "Bonjour Alexandre ! J'ai vu que notre échange P3 Pédiatrie matchait. Tu confirmes ?",
    },
    {
        "Message_ID": "MSG_002",
        "Room_ID": "ROOM_P3_PEDIATRIE_2B8F1A",
        "Timestamp": "2025-05-10 11:35:00",
        "Auteur": "Alexandre Dupont",
        "Texte": "Salut Camille ! Oui absolument, Saint-Luc m'arrange beaucoup mieux géographiquement.",
    },
]


# ---------------------------------------------------------------------------
# 3. GESTION DES REQUÊTES D'URL (PERSISTANCE DE SESSION st.query_params)
# ---------------------------------------------------------------------------
def get_auth_query_param() -> str | None:
    try:
        val = st.query_params.get("auth", None)
        if isinstance(val, list):
            return val[0] if val else None
        return val
    except Exception:
        return None


def clear_query_params():
    try:
        st.query_params.clear()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 4. INITIALISATION PROTÉGÉE DE FIREBASE FIRESTORE (firebase-admin)
# ---------------------------------------------------------------------------
@st.cache_resource
def init_firestore_client():
    if "firebase" not in st.secrets:
        return None
    try:
        if not firebase_admin._apps:
            firebase_creds_dict = dict(st.secrets["firebase"])
            if "private_key" in firebase_creds_dict:
                firebase_creds_dict["private_key"] = firebase_creds_dict[
                    "private_key"
                ].replace("\\n", "\n")
            cred = credentials.Certificate(firebase_creds_dict)
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as exc:
        st.sidebar.warning(f"Connexion Firestore non active ({exc}). Mode mémoire local engagé.")
        return None


def get_firestore_client():
    return init_firestore_client()


# ---------------------------------------------------------------------------
# 5. CACHE ET LECTURES HAUTE PERFORMANCE FIRESTORE (ttl=15s)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=15, show_spinner=False)
def load_users_data() -> pd.DataFrame:
    db = get_firestore_client()
    if db is not None:
        try:
            docs = db.collection(COLLECTION_USERS).stream()
            records = []
            for d in docs:
                data = d.to_dict() or {}
                data["User_ID"] = str(data.get("User_ID") or d.id).strip()
                data["PIN"] = str(data.get("PIN", "")).strip()
                records.append(data)
            if records:
                df = pd.DataFrame(records)
                for col in COLUMNS_UTILISATEURS:
                    if col not in df.columns:
                        df[col] = ""
                return df[COLUMNS_UTILISATEURS]
        except Exception:
            pass
    return pd.DataFrame(USERS_INITIAUX_MOCK)


@st.cache_data(ttl=15, show_spinner=False)
def load_demandes_data() -> pd.DataFrame:
    db = get_firestore_client()
    if db is not None:
        try:
            docs = db.collection(COLLECTION_DEMANDES).stream()
            records = []
            for d in docs:
                data = d.to_dict() or {}
                data["Demande_ID"] = str(data.get("Demande_ID") or d.id).strip()
                records.append(data)
            if records:
                df = pd.DataFrame(records)
                for col in COLUMNS_DEMANDES:
                    if col not in df.columns:
                        df[col] = ""
                return df[COLUMNS_DEMANDES]
        except Exception:
            pass
    return pd.DataFrame(DEMANDES_INITIALES_MOCK)


@st.cache_data(ttl=15, show_spinner=False)
def load_messages_data() -> pd.DataFrame:
    db = get_firestore_client()
    if db is not None:
        try:
            docs = db.collection(COLLECTION_MESSAGES).stream()
            records = []
            for d in docs:
                data = d.to_dict() or {}
                data["Message_ID"] = str(data.get("Message_ID") or d.id).strip()
                records.append(data)
            if records:
                df = pd.DataFrame(records)
                for col in COLUMNS_MESSAGES:
                    if col not in df.columns:
                        df[col] = ""
                return df[COLUMNS_MESSAGES]
        except Exception:
            pass
    return pd.DataFrame(MESSAGES_INITIAUX_MOCK)


# ---------------------------------------------------------------------------
# 6. ÉCRITURES ATOMIQUES DIRECTES ET INVALIDATION DU CACHE
# ---------------------------------------------------------------------------
def create_user_firestore(user_dict: dict) -> bool:
    user_id = str(user_dict.get("User_ID") or f"USR_{uuid.uuid4().hex[:8].upper()}")
    user_dict["User_ID"] = user_id
    user_dict["Email"] = user_dict["Email"].strip().lower()
    user_dict["PIN"] = str(user_dict.get("PIN", "")).strip()

    db = get_firestore_client()
    if db is not None:
        try:
            db.collection(COLLECTION_USERS).document(user_id).set(user_dict)
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Erreur d'écriture Firestore (users) : {e}")
            return False

    global USERS_INITIAUX_MOCK
    USERS_INITIAUX_MOCK.append(user_dict)
    st.cache_data.clear()
    return True


def update_user_pin_firestore(user_id: str, email: str, new_pin: str) -> bool:
    clean_pin = str(new_pin).strip().zfill(4)
    db = get_firestore_client()
    if db is not None:
        try:
            if user_id:
                db.collection(COLLECTION_USERS).document(str(user_id)).update({"PIN": clean_pin})
            else:
                q = (
                    db.collection(COLLECTION_USERS)
                    .where("Email", "==", email.strip().lower())
                    .limit(1)
                    .stream()
                )
                for doc in q:
                    doc.reference.update({"PIN": clean_pin})
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Erreur lors de la mise à jour du code PIN : {e}")
            return False

    global USERS_INITIAUX_MOCK
    for u in USERS_INITIAUX_MOCK:
        if u["Email"].lower() == email.strip().lower():
            u["PIN"] = clean_pin
            break
    st.cache_data.clear()
    return True


def create_demande_firestore(demande_dict: dict) -> bool:
    demande_id = str(demande_dict.get("Demande_ID") or f"DEM_{uuid.uuid4().hex[:8].upper()}")
    demande_dict["Demande_ID"] = demande_id
    demande_dict["Email"] = demande_dict["Email"].strip().lower()

    db = get_firestore_client()
    if db is not None:
        try:
            db.collection(COLLECTION_DEMANDES).document(demande_id).set(demande_dict)
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Erreur d'écriture Firestore (demandes) : {e}")
            return False

    global DEMANDES_INITIALES_MOCK
    DEMANDES_INITIALES_MOCK.append(demande_dict)
    st.cache_data.clear()
    return True


def update_demande_firestore(demande_id: str, payload: dict) -> bool:
    db = get_firestore_client()
    if db is not None:
        try:
            db.collection(COLLECTION_DEMANDES).document(str(demande_id)).update(payload)
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Erreur de mise à jour Firestore (demandes) : {e}")
            return False

    global DEMANDES_INITIALES_MOCK
    for d in DEMANDES_INITIALES_MOCK:
        if d.get("Demande_ID") == demande_id:
            d.update(payload)
            break
    st.cache_data.clear()
    return True


def delete_demande_firestore(demande_id: str) -> bool:
    db = get_firestore_client()
    if db is not None:
        try:
            db.collection(COLLECTION_DEMANDES).document(str(demande_id)).delete()
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Erreur de suppression Firestore : {e}")
            return False

    global DEMANDES_INITIALES_MOCK
    DEMANDES_INITIALES_MOCK = [
        d for d in DEMANDES_INITIALES_MOCK if d.get("Demande_ID") != demande_id
    ]
    st.cache_data.clear()
    return True


def send_message_firestore(room_id: str, auteur: str, texte: str) -> bool:
    msg_id = f"MSG_{uuid.uuid4().hex[:8].upper()}"
    msg_dict = {
        "Message_ID": msg_id,
        "Room_ID": room_id,
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Auteur": auteur,
        "Texte": texte,
    }
    db = get_firestore_client()
    if db is not None:
        try:
            db.collection(COLLECTION_MESSAGES).document(msg_id).set(msg_dict)
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Erreur d'envoi du message : {e}")
            return False

    global MESSAGES_INITIAUX_MOCK
    MESSAGES_INITIAUX_MOCK.append(msg_dict)
    st.cache_data.clear()
    return True


# ---------------------------------------------------------------------------
# 7. SERVICE DE NOTIFICATIONS EMAIL VIA SMTP (st.secrets['smtp'])
# ---------------------------------------------------------------------------
def send_email_via_smtp(to_email: str, subject: str, body_content: str):
    if "smtp" not in st.secrets:
        return
    cfg = st.secrets["smtp"]
    server_host = cfg.get("server", "smtp.gmail.com")
    server_port = int(cfg.get("port", 587))
    smtp_user = cfg.get("email")
    smtp_pass = cfg.get("password")

    msg = MIMEText(body_content, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = f"PermutStage <{smtp_user}>"
    msg["To"] = to_email

    with smtplib.SMTP(server_host, server_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


def send_match_notification_emails(match_item: dict, match_type: str = "bilateral"):
    if "notified_rooms" not in st.session_state:
        st.session_state["notified_rooms"] = set()

    room_id = match_item.get("room_id")
    if not room_id or room_id in st.session_state["notified_rooms"]:
        return

    periode = match_item.get("periode", "")
    specialite = match_item.get("specialite", "")

    if match_type == "bilateral":
        a = match_item["a"]
        b = match_item["b"]
        participants = [a, b]
        subject = f"[PermutStage] MATCH TROUVÉ ! Échange disponible en {periode} - {specialite}"
    else:
        a = match_item["a"]
        b = match_item["b"]
        c = match_item["c"]
        participants = [a, b, c]
        subject = f"[PermutStage] CYCLE TRIANGULAIRE TROUVÉ ! Échange en {periode} - {specialite}"

    for p in participants:
        email_dest = p.get("Email", "").strip().lower()
        nom_dest = p.get("Nom", "Étudiant")
        if not email_dest:
            continue

        body = (
            f"Bonjour {nom_dest},\n\n"
            f"Bonne nouvelle ! Une permutation de stage ({match_type.upper()}) vient d'être détectée sur PermutStage "
            f"pour la période {periode} en {specialite}.\n\n"
            f"Connectez-vous avec votre code PIN pour ouvrir votre salon de discussion privé sécurisé :\n"
            f"https://permutstage-uclouvain.streamlit.app\n\n"
            f"À bientôt sur PermutStage.\n"
        )
        try:
            send_email_via_smtp(email_dest, subject, body)
        except Exception:
            pass

    st.session_state["notified_rooms"].add(room_id)


def send_pin_recovery_email(to_email: str, prenom: str, pin: str):
    subject = "[PermutStage] Récupération de votre code PIN étudiant"
    body = (
        f"Bonjour {prenom},\n\n"
        f"Vous avez demandé le rappel de votre code PIN de connexion à la plateforme PermutStage.\n\n"
        f"Votre code PIN à 4 chiffres est : {pin}\n\n"
        f"Vous pouvez dès à présent l'utiliser dans la barre latérale pour accéder à votre profil, vos annonces et vos salons privés :\n"
        f"https://permutstage-uclouvain.streamlit.app\n\n"
        f"À bientôt sur PermutStage.\n"
    )
    send_email_via_smtp(to_email, subject, body)


# ---------------------------------------------------------------------------
# 8. MOTEUR ALGORITHMIQUE DE MATCHING (BILATÉRAL & TRIANGULAIRE)
# ---------------------------------------------------------------------------
def parse_hospitals(raw_str) -> list[str]:
    if not raw_str or pd.isna(raw_str):
        return []
    parts = re.split(r"[\|\,\;\n]+", str(raw_str))
    cleaned = [p.strip() for p in parts if p.strip()]
    return list(dict.fromkeys(cleaned))


def serialize_hospitals(hospital_list: list[str]) -> str:
    cleaned = [h.strip() for h in hospital_list if h.strip()]
    return " | ".join(dict.fromkeys(cleaned))


def build_room_id(periode: str, specialite: str, emails: list[str]) -> str:
    clean_emails = sorted([e.strip().lower() for e in emails])
    unique_hash = uuid.uuid5(uuid.NAMESPACE_DNS, "_".join(clean_emails)).hex[:8].upper()
    spec_clean = re.sub(r"[^A-Z0-9]+", "", specialite.upper())[:10]
    return f"ROOM_{periode.upper()}_{spec_clean}_{unique_hash}"


def find_bilateral_matches(df_demandes: pd.DataFrame) -> list[dict]:
    if df_demandes.empty:
        return []
    records = df_demandes.to_dict(orient="records")
    n = len(records)
    matches = []
    seen_pairs = set()

    souhaites_map = [set(parse_hospitals(r.get("Hopitaux_Souhaites", ""))) for r in records]

    for i in range(n):
        for j in range(i + 1, n):
            a = records[i]
            b = records[j]

            if a["Email"].strip().lower() == b["Email"].strip().lower():
                continue
            if a["Periode"] != b["Periode"] or a["Specialite"] != b["Specialite"]:
                continue
            if a["Hopital_Actuel"] == b["Hopital_Actuel"]:
                continue

            # Vérification réciproque bilatérale stricte
            if (
                b["Hopital_Actuel"] in souhaites_map[i]
                and a["Hopital_Actuel"] in souhaites_map[j]
            ):
                id_a = f"{a['Email'].lower()}_{a['Periode']}"
                id_b = f"{b['Email'].lower()}_{b['Periode']}"
                pair_key = tuple(sorted([id_a, id_b]))

                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
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


def find_triangular_matches(df_demandes: pd.DataFrame) -> list[dict]:
    if df_demandes.empty:
        return []
    records = df_demandes.to_dict(orient="records")
    n = len(records)
    matches = []
    seen_cycles = set()

    souhaites_map = [set(parse_hospitals(r.get("Hopitaux_Souhaites", ""))) for r in records]

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            a = records[i]
            b = records[j]

            if a["Periode"] != b["Periode"] or a["Specialite"] != b["Specialite"]:
                continue
            if a["Hopital_Actuel"] == b["Hopital_Actuel"]:
                continue
            if b["Hopital_Actuel"] not in souhaites_map[i]:
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


def render_private_chat_room(
    room_id: str,
    current_user: dict | None,
    df_messages: pd.DataFrame,
    label_expander: str,
):
    with st.expander(f"💬 {label_expander}", expanded=True):
        if not current_user:
            st.info("🔒 Connectez-vous avec votre code PIN pour participer à ce salon privé.")
            return

        room_msgs = df_messages[df_messages["Room_ID"] == room_id]
        if not room_msgs.empty:
            room_msgs = room_msgs.sort_values(by="Timestamp", ascending=True)
            for _, m_row in room_msgs.iterrows():
                is_me = m_row["Auteur"].strip() == current_user["Nom"].strip()
                avatar_symb = "🧑‍⚕️" if is_me else "🩺"
                role_label = f"Moi ({m_row['Auteur']})" if is_me else m_row["Auteur"]
                with st.chat_message(name=m_row["Auteur"], avatar=avatar_symb):
                    st.markdown(f"**{role_label}** &nbsp;·&nbsp; _{m_row['Timestamp']}_")
                    st.write(m_row["Texte"])
        else:
            st.caption("Ce salon privé vient d'être ouvert. Envoyez le premier message pour lancer l'échange !")

        # Formulaire d'envoi du message privé
        with st.form(key=f"chat_form_{room_id}", clear_on_submit=True):
            user_msg = st.text_input(
                "Votre message aux co-permutants",
                placeholder="Ex : Bonjour ! Je confirme mon souhait de permuter pour Saint-Luc. Êtes-vous toujours d'accord ?",
                key=f"chat_input_{room_id}",
            )
            btn_send = st.form_submit_button(
                "Envoyer dans le salon privé",
                type="primary",
                use_container_width=True,
            )
            if btn_send:
                t_clean = user_msg.strip()
                if not t_clean:
                    st.warning("Veuillez saisir un texte avant d'envoyer.")
                else:
                    auteur_nom = f"{current_user.get('Prenom', '')} {current_user.get('Nom', '')}".strip()
                    if send_message_firestore(room_id, auteur_nom, t_clean):
                        st.rerun()


# ---------------------------------------------------------------------------
# CHARGEMENT DES COLLECTIONS DEPUIS FIRESTORE & DÉTECTION DES CYCLES
# ---------------------------------------------------------------------------
df_utilisateurs = load_users_data()
df_demandes = load_demandes_data()
df_messages = load_messages_data()

# Reconnexion automatique et transparente si 'auth' est présent dans l'URL (F5 / réveil smartphone)
auth_token = get_auth_query_param()
if auth_token and st.session_state.get("user") is None:
    target_clean = auth_token.strip().lower()
    matched_row = pd.DataFrame()
    if not df_utilisateurs.empty:
        matched_row = df_utilisateurs[
            df_utilisateurs["Email"].astype(str).str.strip().str.lower() == target_clean
        ]
    if matched_row.empty:
        try:
            db_fs = get_firestore_client()
            if db_fs:
                query_res = (
                    db_fs.collection(COLLECTION_USERS)
                    .where("Email", "==", target_clean)
                    .limit(1)
                    .stream()
                )
                for doc in query_res:
                    doc_dict = doc.to_dict() or {}
                    doc_dict["User_ID"] = str(doc_dict.get("User_ID") or doc.id).strip()
                    matched_row = pd.DataFrame([doc_dict])
        except Exception:
            pass

    if not matched_row.empty:
        u_data = matched_row.iloc[0]
        st.session_state["user"] = {
            "User_ID": str(u_data.get("User_ID", "")).strip(),
            "Nom": str(u_data.get("Nom", "")).strip(),
            "Prenom": str(u_data.get("Prenom", "")).strip(),
            "Email": str(u_data.get("Email", "")).strip().lower(),
            "PIN": str(u_data.get("PIN", "")).strip(),
        }

current_user = st.session_state.get("user", None)
current_user_email = current_user["Email"].strip().lower() if current_user else None

# Calcul des correspondances et filtrage strict confidentiel
all_matches_bi = find_bilateral_matches(df_demandes)
all_matches_tri = find_triangular_matches(df_demandes)

# Envoi automatique d'emails d'alerte SMTP lors de la création de nouveaux cycles (Option A)
for m_bi in all_matches_bi:
    send_match_notification_emails(m_bi, match_type="bilateral")
for m_tri in all_matches_tri:
    send_match_notification_emails(m_tri, match_type="triangulaire")

mes_matchs_binomes, mes_matchs_triangulaires = filter_private_matches_for_user(
    current_user_email, all_matches_bi, all_matches_tri
)

# Construction des alertes pour la cloche de notifications
mes_notifications = []
if current_user:
    total_m = len(mes_matchs_binomes) + len(mes_matchs_triangulaires)
    if total_m > 0:
        mes_notifications.append(
            {
                "titre": f"🎉 {total_m} cycle(s) de permutation disponible(s) !",
                "detail": f"Vous avez {len(mes_matchs_binomes)} binôme(s) direct(s) et {len(mes_matchs_triangulaires)} boucle(s) triangulaire(s). Rendez-vous dans l'onglet 'Matchs' !",
            }
        )
    mes_rooms_ids = {m["room_id"] for m in mes_matchs_binomes} | {
        t["room_id"] for t in mes_matchs_triangulaires
    }
    if not df_messages.empty and mes_rooms_ids:
        msgs_de_mes_salons = df_messages[df_messages["Room_ID"].isin(mes_rooms_ids)]
        mon_nom = current_user["Nom"].strip()
        autres_msgs = msgs_de_mes_salons[msgs_de_mes_salons["Auteur"].str.strip() != mon_nom]
        if not autres_msgs.empty:
            derniers = autres_msgs.tail(3)
            for _, r_m in derniers.iterrows():
                mes_notifications.append(
                    {
                        "titre": f"💬 Nouveau message de {r_m['Auteur']}",
                        "detail": f"« {r_m['Texte'][:60]}... »",
                    }
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

    # Accès Administrateur discret
    with st.expander("🛠️ Administration plateforme", expanded=False):
        if st.session_state.get("is_admin", False):
            st.success("Accès administrateur actif.")
            if st.button("Se déconnecter de l'administration", use_container_width=True):
                st.session_state["is_admin"] = False
                st.rerun()
        else:
            admin_pwd = st.text_input(
                "Mot de passe administrateur",
                type="password",
                key="admin_pwd_input",
            )
            if st.button("Valider l'accès", use_container_width=True, key="btn_admin_login"):
                expected_pwd = (
                    st.secrets.get("admin", {}).get("password", "SecretAdmin2025!")
                    if "admin" in st.secrets
                    else "SecretAdmin2025!"
                )
                if admin_pwd == expected_pwd:
                    st.session_state["is_admin"] = True
                    st.success("Accès accordé !")
                    st.rerun()
                else:
                    st.error("Mot de passe administrateur incorrect.")

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
# 10. EN-TÊTE PRINCIPAL & CENTRE DE NOTIFICATIONS (EN HAUT À DROITE)
# ---------------------------------------------------------------------------
header_col_left, header_col_right = st.columns([3, 1])

with header_col_left:
    st.markdown(
        """
        <div class="permut-banner">
            <h1 style="margin: 0; font-size: 1.65rem; font-weight: 700; color: #0f172a;">
                PermutStage — Permutation de Stages de Médecine (P3 à P8)
            </h1>
            <p style="margin: 0.35rem 0 0 0; font-size: 0.92rem; color: #475569;">
                Base de données haute performance Firebase Firestore · Confidentialité stricte des échanges et messagerie privée.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        kpi_col1.metric("Étudiants Inscrits", len(df_utilisateurs))
        kpi_col2.metric("Offres Déposées", len(df_demandes))
        kpi_col3.metric("Matchs Binômes", len(all_matches_bi))
        kpi_col4.metric("Cycles Triangulaires", len(all_matches_tri))

        # 2. Table complète des demandes avec export CSV
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
        <div class="hero-banner" style="background: linear-gradient(135deg, #1E3A8A 0%, #172554 100%) !important; color: #FFFFFF !important; padding: 2rem 2.2rem; border-radius: 14px; margin-bottom: 1.5rem; box-shadow: 0 4px 14px rgba(15, 23, 42, 0.12);">
            <div class="hero-badge" style="display: inline-block; padding: 0.25rem 0.75rem; background: rgba(59, 130, 246, 0.25); border: 1px solid rgba(147, 197, 253, 0.35); border-radius: 9999px; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.05em; color: #BFDBFE !important; margin-bottom: 0.75rem;">
                ✨ PROMOTION MÉDECINE 2028 · MASTER 2
            </div>
            <h1 style="color: #FFFFFF !important; margin: 0 0 0.5rem 0; font-size: 2rem; font-weight: 800; line-height: 1.2;">
                Trouvez votre binôme de stage idéal en quelques clics
            </h1>
            <p style="color: #E2E8F0 !important; margin: 0 0 1.25rem 0; font-size: 1rem; line-height: 1.6; max-width: 850px;">
                Bienvenue sur <strong style="color: #FFFFFF !important;">PermutStage</strong>, la plateforme pensée pour fluidifier, simplifier et centraliser
                les échanges de lieux de stages hospitaliers entre camarades de promotion. Vos souhaits sont analysés
                en temps réel par notre algorithme de permutation, dans le respect le plus strict de votre confidentialité.
            </p>
            <div class="hero-alpha-box" style="background: rgba(255, 255, 255, 0.1) !important; border: 1px solid rgba(255, 255, 255, 0.2) !important; border-radius: 10px; padding: 0.9rem 1.1rem; font-size: 0.88rem; color: #F8FAFC !important; line-height: 1.5;">
                <strong style="color: #FDE047 !important;">🤝 Statut du projet : Version Alpha / Concept Test</strong><br/>
                Cette plateforme est une initiative bénévole conçue <em style="color: #FFFFFF !important;">par et pour les étudiants</em>. Merci pour votre
                bienveillance et vos retours constructifs pour faire évoluer l'outil au service de toute la promotion !
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
        st.subheader("🛡️ Confidentialité & Sécurité des Données")
        st.markdown(
            """
            * **Anonymat du catalogue public :** Dans l'onglet 3 (« Consulter toutes les offres »), seules les informations relatives au stage (Période, Spécialité, Région, Hôpitaux) sont affichées. Les noms, prénoms et adresses email sont masqués.
            * **Salons de discussion hermétiques :** Seuls les étudiants directement concernés par un match bilatéral ou triangulaire ont accès au salon de chat et peuvent consulter les coordonnées de contact de leurs co-permutants.
            * **Authentification simplifiée & PIN :** Chaque compte est sécurisé par un code PIN à 4 chiffres, évitant toute modification non autorisée de vos annonces.
            """
        )


# ===========================================================================
# ONGLET 1 : DÉPOSER UNE NOUVELLE DEMANDE DE PERMUTATION
# ===========================================================================
with tab1:
    st.subheader("Publier une offre de permutation de stage")

    if current_user is None:
        st.warning(
            "🔒 Vous devez être connecté à votre compte étudiant pour soumettre une offre. "
            "Renseignez votre email et code PIN dans le menu latéral à gauche."
        )
    else:
        st.info(
            f"Offre rattachée à : **{current_user['Prenom']} {current_user['Nom']}** (`{current_user['Email']}`)."
        )

        with st.form("form_nouvelle_demande", clear_on_submit=False):
            st.markdown("#### 1. Votre affectation actuelle")
            col_d1, col_d2, col_d3 = st.columns(3)

            with col_d1:
                demande_periode = st.selectbox(
                    "Période de stage *",
                    options=PERIODES,
                    index=0,
                    help="La permutation n'est possible qu'entre étudiants de même période.",
                )
            with col_d2:
                demande_spe = st.selectbox(
                    "Spécialité médicale *",
                    options=SPECIALITES,
                    index=0,
                    help="La spécialité doit être strictement identique entre permutants.",
                )
            with col_d3:
                demande_reg_actuelle = st.selectbox(
                    "Région de l'hôpital actuel *",
                    options=list(HOPITAUX_PAR_REGION.keys()),
                    index=0,
                )

            hopitaux_actuels_dispos = HOPITAUX_PAR_REGION[demande_reg_actuelle]
            demande_hopital_actuel = st.selectbox(
                f"Hôpital où vous êtes actuellement affecté ({demande_reg_actuelle}) *",
                options=hopitaux_actuels_dispos,
            )

            st.markdown("---")
            st.markdown("#### 2. Vos souhaits d'échange (Où souhaitez-vous aller ?)")
            st.caption(
                "Vous pouvez sélectionner un ou plusieurs hôpitaux cibles à travers plusieurs régions."
            )

            regions_selectionnees = st.multiselect(
                "Filtrer les régions souhaitées",
                options=list(HOPITAUX_PAR_REGION.keys()),
                default=[demande_reg_actuelle],
                help="Sélectionnez les régions qui vous intéressent pour afficher la liste des hôpitaux correspondants.",
            )

            pool_hopitaux_souhaites = []
            for r in regions_selectionnees:
                pool_hopitaux_souhaites.extend(HOPITAUX_PAR_REGION[r])
            pool_hopitaux_souhaites = [
                h for h in pool_hopitaux_souhaites if h != demande_hopital_actuel
            ]

            demande_hopitaux_cibles = st.multiselect(
                "Hôpitaux souhaités *",
                options=pool_hopitaux_souhaites,
                default=[],
                help="Plus vous cochez d'hôpitaux acceptables, plus vos chances de matching immédiat sont élevées.",
            )

            btn_submit_demande = st.form_submit_button(
                "🚀 Publier mon offre de permutation",
                type="primary",
                use_container_width=True,
            )

            if btn_submit_demande:
                errors = []
                if not demande_hopitaux_cibles:
                    errors.append(
                        "Veuillez sélectionner au moins un hôpital souhaité pour l'échange."
                    )
                if demande_hopital_actuel in demande_hopitaux_cibles:
                    errors.append(
                        "L'hôpital souhaité ne peut pas être votre hôpital actuel."
                    )

                # Vérifier qu'une offre n'existe pas déjà pour cet étudiant sur la même période
                deja_present = df_demandes[
                    (df_demandes["Email"].str.lower() == current_user_email)
                    & (df_demandes["Periode"] == demande_periode)
                ]
                if not deja_present.empty:
                    errors.append(
                        f"Vous avez déjà une offre enregistrée pour la période {demande_periode}. "
                        "Modifiez-la ou supprimez-la dans l'onglet 'Gérer mon offre'."
                    )

                if errors:
                    for err in errors:
                        st.error(err)
                else:
                    nouvelle_demande = {
                        "Demande_ID": f"DEM_{uuid.uuid4().hex[:8].upper()}",
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Nom": f"{current_user['Prenom']} {current_user['Nom']}",
                        "Email": current_user_email,
                        "Periode": demande_periode,
                        "Specialite": demande_spe,
                        "Hopital_Actuel": demande_hopital_actuel,
                        "Hopitaux_Souhaites": serialize_hospitals(demande_hopitaux_cibles),
                    }
                    if create_demande_firestore(nouvelle_demande):
                        st.success(
                            "🎉 Votre offre a été enregistrée avec succès dans Firebase Firestore ! "
                            "L'algorithme de matching a recalculé les correspondances en temps réel."
                        )
                        st.rerun()


# ===========================================================================
# ONGLET 2 : MATCHS DISPONIBLES & SALONS PRIVÉS (CONFIDENTIALITÉ STRICTE)
# ===========================================================================
with tab2:
    st.subheader("Mes Correspondances de Permutation & Salons de Discussion")

    if current_user is None:
        st.warning(
            "🔒 **Confidentialité stricte :** Les correspondances bilatérales et triangulaires, "
            "ainsi que les salons de discussion privés ne sont accessibles qu'aux étudiants authentifiés. "
            "Connectez-vous via le menu latéral avec votre adresse email et votre code PIN."
        )
    else:
        st.markdown(
            f"Espace d'échange privé réservé à : **{current_user['Prenom']} {current_user['Nom']}**."
        )

        col_bi, col_tri = st.columns(2)

        with col_bi:
            st.markdown(
                f"### Mes Salons Bilatéraux — Binômes directs ({len(mes_matchs_binomes)})"
            )
            if not mes_matchs_binomes:
                st.info("Aucun binôme direct trouvé pour le moment. Déposez une offre ou élargissez vos hôpitaux cibles.")
            else:
                for m in mes_matchs_binomes:
                    a, b = m["a"], m["b"]
                    st.markdown(
                        f"""
                        <div class="match-card">
                            <div style="font-weight: 700; color: #166534; margin-bottom: 0.4rem;">
                                MATCH PRIVÉ BINÔME DIRECT · {m['periode']} · {m['specialite']}
                            </div>
                            <p style="margin: 0.35rem 0; font-size: 0.92rem; line-height: 1.5;">
                                <strong>{a['Nom']}</strong> ({a['Hopital_Actuel']})
                                &nbsp;&lt;---&gt;&nbsp;
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
    st.subheader("Catalogue Public des Annonces Déposées (Anonymisé)")
    st.caption(
        "Conformément aux règles de confidentialité, l'identité des étudiants et leurs emails ne sont pas affichés publiquement. "
        "Les coordonnées ne sont débloquées que dans les salons privés dès qu'un match direct ou triangulaire est formé."
    )

    col_f1, col_f2, col_f3, col_f4 = st.columns([1, 1, 1, 2])
    with col_f1:
        filtre_periode = st.selectbox(
            "Période", options=["Toutes"] + PERIODES, key="filtre_per_tab3"
        )
    with col_f2:
        filtre_specialite = st.selectbox(
            "Spécialité", options=["Toutes"] + SPECIALITES, key="filtre_spe_tab3"
        )
    with col_f3:
        filtre_region = st.selectbox(
            "Région hôpital actuel",
            options=["Toutes"] + list(HOPITAUX_PAR_REGION.keys()),
            key="filtre_reg_tab3",
        )
    with col_f4:
        filtre_recherche = st.text_input(
            "Recherche libre (Hôpital)",
            placeholder="Ex: Saint-Luc, Namur, Dinant...",
            key="filtre_search_tab3",
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
                "Vous n'avez actuellement aucune offre active enregistrée. "
                "Utilisez l'onglet '1. Déposer une demande' pour publier votre première offre de stage !"
            )
        else:
            options_offres = [
                f"{r['Demande_ID']} | {r['Periode']} - {r['Specialite']} ({r['Hopital_Actuel']})"
                for _, r in df_mes_offres.iterrows()
            ]
            choix_offre_str = st.selectbox(
                "Sélectionnez l'offre à administrer",
                options=options_offres,
                key="select_mes_offres",
            )
            demande_id_sel = choix_offre_str.split(" | ")[0].strip()
            row_sel = df_mes_offres[df_mes_offres["Demande_ID"] == demande_id_sel].iloc[0]

            col_edit, col_delete = st.columns([2, 1])

            with col_edit:
                st.markdown("#### ✏️ Modifier mes souhaits d'hôpitaux cibles")
                st.caption(
                    "Vous pouvez à tout moment ajouter ou retirer des hôpitaux souhaités pour déclencher de nouveaux matchs."
                )

                region_actuelle_offre = HOPITAL_VERS_REGION.get(
                    row_sel["Hopital_Actuel"], list(HOPITAUX_PAR_REGION.keys())[0]
                )
                souhaites_actuels = parse_hospitals(row_sel["Hopitaux_Souhaites"])

                with st.form(key=f"form_edit_{demande_id_sel}"):
                    st.text_input(
                        "Période & Spécialité (Non modifiable)",
                        value=f"{row_sel['Periode']} — {row_sel['Specialite']}",
                        disabled=True,
                    )
                    st.text_input(
                        "Votre hôpital actuel (Non modifiable)",
                        value=f"{row_sel['Hopital_Actuel']} ({region_actuelle_offre})",
                        disabled=True,
                    )

                    regions_mod = st.multiselect(
                        "Filtrer les régions cibles",
                        options=list(HOPITAUX_PAR_REGION.keys()),
                        default=list(HOPITAUX_PAR_REGION.keys()),
                        key=f"regions_mod_{demande_id_sel}",
                    )

                    pool_mod = []
                    for reg in regions_mod:
                        pool_mod.extend(HOPITAUX_PAR_REGION[reg])
                    pool_mod = [h for h in pool_mod if h != row_sel["Hopital_Actuel"]]

                    # Nettoyage des options par défaut pour correspondre au pool disponible
                    def_souhaites = [h for h in souhaites_actuels if h in pool_mod]

                    nouveaux_souhaites = st.multiselect(
                        "Sélectionnez vos hôpitaux souhaités *",
                        options=pool_mod,
                        default=def_souhaites,
                        key=f"multi_mod_{demande_id_sel}",
                    )

                    btn_save_modif = st.form_submit_button(
                        "💾 Enregistrer les modifications",
                        type="primary",
                        use_container_width=True,
                    )

                    if btn_save_modif:
                        if not nouveaux_souhaites:
                            st.error("Veuillez sélectionner au moins un hôpital souhaité.")
                        else:
                            up_payload = {
                                "Hopitaux_Souhaites": serialize_hospitals(nouveaux_souhaites),
                                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            }
                            if update_demande_firestore(demande_id_sel, up_payload):
                                st.success("Vos souhaits ont été mis à jour avec succès dans Firestore !")
                                st.rerun()

            with col_delete:
                st.markdown("#### 🗑️ Supprimer cette offre")
                st.caption(
                    "Action irréversible. Pour sécuriser la suppression, veuillez entrer votre code PIN étudiant."
                )

                with st.form(key=f"form_del_{demande_id_sel}"):
                    pin_confirm = st.text_input(
                        "Code PIN de confirmation",
                        type="password",
                        max_chars=4,
                        key=f"pin_del_{demande_id_sel}",
                    )
                    btn_supprimer = st.form_submit_button(
                        "Supprimer mon offre",
                        type="secondary",
                        use_container_width=True,
                    )

                    if btn_supprimer:
                        clean_pin_c = pin_confirm.strip()
                        current_pin = str(current_user.get("PIN", "")).strip().zfill(4)

                        if clean_pin_c != current_pin:
                            st.error("Code PIN incorrect. Suppression refusée.")
                        else:
                            if delete_demande_firestore(demande_id_sel):
                                st.success("Votre annonce a été supprimée définitivement de Firestore.")
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
