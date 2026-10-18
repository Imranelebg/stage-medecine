"""
PermutStage — Plateforme Collaborative d'Échange de Lieux de Stage (Médecine P3 à P8)
Architecture complète :
- Comptes Étudiants (Feuille 'Utilisateurs' + st.session_state['user'])
- Confidentialité stricte des échanges (Matching Privé réservé aux étudiants impliqués)
- Centre de Notifications dynamique en haut à droite + Onglet Alertes
- Alertes Email automatiques via SMTP (smtplib + email.mime + st.secrets['smtp'])
- Gestion complète des offres (Modification pré-remplie + Suppression avec confirmation)
- Espace Administrateur (st.secrets['admin']['password'])

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

# Colonnes exactes des 3 feuilles Google Sheets
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
        conn.update(worksheet=FEUILLE_UTILISATEURS, data=df[COLONNES_UTILISATEURS])
        st.cache_data.clear()
        return True
    except Exception as exc:
        st.error(f"Erreur lors de l'écriture dans la feuille '{FEUILLE_UTILISATEURS}' : {exc}")
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
        for col in ["Timestamp", "Nom", "Email", "Periode", "Specialite", "Hopital_Actuel", "Hopitaux_Souhaites"]:
            df[col] = df[col].fillna("").astype(str).str.strip()
        return df[COLONNES_DEMANDES]
    except Exception as exc:
        st.error(f"Erreur lors de la lecture de la feuille '{FEUILLE_DEMANDES}' : {exc}")
        return pd.DataFrame(columns=COLONNES_DEMANDES)


def save_demandes(df: pd.DataFrame) -> bool:
    """Met à jour la feuille 'Demandes' dans Google Sheets."""
    try:
        conn = get_connection()
        conn.update(worksheet=FEUILLE_DEMANDES, data=df[COLONNES_DEMANDES])
        st.cache_data.clear()
        return True
    except Exception as exc:
        st.error(f"Erreur lors de l'écriture dans la feuille '{FEUILLE_DEMANDES}' : {exc}")
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
            df[col] = df[col].fillna("").astype(str).str.strip()
        return df[COLONNES_MESSAGES]
    except Exception as exc:
        st.error(f"Erreur lors de la lecture de la feuille '{FEUILLE_MESSAGES}' : {exc}")
        return pd.DataFrame(columns=COLONNES_MESSAGES)


def append_message(
    df_messages: pd.DataFrame,
    room_id: str,
    sender_email: str,
    sender_name: str,
    texte: str,
) -> bool:
    """Ajoute un message dans la feuille 'Messages' et vide le cache."""
    nouveau_msg = pd.DataFrame(
        [
            {
                "Message_ID": f"MSG_{uuid.uuid4().hex[:10].upper()}",
                "Room_ID": room_id,
                "Sender_Email": sender_email.strip().lower(),
                "Sender_Name": sender_name.strip(),
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Texte": texte.strip(),
            }
        ]
    )
    df_maj = pd.concat([df_messages, nouveau_msg], ignore_index=True)
    try:
        conn = get_connection()
        conn.update(worksheet=FEUILLE_MESSAGES, data=df_maj[COLONNES_MESSAGES])
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


# Initialisation du registre anti-doublon d'envoi d'emails en session
if "notified_match_rooms" not in st.session_state:
    st.session_state["notified_match_rooms"] = set()


# ---------------------------------------------------------------------------
# 4. SYSTÈME D'ALERTES PAR EMAIL (OPTION A : UNIQUEMENT EN CAS DE MATCH DIRECT)
# ---------------------------------------------------------------------------
def resolve_student_prenom(
    email: str, fallback_nom: str, df_utilisateurs: pd.DataFrame
) -> str:
    """Récupère le prénom de l'étudiant depuis la feuille 'Utilisateurs' ou depuis son nom complet."""
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
        # Si les secrets SMTP ne sont pas configurés, l'enregistrement Google Sheets reste prioritaire
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
                except Exception as e:
                    # Anti-plantage individuel si une adresse email destinataire est invalide
                    continue

        st.session_state["notified_match_rooms"].add(room_id)
        return sent_count
    except Exception as e:
        # Anti-plantage absolu : aucun écran rouge si le serveur SMTP a un ralentissement
        return sent_count


def trigger_new_match_emails(
    anciens_rooms: set[str],
    df_demandes_maj: pd.DataFrame,
    df_utilisateurs: pd.DataFrame,
    df_messages: pd.DataFrame,
) -> None:
    """
    Vérifie automatiquement après un ajout ou une modification dans 'Demandes' si un nouveau
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
    except Exception as e:
        # Priorité absolue à la persistance Google Sheets
        pass


def send_pin_recovery_email(dest_email: str, prenom: str, pin: str) -> bool:
    """
    Envoie le code PIN par email via SMTP en cas d'oubli de l'étudiant.
    Respecte l'objet et le corps de message demandés.
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
# 5. MOTEUR DE MATCHING & FILTRE DE CONFIDENTIALITÉ STRICTE
# ---------------------------------------------------------------------------
def compute_bilateral_matches(df: pd.DataFrame) -> list[dict]:
    """Détecte tous les échanges bilatéraux (A <-> B) pour même période et même spécialité."""
    matches = []
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
# 6. COMPOSANT DE SALON DE CHAT PRIVÉ (RÉSERVÉ AUX MEMBRES CONNECTÉS DU MATCH)
# ---------------------------------------------------------------------------
def render_private_chat_room(
    room_id: str,
    current_user: dict,
    df_messages: pd.DataFrame,
    label_expander: str,
):
    """Salon de discussion privé : l'étudiant est déjà authentifié via st.session_state['user']."""
    messages_salon = df_messages[df_messages["Room_ID"] == room_id]
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
            if append_message(
                df_messages, room_id, user_email, user_full_name, nouveau_texte
            ):
                st.rerun()


# ---------------------------------------------------------------------------
# 7. CHARGEMENT DES DONNÉES & BARRE LATÉRALE (PROFIL ÉTUDIANT + ADMIN)
# ---------------------------------------------------------------------------
df_utilisateurs = load_utilisateurs()
df_demandes = load_demandes()
df_messages = load_messages()

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

with st.sidebar:
    st.subheader("Mon Compte Étudiant")
    if current_user is not None:
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
                        mask_u = df_utilisateurs["Email"].str.lower() == current_user_email
                        if mask_u.any():
                            df_utilisateurs.loc[mask_u, "PIN"] = n_clean
                            if save_utilisateurs(df_utilisateurs):
                                if not df_demandes.empty:
                                    mask_d = df_demandes["Email"].str.lower() == current_user_email
                                    if mask_d.any():
                                        df_demandes.loc[mask_d, "PIN"] = n_clean
                                        save_demandes(df_demandes)
                                st.session_state["user"]["PIN"] = n_clean
                                st.success("Votre code PIN a été modifié avec succès !")
                                st.rerun()

        if st.button("Se déconnecter", use_container_width=True):
            st.session_state["user"] = None
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
                en temps réel par notre algorithme de permutation, dans le respect le plus strict de votre confidentialité.
            </p>
            <div style="background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 10px; padding: 0.9rem 1.1rem; font-size: 0.88rem; color: #f8fafc; line-height: 1.5;">
                <strong style="color: #fde047;">🤝 Statut du projet : Version Alpha / Concept Test</strong><br/>
                Cette plateforme est une initiative bénévole conçue <em>par et pour les étudiants</em>. Merci pour votre
                bienveillance et vos retours constructifs pour faire évoluer l'outil au service de toute la promotion !
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Fonctionnement pas-à-pas
    st.subheader("🧭 Comment ça marche ? (Le parcours en 4 étapes simples)")
    col_e1, col_e2, col_e3, col_e4 = st.columns(4)

    with col_e1:
        st.markdown(
            """
            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 1rem; min-height: 190px;">
                <div style="width: 32px; height: 32px; border-radius: 8px; background: #dbeafe; color: #1e40af; font-weight: 800; display: flex; align-items: center; justify-content: center; margin-bottom: 0.5rem;">1</div>
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
            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 1rem; min-height: 190px;">
                <div style="width: 32px; height: 32px; border-radius: 8px; background: #e0e7ff; color: #3730a3; font-weight: 800; display: flex; align-items: center; justify-content: center; margin-bottom: 0.5rem;">2</div>
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
            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 1rem; min-height: 190px;">
                <div style="width: 32px; height: 32px; border-radius: 8px; background: #f3e8ff; color: #6b21a8; font-weight: 800; display: flex; align-items: center; justify-content: center; margin-bottom: 0.5rem;">3</div>
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
            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 1rem; min-height: 190px;">
                <div style="width: 32px; height: 32px; border-radius: 8px; background: #dcfce7; color: #166534; font-weight: 800; display: flex; align-items: center; justify-content: center; margin-bottom: 0.5rem;">4</div>
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

    # 3. Règles & Conditions d'Échange
    with col_regles:
        st.subheader("⚖️ Les Règles & Conditions d'Échange")
        st.markdown(
            """
            * **Même période obligatoire :** Une permutation n'est possible qu'au sein d'une même tranche chronologique (ex. P3 contre P3, P4 contre P4).
            * **Même spécialité obligatoire :** Condition sine qua non : Pédiatrie contre Pédiatrie, Chirurgie contre Chirurgie, etc. Seul l'hôpital d'affectation change.
            * **Validation facultaire ultérieure :** PermutStage permet de trouver et finaliser un accord mutuel de principe. Une fois votre binôme ou triangle confirmé dans le salon privé, la démarche officielle auprès de la **coordination / commission des stages** demeure requise selon le règlement facultaire.
            """
        )

    # 4. Confidentialité & Protection des Données Personnelles
    with col_rgpd:
        st.subheader("🔒 Confidentialité & Respect de la Vie Privée")
        st.markdown(
            """
            * **Authentification minimale par code PIN :** Pas de stockage de mots de passe sensibles. Vos coordonnées sont protégées par votre email institutionnel et un PIN personnel à 4 chiffres.
            * **Minimisation stricte des données :** Seules les informations strictement indispensables à la logistique de permutation sont traitées.
            * **Matching 100 % privé et hermétique :** Les autres camarades de promotion ne voient **jamais** qui permute avec qui. Seuls les étudiants directement concernés par un cycle complet ont accès aux coordonnées et aux salons de discussion.
            """
        )

    st.write("")
    st.divider()

    # 5. Appel à l'action (Call-to-Action)
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
                    # Mémoriser les Room_IDs existants avant ajout pour détecter les NOUVEAUX matchs
                    anciens_rooms = {
                        m["room_id"] for m in all_matchs_binomes
                    } | {t["room_id"] for t in all_matchs_triangulaires}

                    nouvelle_demande = pd.DataFrame(
                        [
                            {
                                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "Nom": nom_complet_verrouille,
                                "Email": email_verrouille,
                                "PIN": str(current_user.get("PIN", "")).strip(),
                                "Periode": periode,
                                "Specialite": specialite,
                                "Hopital_Actuel": hopital_actuel,
                                "Hopitaux_Souhaites": serialize_hospitals(
                                    hopitaux_souhaites
                                ),
                            }
                        ]
                    )
                    df_maj = pd.concat(
                        [df_demandes, nouvelle_demande], ignore_index=True
                    )
                    if save_demandes(df_maj):
                        # Vérifier uniquement les nouveaux cycles complets (bilatéraux ou triangulaires)
                        trigger_new_match_emails(
                            anciens_rooms=anciens_rooms,
                            df_demandes_maj=df_maj,
                            df_utilisateurs=df_utilisateurs,
                            df_messages=df_messages,
                        )

                        st.success(
                            f"Votre demande pour la période {periode} ({specialite}) a été publiée !"
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

                                # Vérifier unicité si changement de période
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
