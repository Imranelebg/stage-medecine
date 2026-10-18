"""
PermutStage — Plateforme Collaborative d'Échange de Lieux de Stage (Médecine P3 à P8)
Architecture complète :
- Comptes Étudiants (Feuille 'Utilisateurs' + st.session_state['user'])
- Confidentialité stricte des échanges (Matching Privé réservé aux étudiants impliqués)
- Centre de Notifications dynamique en haut à droite + Onglet Alertes
- Alertes Email automatiques via SMTP (smtplib + email.mime + st.secrets['smtp'])
- Récupération de code PIN oublié par email & modification du code PIN
- Gestion complète des offres (Modification pré-remplie + Suppression avec confirmation)
- Accès Administrateur discret tout en bas à droite de "Gérer mon offre" (st.secrets['admin']['password'])
- Mentions développeur (Sidebar & Footer global) : Imrane Machbaête — Version Alpha

Exécution : streamlit run app.py
"""

import re
import uuid
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# ---------------------------------------------------------------------------
# 1. CONFIGURATION DE LA PAGE & STYLE ÉPURÉ (SANS LOGO)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="PermutStage — Permutation de Stages Médecine",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    .permut-banner {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        color: #0f172a;
        padding: 1.25rem 1.75rem;
        border-radius: 10px;
        margin-bottom: 1.25rem;
    }
    .match-card {
        background-color: #f0fdf4;
        border: 1px solid #86efac;
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 1rem;
    }
    .tri-card {
        background-color: #ecfdf5;
        border: 1px solid #6ee7b7;
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 1rem;
    }
    .offer-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.15rem;
        margin-bottom: 0.75rem;
    }
    .notif-card {
        background-color: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.6rem;
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

COLONNES_UTILISATEURS = [
    "User_ID",
    "Nom",
    "Prenom",
    "Email",
    "PIN",
    "Date_Inscription",
]

COLONNES_DEMANDES = [
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

FEUILLE_UTILISATEURS = "Utilisateurs"
FEUILLE_DEMANDES = "Demandes"
FEUILLE_MESSAGES = "Messages"

# Initialisation de la session utilisateur et de l'accès administrateur
if "user" not in st.session_state:
    st.session_state["user"] = None
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False


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
# 3. PERSISTANCE GOOGLE SHEETS (3 FEUILLES : Utilisateurs, Demandes, Messages)
# ---------------------------------------------------------------------------
def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)


def normalize_pin_series(series: pd.Series) -> pd.Series:
    s = (
        series.fillna("")
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
    )
    return s.apply(lambda x: x.zfill(4) if x.isdigit() else x)


def load_utilisateurs() -> pd.DataFrame:
    """Lit la feuille 'Utilisateurs' depuis Google Sheets."""
    try:
        conn = get_connection()
        df = conn.read(worksheet=FEUILLE_UTILISATEURS, ttl=5)
        if df is None or df.empty:
            return pd.DataFrame(columns=COLONNES_UTILISATEURS)
        df = df.dropna(how="all")
        for col in COLONNES_UTILISATEURS:
            if col not in df.columns:
                df[col] = ""
        df["PIN"] = normalize_pin_series(df["PIN"])
        for col in ["User_ID", "Nom", "Prenom", "Email", "Date_Inscription"]:
            df[col] = df[col].fillna("").astype(str).str.strip()
        return df[COLONNES_UTILISATEURS]
    except Exception as exc:
        st.error(f"Erreur lors de la lecture de la feuille '{FEUILLE_UTILISATEURS}' : {exc}")
        return pd.DataFrame(columns=COLONNES_UTILISATEURS)


def save_utilisateurs(df: pd.DataFrame) -> bool:
    """Met à jour la feuille 'Utilisateurs' dans Google Sheets."""
    try:
        conn = get_connection()
        clean_df = df.copy()
        for col in COLONNES_UTILISATEURS:
            if col not in clean_df.columns:
                clean_df[col] = ""
        clean_df["PIN"] = normalize_pin_series(clean_df["PIN"])
        conn.update(worksheet=FEUILLE_UTILISATEURS, data=clean_df[COLONNES_UTILISATEURS])
        return True
    except Exception as exc:
        st.error(f"Erreur lors de l'enregistrement de l'utilisateur : {exc}")
        return False


def load_demandes() -> pd.DataFrame:
    """Lit la feuille 'Demandes' depuis Google Sheets."""
    try:
        conn = get_connection()
        df = conn.read(worksheet=FEUILLE_DEMANDES, ttl=5)
        if df is None or df.empty:
            return pd.DataFrame(columns=COLONNES_DEMANDES)
        df = df.dropna(how="all")
        for col in COLONNES_DEMANDES:
            if col not in df.columns:
                df[col] = ""
        df["PIN"] = normalize_pin_series(df["PIN"])
        for col in ["Nom", "Email", "Periode", "Specialite", "Hopital_Actuel", "Hopitaux_Souhaites"]:
            df[col] = df[col].fillna("").astype(str).str.strip()
        return df[COLONNES_DEMANDES]
    except Exception as exc:
        st.error(f"Erreur lors de la lecture de la feuille '{FEUILLE_DEMANDES}' : {exc}")
        return pd.DataFrame(columns=COLONNES_DEMANDES)


def save_demandes(df: pd.DataFrame) -> bool:
    """Met à jour la feuille 'Demandes' dans Google Sheets."""
    try:
        conn = get_connection()
        clean_df = df.copy()
        for col in COLONNES_DEMANDES:
            if col not in clean_df.columns:
                clean_df[col] = ""
        clean_df["PIN"] = normalize_pin_series(clean_df["PIN"])
        conn.update(worksheet=FEUILLE_DEMANDES, data=clean_df[COLONNES_DEMANDES])
        return True
    except Exception as exc:
        st.error(f"Erreur lors de l'enregistrement de la demande : {exc}")
        return False


def load_messages() -> pd.DataFrame:
    """Lit la feuille 'Messages' depuis Google Sheets."""
    try:
        conn = get_connection()
        df = conn.read(worksheet=FEUILLE_MESSAGES, ttl=5)
        if df is None or df.empty:
            return pd.DataFrame(columns=COLONNES_MESSAGES)
        df = df.dropna(how="all")
        for col in COLONNES_MESSAGES:
            if col not in df.columns:
                df[col] = ""
        for col in COLONNES_MESSAGES:
            df[col] = df[col].fillna("").astype(str).str.strip()
        return df[COLONNES_MESSAGES]
    except Exception as exc:
        st.error(f"Erreur lors de la lecture de la feuille '{FEUILLE_MESSAGES}' : {exc}")
        return pd.DataFrame(columns=COLONNES_MESSAGES)


def save_messages(df: pd.DataFrame) -> bool:
    """Met à jour la feuille 'Messages' dans Google Sheets."""
    try:
        conn = get_connection()
        clean_df = df.copy()
        for col in COLONNES_MESSAGES:
            if col not in clean_df.columns:
                clean_df[col] = ""
        conn.update(worksheet=FEUILLE_MESSAGES, data=clean_df[COLONNES_MESSAGES])
        return True
    except Exception as exc:
        st.error(f"Erreur lors de l'enregistrement du message : {exc}")
        return False


def parse_hospitals(raw_str: str) -> list[str]:
    if not raw_str or pd.isna(raw_str):
        return []
    return [h.strip() for h in str(raw_str).split(";") if h.strip()]


def serialize_hospitals(hospitals: list[str]) -> str:
    return ";".join(dict.fromkeys(h.strip() for h in hospitals if h.strip()))


# ---------------------------------------------------------------------------
# 4. ENVOI D'ALERTES EMAIL AUTOMATIQUES VIA SMTP (smtplib + email.mime)
# ---------------------------------------------------------------------------
def send_smtp_match_notification(destinataires_emails: list[str], subject: str, body: str) -> bool:
    """Envoie un email via SMTP avec smtplib et email.mime.text.MIMEText."""
    try:
        smtp_conf = st.secrets["smtp"]
        smtp_server = smtp_conf["server"]
        smtp_port = int(smtp_conf.get("port", 587))
        smtp_user = smtp_conf["username"]
        smtp_pwd = smtp_conf["password"]

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = ", ".join(destinataires_emails)

        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pwd)
            server.sendmail(smtp_user, destinataires_emails, msg.as_string())
        return True
    except Exception:
        return False


def trigger_new_match_emails(anciens_rooms: set, df_demandes_maj: pd.DataFrame, df_utilisateurs: pd.DataFrame, df_messages: pd.DataFrame):
    """Détecte les nouveaux matchs créés et expédie une alerte email automatique."""
    try:
        all_binomes_apres, all_tri_apres = compute_all_matches(df_demandes_maj)
        nouveaux_binomes = [m for m in all_binomes_apres if m["room_id"] not in anciens_rooms]
        nouveaux_tri = [t for t in all_tri_apres if t["room_id"] not in anciens_rooms]

        app_url = "https://stages-medecine-ucl.streamlit.app/"

        for m in nouveaux_binomes:
            emails = [m["user1"]["Email"].strip().lower(), m["user2"]["Email"].strip().lower()]
            p = m["periode"]
            s = m["specialite"]
            h1 = m["user1"]["Hopital_Actuel"]
            h2 = m["user2"]["Hopital_Actuel"]

            for dest_email, dest_name, part_name, mon_hop, son_hop in [
                (emails[0], m["user1"]["Nom"], m["user2"]["Nom"], h1, h2),
                (emails[1], m["user2"]["Nom"], m["user1"]["Nom"], h2, h1),
            ]:
                subject = f"[PermutStage] Nouveau Match détecté pour votre stage de {s} ({p})"
                body = (
                    f"Bonjour {dest_name},\n\n"
                    f"Bonne nouvelle ! Une permutation directe a été trouvée pour votre stage de {s} en période {p}.\n\n"
                    f"Détails de l'échange :\n"
                    f"- Votre stage actuel : {mon_hop}\n"
                    f"- Stage proposé par {part_name} : {son_hop}\n\n"
                    f"Votre salon de discussion privé et confidentiel est désormais ouvert sur la plateforme :\n"
                    f"{app_url}\n\n"
                    f"Connectez-vous pour finaliser votre accord en toute discrétion.\n\n"
                    f"L'équipe PermutStage"
                )
                send_smtp_match_notification([dest_email], subject, body)

        for t in nouveaux_tri:
            u1, u2, u3 = t["user1"], t["user2"], t["user3"]
            p = t["periode"]
            s = t["specialite"]
            tri_data = [
                (u1["Email"], u1["Nom"], u2["Nom"], u1["Hopital_Actuel"], u2["Hopital_Actuel"]),
                (u2["Email"], u2["Nom"], u3["Nom"], u2["Hopital_Actuel"], u3["Hopital_Actuel"]),
                (u3["Email"], u3["Nom"], u1["Nom"], u3["Hopital_Actuel"], u1["Hopital_Actuel"]),
            ]
            for dest_email, dest_name, receveur_nom, mon_hop, cible_hop in tri_data:
                subject = f"[PermutStage] Boucle triangulaire détectée pour votre stage de {s} ({p})"
                body = (
                    f"Bonjour {dest_name},\n\n"
                    f"Une opportunité d'échange en boucle triangulaire (3 étudiants) a été identifiée pour votre stage de {s} ({p}).\n\n"
                    f"Votre affectation actuelle : {mon_hop}\n"
                    f"L'hôpital que vous obtiendrez : {cible_hop}\n\n"
                    f"Rejoignez le salon de discussion tripartite confidentiel sur PermutStage :\n"
                    f"{app_url}\n\n"
                    f"L'équipe PermutStage"
                )
                send_smtp_match_notification([dest_email], subject, body)
    except Exception:
        pass


def send_pin_recovery_email(dest_email: str, prenom: str, pin: str) -> bool:
    """Envoie le code PIN par email via SMTP en cas d'oubli de l'étudiant."""
    try:
        smtp_conf = st.secrets["smtp"]
        smtp_server = smtp_conf["server"]
        smtp_port = int(smtp_conf.get("port", 587))
        smtp_user = smtp_conf["username"]
        smtp_pwd = smtp_conf["password"]

        subject = "[PermutStage] Récupération de votre code PIN"
        body = (
            f"Bonjour {prenom},\n\n"
            f"Vous avez demandé la récupération de votre code PIN pour accéder à PermutStage.\n\n"
            f"Votre code PIN de connexion est : {pin}\n\n"
            f"Vous pouvez désormais vous connecter directement sur la plateforme :\n"
            f"https://stages-medecine-ucl.streamlit.app/\n\n"
            f"Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet email ou modifier votre PIN depuis votre profil.\n\n"
            f"L'équipe PermutStage"
        )

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = dest_email

        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pwd)
            server.sendmail(smtp_user, [dest_email], msg.as_string())
        return True
    except Exception as exc:
        raise exc


# ---------------------------------------------------------------------------
# 5. MOTEUR DE MATCHING & FILTRE DE CONFIDENTIALITÉ STRICTE
# ---------------------------------------------------------------------------
def compute_all_matches(df: pd.DataFrame):
    """Calcule tous les binômes et boucles triangulaires compatibles."""
    bilaterals = []
    triangulars = []
    if df.empty or len(df) < 2:
        return bilaterals, triangulars

    records = df.to_dict("records")
    for r in records:
        r["_souhaits"] = set(parse_hospitals(r.get("Hopitaux_Souhaites", "")))

    n = len(records)
    for i in range(n):
        for j in range(i + 1, n):
            u1, u2 = records[i], records[j]
            if u1["Email"].strip().lower() == u2["Email"].strip().lower():
                continue
            if u1["Periode"] != u2["Periode"] or u1["Specialite"] != u2["Specialite"]:
                continue
            if u2["Hopital_Actuel"] in u1["_souhaits"] and u1["Hopital_Actuel"] in u2["_souhaits"]:
                sorted_emails = sorted([u1["Email"].strip().lower(), u2["Email"].strip().lower()])
                room_id = f"match_2_{u1['Periode']}_{u1['Specialite']}_{sorted_emails[0]}_{sorted_emails[1]}"
                bilaterals.append({
                    "user1": u1,
                    "user2": u2,
                    "periode": u1["Periode"],
                    "specialite": u1["Specialite"],
                    "room_id": room_id,
                })

    if n >= 3:
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                for k in range(n):
                    if k == i or k == j:
                        continue
                    u1, u2, u3 = records[i], records[j], records[k]
                    e1 = u1["Email"].strip().lower()
                    e2 = u2["Email"].strip().lower()
                    e3 = u3["Email"].strip().lower()
                    if len({e1, e2, e3}) < 3:
                        continue
                    if not (u1["Periode"] == u2["Periode"] == u3["Periode"]):
                        continue
                    if not (u1["Specialite"] == u2["Specialite"] == u3["Specialite"]):
                        continue
                    if (
                        u2["Hopital_Actuel"] in u1["_souhaits"]
                        and u3["Hopital_Actuel"] in u2["_souhaits"]
                        and u1["Hopital_Actuel"] in u3["_souhaits"]
                    ):
                        sorted_tri_emails = sorted([e1, e2, e3])
                        tri_room_id = f"match_3_{u1['Periode']}_{u1['Specialite']}_{sorted_tri_emails[0]}_{sorted_tri_emails[1]}_{sorted_tri_emails[2]}"
                        if not any(t["room_id"] == tri_room_id for t in triangulars):
                            triangulars.append({
                                "user1": u1,
                                "user2": u2,
                                "user3": u3,
                                "periode": u1["Periode"],
                                "specialite": u1["Specialite"],
                                "room_id": tri_room_id,
                            })

    return bilaterals, triangulars


def get_private_matches_for_user(email: str, all_binomes: list, all_triangulaires: list):
    """Filtre strict de confidentialité."""
    if not email:
        return [], []
    e = email.strip().lower()
    mes_binomes = [
        m for m in all_binomes
        if m["user1"]["Email"].strip().lower() == e or m["user2"]["Email"].strip().lower() == e
    ]
    mes_tri = [
        t for t in all_triangulaires
        if t["user1"]["Email"].strip().lower() == e
        or t["user2"]["Email"].strip().lower() == e
        or t["user3"]["Email"].strip().lower() == e
    ]
    return mes_binomes, mes_tri


def build_user_notifications(email: str, mes_binomes: list, mes_tri: list, df_messages: pd.DataFrame):
    """Génère le centre de notifications."""
    notifs = []
    if not email:
        return notifs
    em_clean = email.strip().lower()

    for m in mes_binomes:
        part = m["user2"] if m["user1"]["Email"].strip().lower() == em_clean else m["user1"]
        notifs.append({
            "titre": f"🤝 Match direct disponible ({m['periode']} · {m['specialite']})",
            "detail": f"Échange possible avec {part['Nom']} : vous obtenez '{part['Hopital_Actuel']}'. Salon privé accessible.",
            "room_id": m["room_id"],
        })

    for t in mes_tri:
        notifs.append({
            "titre": f"🔄 Boucle triangulaire active ({t['periode']} · {t['specialite']})",
            "detail": "Une combinaison à 3 étudiants est complète pour votre stage. Consultez le salon tripartite.",
            "room_id": t["room_id"],
        })

    if not df_messages.empty and "Room_ID" in df_messages.columns:
        mes_rooms = {m["room_id"] for m in mes_binomes} | {t["room_id"] for t in mes_tri}
        nouveaux_msg = df_messages[
            df_messages["Room_ID"].isin(mes_rooms)
            & (df_messages["Sender_Email"].str.lower() != em_clean)
        ]
        if not nouveaux_msg.empty:
            for room_id, g in nouveaux_msg.groupby("Room_ID"):
                last_m = g.iloc[-1]
                notifs.append({
                    "titre": f"💬 Nouveau message de {last_m['Sender_Name']}",
                    "detail": f"« {last_m['Texte'][:60]}... » (Salon privé)",
                    "room_id": room_id,
                })
    return notifs


# ---------------------------------------------------------------------------
# 6. CHARGEMENT INITIAL DES DONNÉES
# ---------------------------------------------------------------------------
df_utilisateurs = load_utilisateurs()
df_demandes = load_demandes()
df_messages = load_messages()

current_user = st.session_state.get("user")
current_user_email = current_user["Email"].strip().lower() if current_user else ""

all_matchs_binomes, all_matchs_triangulaires = compute_all_matches(df_demandes)
mes_matchs_binomes, mes_matchs_triangulaires = get_private_matches_for_user(
    current_user_email, all_matchs_binomes, all_matchs_triangulaires
)
mes_notifications = build_user_notifications(
    current_user_email, mes_matchs_binomes, mes_matchs_triangulaires, df_messages
)

# ---------------------------------------------------------------------------
# 7. BARRE LATÉRALE : AUTHENTIFICATION, PROFIL & MENTIONS
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("PermutStage")
    st.caption("Médecine UCLouvain — P3 à P8")
    st.divider()

    st.subheader("Mon Compte Étudiant")

    if current_user is not None:
        st.success(
            f"Connecté : **{current_user['Prenom']} {current_user['Nom']}**\n\n`{current_user['Email']}`"
        )

        with st.expander("🔒 Modifier mon code PIN", expanded=False):
            with st.form("sidebar_change_pin_form"):
                old_pin_in = st.text_input(
                    "Code PIN actuel", type="password", max_chars=4
                )
                new_pin_in = st.text_input(
                    "Nouveau code PIN", type="password", max_chars=4
                )
                conf_pin_in = st.text_input(
                    "Confirmer le nouveau code PIN", type="password", max_chars=4
                )
                btn_save_pin = st.form_submit_button(
                    "Mettre à jour mon code PIN", use_container_width=True
                )

                if btn_save_pin:
                    old_c = old_pin_in.strip()
                    new_c = new_pin_in.strip()
                    conf_c = conf_pin_in.strip()

                    expected_cur_pin = str(current_user.get("PIN", "")).strip()

                    if old_c != expected_cur_pin:
                        st.error("Le code PIN actuel est incorrect.")
                    elif not re.match(r"^\d{4}$", new_c):
                        st.error("Le nouveau code PIN doit comporter exactement 4 chiffres.")
                    elif new_c != conf_c:
                        st.error("Le nouveau code PIN et sa confirmation ne correspondent pas.")
                    else:
                        u_idx = df_utilisateurs[
                            df_utilisateurs["Email"].str.lower() == current_user_email
                        ].index
                        if not u_idx.empty:
                            df_utilisateurs.loc[u_idx, "PIN"] = new_c
                            save_utilisateurs(df_utilisateurs)

                        dem_idx = df_demandes[
                            df_demandes["Email"].str.lower() == current_user_email
                        ].index
                        if not dem_idx.empty:
                            df_demandes.loc[dem_idx, "PIN"] = new_c
                            save_demandes(df_demandes)

                        st.session_state["user"]["PIN"] = new_c
                        st.success("Votre code PIN a été mis à jour avec succès !")
                        st.rerun()

        if st.button("Se déconnecter", use_container_width=True):
            st.session_state["user"] = None
            st.session_state["is_admin"] = False
            st.rerun()
    else:
        auth_tabs = st.tabs(["Connexion", "Créer un compte"])

        # Onglet Connexion
        with auth_tabs[0]:
            with st.form("sidebar_login_form"):
                login_email = st.text_input(
                    "Email institutionnel", placeholder="prenom.nom@student.uclouvain.be"
                )
                login_pin = st.text_input(
                    "Code PIN (4 chiffres)", type="password", max_chars=4
                )
                btn_login = st.form_submit_button(
                    "Se connecter", type="primary", use_container_width=True
                )

                if btn_login:
                    em_clean = login_email.strip().lower()
                    pin_clean = login_pin.strip()
                    user_rows = df_utilisateurs[
                        df_utilisateurs["Email"].str.lower() == em_clean
                    ]
                    if user_rows.empty:
                        st.error("Aucun compte trouvé pour cet email. Créez d'abord un compte.")
                    elif str(user_rows.iloc[0]["PIN"]).strip() != pin_clean:
                        st.error("Code PIN incorrect.")
                    else:
                        u_row = user_rows.iloc[0]
                        st.session_state["user"] = {
                            "User_ID": u_row["User_ID"],
                            "Nom": u_row["Nom"],
                            "Prenom": u_row["Prenom"],
                            "Email": u_row["Email"].strip().lower(),
                            "PIN": str(u_row["PIN"]).strip(),
                        }
                        st.rerun()

            # Option Code PIN oublié (Renvoi par email)
            with st.expander("🔑 Code PIN oublié ?", expanded=False):
                st.caption("Recevez immédiatement votre code PIN sur votre adresse email institutionnelle.")
                with st.form("sidebar_forgot_pin_form"):
                    forgot_email_input = st.text_input(
                        "Entrez votre adresse email étudiante",
                        placeholder="prenom.nom@student.uclouvain.be",
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
                                df_utilisateurs["Email"].str.lower() == fem_clean
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

        # Onglet Créer un compte
        with auth_tabs[1]:
            with st.form("sidebar_register_form"):
                reg_prenom = st.text_input("Prénom *")
                reg_nom = st.text_input("Nom *")
                reg_email = st.text_input(
                    "Email institutionnel *", placeholder="prenom.nom@student.uclouvain.be"
                )
                reg_pin = st.text_input(
                    "Choisir un Code PIN à 4 chiffres *", type="password", max_chars=4
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
                            df_utilisateurs["Email"].str.lower() == e_clean
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
                            "PIN": pin_c,
                            "Date_Inscription": datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                        }
                        df_u_maj = pd.concat(
                            [df_utilisateurs, pd.DataFrame([new_user_dict])],
                            ignore_index=True,
                        )
                        if save_utilisateurs(df_u_maj):
                            st.session_state["user"] = new_user_dict
                            st.success("Compte créé et connecté !")
                            st.rerun()

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
# 8. EN-TÊTE PRINCIPAL & CENTRE DE NOTIFICATIONS (EN HAUT À DROITE)
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
                Confidentialité stricte : vos correspondances et salons de discussion sont privés et visibles uniquement par les participants concernés.
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
            st.caption("Supervision complète des offres, gestion des tables Google Sheets et statistiques de promotion.")
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
        st.markdown("#### 📋 Vue globale sur l'ensemble des demandes (`Demandes`)")
        csv_bytes = df_demandes.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Télécharger l'état complet des demandes (.CSV)",
            data=csv_bytes,
            file_name=f"permutstage_demandes_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )
        st.dataframe(df_demandes, use_container_width=True, hide_index=True)

        # 3. Gestion des tables
        st.markdown("#### ⚙️ Gestion des tables & Suppression administrative")
        adm_t1, adm_t2, adm_t3 = st.tabs(["Supprimer une demande", "Table Utilisateurs", "Table Messages"])
        with adm_t1:
            if not df_demandes.empty:
                st.caption("Suppression administrative directe d'une offre (sans code PIN).")
                options_suppression = [
                    f"{idx} | {row['Periode']} - {row['Specialite']} | {row['Nom']} ({row['Email']}) — {row['Hopital_Actuel']}"
                    for idx, row in df_demandes.iterrows()
                ]
                choix_admin_del = st.selectbox(
                    "Sélectionner l'annonce à supprimer", options=options_suppression, key="admin_del_select_box"
                )
                if st.button("Supprimer définitivement cette offre (Admin)", type="primary", key="btn_admin_del_submit"):
                    idx_to_drop = int(choix_admin_del.split(" | ")[0])
                    df_restant = df_demandes.drop(index=idx_to_drop).reset_index(drop=True)
                    if save_demandes(df_restant):
                        st.success("Annonce supprimée avec succès par l'administrateur.")
                        st.rerun()
            else:
                st.info("Aucune annonce active dans la table des demandes.")

        with adm_t2:
            st.dataframe(df_utilisateurs, use_container_width=True, hide_index=True)

        with adm_t3:
            st.dataframe(df_messages, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# 9. ONGLETS PRINCIPAUX DE L'APPLICATION
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
        <div style="background: linear-gradient(135deg, #1e3a8a 0%, #1e1b4b 100%); color: white; padding: 2rem 2.2rem; border-radius: 14px; margin-bottom: 1.5rem;">
            <div style="display: inline-block; padding: 0.25rem 0.75rem; background: rgba(59, 130, 246, 0.25); border: 1px solid rgba(147, 197, 253, 0.35); border-radius: 9999px; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.05em; color: #bfdbfe; margin-bottom: 0.75rem;">
                ✨ PROMOTION MÉDECINE 2028 · MASTER 2
            </div>
            <h1 style="color: white; margin: 0 0 0.5rem 0; font-size: 2rem; font-weight: 800; line-height: 1.2;">
                Trouvez votre binôme de stage idéal en quelques clics
            </h1>
            <p style="color: #e0e7ff; margin: 0 0 1.25rem 0; font-size: 1rem; line-height: 1.6; max-width: 850px;">
                Bienvenue sur <strong>PermutStage</strong>, la plateforme pensée pour fluidifier, simplifier et centraliser
                les échanges de lieux de stages hospitaliers entre camarades de promotion. Vos souhaits sont analysés
                en continu pour trouver les meilleures permutations bilatérales ou triangulaires, dans le respect
                strict de votre vie privée.
            </p>
            <div style="background: rgba(255, 255, 255, 0.1); border-left: 4px solid #60a5fa; padding: 0.85rem 1.1rem; border-radius: 6px; font-size: 0.88rem; line-height: 1.5; color: #f8fafc;">
                <strong>💡 Version Alpha / Concept Test :</strong> Cet outil a été développé bénévolement par et pour les étudiants afin d'éliminer les annonces éparpillées sur les réseaux sociaux. Merci pour votre bienveillance, vos retours et vos suggestions pour améliorer continuellement la plateforme !
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 🧭 Comment ça marche ? (Parcours en 4 étapes)")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            """
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.2rem; height: 100%;">
                <div style="font-size: 1.8rem; margin-bottom: 0.5rem;">👤</div>
                <div style="font-size: 0.82rem; font-weight: 700; color: #1e3a8a; text-transform: uppercase;">Étape 1</div>
                <h4 style="margin: 0.2rem 0 0.5rem 0; font-size: 1rem; font-weight: 700; color: #0f172a;">Profil en 30s</h4>
                <p style="font-size: 0.85rem; color: #475569; margin: 0; line-height: 1.45;">
                    Créez votre compte avec votre nom, prénom, email institutionnel et un simple <strong>code PIN à 4 chiffres</strong>.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.2rem; height: 100%;">
                <div style="font-size: 1.8rem; margin-bottom: 0.5rem;">📝</div>
                <div style="font-size: 0.82rem; font-weight: 700; color: #1e3a8a; text-transform: uppercase;">Étape 2</div>
                <h4 style="margin: 0.2rem 0 0.5rem 0; font-size: 1rem; font-weight: 700; color: #0f172a;">Déposez votre offre</h4>
                <p style="font-size: 0.85rem; color: #475569; margin: 0; line-height: 1.45;">
                    Renseignez votre période, spécialité, hôpital attribué et sélectionnez un ou plusieurs hôpitaux souhaités.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            """
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.2rem; height: 100%;">
                <div style="font-size: 1.8rem; margin-bottom: 0.5rem;">⚡</div>
                <div style="font-size: 0.82rem; font-weight: 700; color: #1e3a8a; text-transform: uppercase;">Étape 3</div>
                <h4 style="margin: 0.2rem 0 0.5rem 0; font-size: 1rem; font-weight: 700; color: #0f172a;">Matching automatique</h4>
                <p style="font-size: 0.85rem; color: #475569; margin: 0; line-height: 1.45;">
                    L'algorithme compare les souhaits et détecte instantanément les binômes directs ou les boucles triangulaires compatibles.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            """
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.2rem; height: 100%;">
                <div style="font-size: 1.8rem; margin-bottom: 0.5rem;">💬</div>
                <div style="font-size: 0.82rem; font-weight: 700; color: #1e3a8a; text-transform: uppercase;">Étape 4</div>
                <h4 style="margin: 0.2rem 0 0.5rem 0; font-size: 1rem; font-weight: 700; color: #0f172a;">Salons privés & Email</h4>
                <p style="font-size: 0.85rem; color: #475569; margin: 0; line-height: 1.45;">
                    Dès qu'un match se produit, une alerte email est envoyée et un salon privé sécurisé s'ouvre pour vous accorder.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    col_regles, col_secu = st.columns(2)

    with col_regles:
        st.markdown(
            """
            <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 12px; padding: 1.3rem;">
                <h3 style="margin-top: 0; color: #0f172a; font-size: 1.1rem; display: flex; items-center; gap: 0.5rem;">
                    ⚖️ Règles et Conditions d'Échange
                </h3>
                <ul style="font-size: 0.88rem; color: #334155; line-height: 1.6; margin-bottom: 0; padding-left: 1.2rem;">
                    <li><strong>Même période obligatoire :</strong> P3 ne peut permuter qu'avec P3, P4 avec P4, etc.</li>
                    <li><strong>Même spécialité obligatoire :</strong> Pédiatrie contre Pédiatrie, Urgences contre Urgences.</li>
                    <li><strong>Une seule offre par période :</strong> Vous pouvez déposer plusieurs offres tant qu'elles concernent des périodes distinctes.</li>
                    <li><strong>Validation facultaire ultérieure :</strong> La plateforme permet de trouver un accord mutuel. Une fois le binôme confirmé, la procédure officielle de demande de permutation auprès de la commission facultaire des stages reste obligatoire.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_secu:
        st.markdown(
            """
            <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 1.3rem;">
                <h3 style="margin-top: 0; color: #166534; font-size: 1.1rem; display: flex; items-center; gap: 0.5rem;">
                    🛡️ Confidentialité & Protection des Données
                </h3>
                <ul style="font-size: 0.88rem; color: #14532d; line-height: 1.6; margin-bottom: 0; padding-left: 1.2rem;">
                    <li><strong>Authentification minimale :</strong> Pas de mot de passe complexe, connexion rapide par code PIN personnel à 4 chiffres.</li>
                    <li><strong>Minimisation stricte :</strong> Seules les données indispensables à la logistique du stage sont collectées.</li>
                    <li><strong>Salons 100 % confidentiels :</strong> Les annonces en négociation et les messageries privées ne sont visibles <em>que</em> par les étudiants directement concernés par le match.</li>
                    <li><strong>Aucune visibilité tierce :</strong> Aucun tiers ne peut savoir qui échange avec qui.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    st.info("Prêt à débuter ? Connectez-vous via le menu latéral ou rendez-vous sur l'onglet **'1. Déposer une demande'** pour soumettre vos souhaits.")

# ===========================================================================
# ONGLET 1 : DÉPOSER UNE DEMANDE
# ===========================================================================
with tab1:
    st.subheader("Déposer une offre d'échange de stage")

    if current_user is None:
        st.warning(
            "🔒 Vous devez être connecté à votre compte étudiant pour déposer une annonce. "
            "Créez ou connectez votre compte dans la barre latérale gauche."
        )
    else:
        st.caption(f"Offre déposée sous l'identité : **{current_user['Prenom']} {current_user['Nom']}** (`{current_user['Email']}`)")

        with st.form("form_depot_demande", clear_on_submit=True):
            col_form_1, col_form_2 = st.columns(2)
            with col_form_1:
                sel_periode = st.selectbox("Période *", options=PERIODES)
                sel_spec = st.selectbox("Spécialité *", options=SPECIALITES)
            with col_form_2:
                sel_hopital_actuel = st.selectbox(
                    "Hôpital actuel attribué *",
                    options=TOUS_LES_HOPITAUX,
                    format_func=lambda h: f"[{HOPITAL_VERS_REGION.get(h, '')}] {h}",
                )

            st.markdown("#### Hôpitaux souhaités en échange *")
            sel_hopitaux_souhaites = st.multiselect(
                "Sélectionnez un ou plusieurs lieux souhaités :",
                options=TOUS_LES_HOPITAUX,
                format_func=lambda h: f"[{HOPITAL_VERS_REGION.get(h, '')}] {h}",
                placeholder="Choisissez vos hôpitaux souhaités...",
            )

            btn_submit_demande = st.form_submit_button(
                "Publier mon offre d'échange", type="primary", use_container_width=True
            )

            if btn_submit_demande:
                form_errors = []
                if not sel_hopitaux_souhaites:
                    form_errors.append("Veuillez choisir au moins un hôpital souhaité.")
                if sel_hopital_actuel in sel_hopitaux_souhaites:
                    form_errors.append("L'hôpital actuel attribué ne peut pas figurer dans votre liste de souhaits.")

                if (
                    not df_demandes.empty
                    and not df_demandes[
                        (df_demandes["Email"].str.lower() == current_user_email)
                        & (df_demandes["Periode"] == sel_periode)
                    ].empty
                ):
                    form_errors.append(
                        f"Vous avez déjà déposé une offre active pour la période {sel_periode}. "
                        "Rendez-vous dans l'onglet '4. Gérer mon offre' pour la modifier."
                    )

                if form_errors:
                    for e in form_errors:
                        st.error(e)
                else:
                    anciens_rooms = {m["room_id"] for m in all_matchs_binomes} | {
                        t["room_id"] for t in all_matchs_triangulaires
                    }

                    nouvelle_demande = {
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Nom": f"{current_user['Prenom']} {current_user['Nom']}",
                        "Email": current_user["Email"],
                        "PIN": current_user["PIN"],
                        "Periode": sel_periode,
                        "Specialite": sel_spec,
                        "Hopital_Actuel": sel_hopital_actuel,
                        "Hopitaux_Souhaites": serialize_hospitals(sel_hopitaux_souhaites),
                    }
                    df_demandes_maj = pd.concat(
                        [df_demandes, pd.DataFrame([nouvelle_demande])],
                        ignore_index=True,
                    )
                    if save_demandes(df_demandes_maj):
                        trigger_new_match_emails(
                            anciens_rooms=anciens_rooms,
                            df_demandes_maj=df_demandes_maj,
                            df_utilisateurs=df_utilisateurs,
                            df_messages=df_messages,
                        )
                        st.success(
                            f"Votre offre pour la période {sel_periode} ({sel_spec}) a été enregistrée avec succès !"
                        )
                        st.rerun()

# ===========================================================================
# ONGLET 2 : MATCHS PRIVÉS & SALONS DE DISCUSSION CONFIDENTIELS
# ===========================================================================
with tab2:
    st.subheader("Mes Matchs Disponibles & Salons Privés")

    if current_user is None:
        st.warning(
            "🔒 Cet espace est strictement confidentiel. "
            "Connectez-vous avec votre compte étudiant pour consulter vos correspondances."
        )
    else:
        st.markdown(
            f"""
            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 0.85rem 1.15rem; margin-bottom: 1rem; font-size: 0.88rem; color: #334155;">
                Connecté sous <strong>{current_user['Prenom']} {current_user['Nom']}</strong> (<code>{current_user['Email']}</code>).
                Seuls vos matchs directs ou triangulaires sont affichés ci-dessous.
            </div>
            """,
            unsafe_allow_html=True,
        )

        total_matchs_user = len(mes_matchs_binomes) + len(mes_matchs_triangulaires)

        if total_matchs_user == 0:
            st.info(
                "Aucun match direct ou triangulaire ne correspond à vos souhaits pour le moment. "
                "Dès qu'un autre étudiant dépose une offre compatible, vous recevrez une notification et un email automatique !"
            )
        else:
            if mes_matchs_binomes:
                st.markdown(f"#### 🤝 Échanges directs binômes ({len(mes_matchs_binomes)})")
                for idx_m, m in enumerate(mes_matchs_binomes):
                    u1 = m["user1"]
                    u2 = m["user2"]
                    est_u1 = u1["Email"].strip().lower() == current_user_email
                    moi = u1 if est_u1 else u2
                    partenaire = u2 if est_u1 else u1

                    st.markdown(
                        f"""
                        <div class="match-card">
                            <div style="font-weight: 700; color: #166534; font-size: 1.05rem;">
                                Match Direct · {m['periode']} · {m['specialite']}
                            </div>
                            <div style="margin-top: 0.4rem; font-size: 0.92rem; color: #1e293b;">
                                <strong>Votre stage actuel :</strong> {moi['Hopital_Actuel']}<br/>
                                <strong>Stage obtenu en échange :</strong> {partenaire['Hopital_Actuel']} (proposé par <strong>{partenaire['Nom']}</strong>)
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    with st.expander(
                        f"💬 Ouvrir le Salon Privé avec {partenaire['Nom']} (Room: {m['room_id'][:28]}...)",
                        expanded=True,
                    ):
                        room_id = m["room_id"]
                        msgs_room = df_messages[df_messages["Room_ID"] == room_id]

                        if msgs_room.empty:
                            st.caption("Aucun message échangé pour le moment. Saluez votre camarade !")
                        else:
                            for _, msg_row in msgs_room.iterrows():
                                is_me = msg_row["Sender_Email"].strip().lower() == current_user_email
                                align = "right" if is_me else "left"
                                bg_color = "#eff6ff" if is_me else "#f1f5f9"
                                border_col = "#bfdbfe" if is_me else "#e2e8f0"
                                label_sender = "Vous" if is_me else msg_row["Sender_Name"]

                                st.markdown(
                                    f"""
                                    <div style="text-align: {align}; margin-bottom: 0.5rem;">
                                        <div style="display: inline-block; background-color: {bg_color}; border: 1px solid {border_col}; border-radius: 8px; padding: 0.5rem 0.85rem; max-width: 75%; text-align: left;">
                                            <div style="font-size: 0.75rem; font-weight: 700; color: #1e3a8a;">
                                                {label_sender} · <span style="color: #64748b; font-weight: 400;">{msg_row['Timestamp']}</span>
                                            </div>
                                            <div style="font-size: 0.88rem; color: #0f172a; margin-top: 0.2rem;">
                                                {msg_row['Texte']}
                                            </div>
                                        </div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )

                        with st.form(f"msg_form_binome_{idx_m}", clear_on_submit=True):
                            texte_input = st.text_input(
                                "Écrire un message privé",
                                placeholder="Bonjour, es-tu d'accord pour qu'on échange nos stages ?",
                                key=f"input_b_{idx_m}",
                            )
                            btn_send = st.form_submit_button("Envoyer dans le salon privé")
                            if btn_send:
                                txt_c = texte_input.strip()
                                if txt_c:
                                    nouveau_message = {
                                        "Message_ID": f"MSG_{uuid.uuid4().hex[:8].upper()}",
                                        "Room_ID": room_id,
                                        "Sender_Email": current_user["Email"],
                                        "Sender_Name": f"{current_user['Prenom']} {current_user['Nom']}",
                                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "Texte": txt_c,
                                    }
                                    df_messages_maj = pd.concat(
                                        [df_messages, pd.DataFrame([nouveau_message])],
                                        ignore_index=True,
                                    )
                                    if save_messages(df_messages_maj):
                                        st.rerun()

            if mes_matchs_triangulaires:
                st.markdown(f"#### 🔄 Échanges en boucle triangulaire ({len(mes_matchs_triangulaires)})")
                for idx_t, t in enumerate(mes_matchs_triangulaires):
                    u1 = t["user1"]
                    u2 = t["user2"]
                    u3 = t["user3"]
                    st.markdown(
                        f"""
                        <div class="tri-card">
                            <div style="font-weight: 700; color: #065f46; font-size: 1.05rem;">
                                Boucle Triangulaire · {t['periode']} · {t['specialite']}
                            </div>
                            <div style="margin-top: 0.4rem; font-size: 0.92rem; color: #1e293b;">
                                <strong>Cycle d'affectation :</strong><br/>
                                • <strong>{u1['Nom']}</strong> cède <em>{u1['Hopital_Actuel']}</em> à <strong>{u3['Nom']}</strong><br/>
                                • <strong>{u2['Nom']}</strong> cède <em>{u2['Hopital_Actuel']}</em> à <strong>{u1['Nom']}</strong><br/>
                                • <strong>{u3['Nom']}</strong> cède <em>{u3['Hopital_Actuel']}</em> à <strong>{u2['Nom']}</strong>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    with st.expander(
                        f"💬 Ouvrir le Salon Tripartite Privé (Room: {t['room_id'][:28]}...)",
                        expanded=True,
                    ):
                        room_id_tri = t["room_id"]
                        msgs_tri_room = df_messages[df_messages["Room_ID"] == room_id_tri]

                        if msgs_tri_room.empty:
                            st.caption("Aucun message dans ce salon tripartite pour l'instant.")
                        else:
                            for _, msg_row in msgs_tri_room.iterrows():
                                is_me = msg_row["Sender_Email"].strip().lower() == current_user_email
                                align = "right" if is_me else "left"
                                bg_color = "#ecfdf5" if is_me else "#f1f5f9"
                                border_col = "#a7f3d0" if is_me else "#e2e8f0"
                                label_sender = "Vous" if is_me else msg_row["Sender_Name"]

                                st.markdown(
                                    f"""
                                    <div style="text-align: {align}; margin-bottom: 0.5rem;">
                                        <div style="display: inline-block; background-color: {bg_color}; border: 1px solid {border_col}; border-radius: 8px; padding: 0.5rem 0.85rem; max-width: 75%; text-align: left;">
                                            <div style="font-size: 0.75rem; font-weight: 700; color: #065f46;">
                                                {label_sender} · <span style="color: #64748b; font-weight: 400;">{msg_row['Timestamp']}</span>
                                            </div>
                                            <div style="font-size: 0.88rem; color: #0f172a; margin-top: 0.2rem;">
                                                {msg_row['Texte']}
                                            </div>
                                        </div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )

                        with st.form(f"msg_form_tri_{idx_t}", clear_on_submit=True):
                            texte_tri_input = st.text_input(
                                "Écrire au groupe tripartite",
                                placeholder="Bonjour à tous les deux, validons-nous cette boucle ?",
                                key=f"input_t_{idx_t}",
                            )
                            btn_send_tri = st.form_submit_button("Envoyer dans le salon tripartite")
                            if btn_send_tri:
                                txt_c = texte_tri_input.strip()
                                if txt_c:
                                    nouveau_message = {
                                        "Message_ID": f"MSG_{uuid.uuid4().hex[:8].upper()}",
                                        "Room_ID": room_id_tri,
                                        "Sender_Email": current_user["Email"],
                                        "Sender_Name": f"{current_user['Prenom']} {current_user['Nom']}",
                                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "Texte": txt_c,
                                    }
                                    df_messages_maj = pd.concat(
                                        [df_messages, pd.DataFrame([nouveau_message])],
                                        ignore_index=True,
                                    )
                                    if save_messages(df_messages_maj):
                                        st.rerun()

# ===========================================================================
# ONGLET 3 : CONSULTER TOUTES LES OFFRES (ANONYMISÉES SANS CONTACT)
# ===========================================================================
with tab3:
    st.subheader(f"Catalogue global des offres disponibles ({len(df_demandes)})")
    st.caption("Affichage anonymisé respectant la confidentialité : les coordonnées des étudiants n'apparaissent pas publiquement.")

    col_filtre_p, col_filtre_s, col_filtre_r = st.columns(3)
    with col_filtre_p:
        f_periode = st.selectbox("Filtrer par Période", options=["Toutes"] + PERIODES)
    with col_filtre_s:
        f_specialite = st.selectbox("Filtrer par Spécialité", options=["Toutes"] + SPECIALITES)
    with col_filtre_r:
        f_region = st.selectbox("Filtrer par Région de l'hôpital actuel", options=["Toutes"] + REGIONS)

    df_filtre = df_demandes.copy()
    if f_periode != "Toutes":
        df_filtre = df_filtre[df_filtre["Periode"] == f_periode]
    if f_specialite != "Toutes":
        df_filtre = df_filtre[df_filtre["Specialite"] == f_specialite]
    if f_region != "Toutes":
        df_filtre = df_filtre[
            df_filtre["Hopital_Actuel"].apply(lambda h: HOPITAL_VERS_REGION.get(h, "") == f_region)
        ]

    if df_filtre.empty:
        st.info("Aucune offre ne correspond à ces critères.")
    else:
        for idx, row in df_filtre.iterrows():
            souhaites_liste = ", ".join(parse_hospitals(row["Hopitaux_Souhaites"]))
            region_act = HOPITAL_VERS_REGION.get(row["Hopital_Actuel"], "Région")

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
# ONGLET 4 : GÉRER MON OFFRE (MODIFICATION PRÉ-REMPLIE & SUPPRESSION CONFIRMÉE)
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
                periode_courante = row["Periode"]
                spec_courante = row["Specialite"]
                hop_actuel_courant = row["Hopital_Actuel"]
                souhaites_courants = [
                    h
                    for h in parse_hospitals(row["Hopitaux_Souhaites"])
                    if h in TOUS_LES_HOPITAUX
                ]

                with st.expander(
                    f"📌 Période {periode_courante} · {spec_courante} — Actuel : {hop_actuel_courant} (Modifié le {row['Timestamp']})",
                    expanded=True,
                ):
                    col_edit, col_del = st.columns([2, 1])

                    # OPTION 1 : MODIFIER L'ANNONCE
                    with col_edit:
                        st.markdown("##### Option 1 : Modifier l'annonce")
                        with st.form(f"edit_form_{idx}"):
                            new_periode = st.selectbox(
                                "Période",
                                options=PERIODES,
                                index=PERIODES.index(periode_courante)
                                if periode_courante in PERIODES
                                else 0,
                                key=f"edit_per_{idx}",
                            )
                            new_spec = st.selectbox(
                                "Spécialité",
                                options=SPECIALITES,
                                index=SPECIALITES.index(spec_courante)
                                if spec_courante in SPECIALITES
                                else 0,
                                key=f"edit_spec_{idx}",
                            )
                            new_hop_actuel = st.selectbox(
                                "Hôpital actuel",
                                options=TOUS_LES_HOPITAUX,
                                index=TOUS_LES_HOPITAUX.index(hop_actuel_courant)
                                if hop_actuel_courant in TOUS_LES_HOPITAUX
                                else 0,
                                key=f"edit_act_{idx}",
                            )
                            new_souhaites = st.multiselect(
                                "Hôpitaux souhaités",
                                options=TOUS_LES_HOPITAUX,
                                default=souhaites_courants,
                                format_func=lambda h: f"[{HOPITAL_VERS_REGION.get(h, '')}] {h}",
                                key=f"edit_wish_{idx}",
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

                                if new_periode != periode_courante:
                                    conflit = df_demandes[
                                        (df_demandes.index != idx)
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

                                    df_demandes.at[idx, "Timestamp"] = (
                                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    )
                                    df_demandes.at[idx, "Periode"] = new_periode
                                    df_demandes.at[idx, "Specialite"] = new_spec
                                    df_demandes.at[idx, "Hopital_Actuel"] = (
                                        new_hop_actuel
                                    )
                                    df_demandes.at[idx, "Hopitaux_Souhaites"] = (
                                        serialize_hospitals(new_souhaites)
                                    )
                                    if save_demandes(df_demandes):
                                        trigger_new_match_emails(
                                            anciens_rooms=anciens_rooms_avant_modif,
                                            df_demandes_maj=df_demandes,
                                            df_utilisateurs=df_utilisateurs,
                                            df_messages=df_messages,
                                        )
                                        st.success(
                                            "Votre annonce a été mise à jour avec succès !"
                                        )
                                        st.rerun()

                    # OPTION 2 : SUPPRIMER L'ANNONCE AVEC CONFIRMATION EXPLICITE
                    with col_del:
                        st.markdown("##### Option 2 : Supprimer l'annonce")
                        st.caption(
                            "Cette action retirera définitivement votre demande de la feuille Google Sheets et fermera les salons associés."
                        )
                        confirm_check = st.checkbox(
                            "Je confirme vouloir supprimer définitivement cette offre",
                            key=f"confirm_del_{idx}",
                        )
                        if st.button(
                            "Confirmer la suppression",
                            key=f"btn_del_{idx}",
                            type="secondary",
                            disabled=not confirm_check,
                            use_container_width=True,
                        ):
                            df_restant = df_demandes.drop(index=idx).reset_index(
                                drop=True
                            )
                            if save_demandes(df_restant):
                                st.success(
                                    f"Votre offre pour la période {periode_courante} a été supprimée."
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
# 10. PIED DE PAGE (FOOTER GLOBAL)
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
