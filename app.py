"""
PermutStage — Application Collaborative d'Échange de Lieux de Stage (Médecine P3 à P8)
Exécution : streamlit run app.py
"""

import re
import uuid
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
        margin-bottom: 1.5rem;
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

# Colonnes exactes des 2 feuilles Google Sheets
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

FEUILLE_DEMANDES = "Demandes"
FEUILLE_MESSAGES = "Messages"


# ---------------------------------------------------------------------------
# 3. PERSISTANCE GOOGLE SHEETS (FEUILLES "Demandes" & "Messages")
# ---------------------------------------------------------------------------
def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)


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
        df["PIN"] = (
            df["PIN"]
            .fillna("")
            .astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.strip()
        )
        df["PIN"] = df["PIN"].apply(lambda x: x.zfill(4) if x.isdigit() else x)
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
    """Sérialise les hôpitaux souhaités avec un point-virgule."""
    return "; ".join([h.strip() for h in hospitals if h.strip()])


def parse_hospitals(raw_str: str) -> list[str]:
    """Désérialise la chaîne séparée par des points-virgules en liste."""
    if not raw_str or pd.isna(raw_str):
        return []
    return [h.strip() for h in str(raw_str).split(";") if h.strip()]


def build_room_id(periode: str, specialite: str, emails: list[str]) -> str:
    """Génère un identifiant unique de salon : ROOM_{periode}_{specialite}_{emails_triés}."""
    sorted_emails = sorted([e.strip().lower() for e in emails])
    return f"ROOM_{periode}_{specialite}_{'_'.join(sorted_emails)}"


# ---------------------------------------------------------------------------
# 4. MOTEUR DE MATCHING (BILATÉRAL & TRIANGULAIRE)
# ---------------------------------------------------------------------------
def compute_bilateral_matches(df: pd.DataFrame) -> list[dict]:
    """Détecte les échanges bilatéraux (A <-> B) pour même période et même spécialité."""
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
                        "a": a,
                        "b": b,
                    }
                )
    return matches


def compute_triangular_matches(df: pd.DataFrame) -> list[dict]:
    """Détecte les cycles à 3 personnes (A donne à B, B donne à C, C donne à A)."""
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
                                "a": a,
                                "b": b,
                                "c": c,
                            }
                        )
    return matches


# ---------------------------------------------------------------------------
# 5. COMPOSANT DE SALON DE CHAT INTERNE (st.chat_message & st.chat_input)
# ---------------------------------------------------------------------------
def render_chat_room(
    room_id: str,
    participants: list[dict],
    df_messages: pd.DataFrame,
    label_expander: str,
):
    """Affiche le salon de discussion associé à un match (binôme ou cycle à 3)."""
    messages_salon = df_messages[df_messages["Room_ID"] == room_id]
    nb_msg = len(messages_salon)

    with st.expander(f"💬 {label_expander} ({nb_msg} message(s)) — {room_id}"):
        emails_participants = [p["Email"].strip().lower() for p in participants]
        map_participants = {p["Email"].strip().lower(): p for p in participants}

        col_id1, col_id2 = st.columns(2)
        with col_id1:
            selected_email = st.selectbox(
                "Votre email institutionnel",
                options=emails_participants,
                format_func=lambda em: f"{map_participants[em]['Nom']} ({em})",
                key=f"chat_email_{room_id}",
            )
        with col_id2:
            pin_attendu = str(map_participants[selected_email].get("PIN", "")).strip()
            if pin_attendu:
                pin_saisi = st.text_input(
                    "Votre code PIN (4 chiffres)",
                    type="password",
                    max_chars=4,
                    key=f"chat_pin_{room_id}",
                )
                acces_autorise = pin_saisi.strip() == pin_attendu
            else:
                st.caption("Accès direct activé pour votre adresse email.")
                acces_autorise = True

        if not acces_autorise:
            st.info(
                "Sélectionnez votre adresse email et renseignez votre code PIN à 4 chiffres pour accéder au salon de discussion."
            )
            return

        # Affichage de l'historique des messages du salon
        if messages_salon.empty:
            st.caption("Aucun message dans ce salon pour le moment. Lancez la discussion !")
        else:
            for _, msg in messages_salon.iterrows():
                is_me = msg["Sender_Email"].strip().lower() == selected_email
                role = "user" if is_me else "assistant"
                with st.chat_message(role):
                    st.markdown(
                        f"**{msg['Sender_Name']}** · *{msg['Timestamp']}*\n\n{msg['Texte']}"
                    )

        # Zone de saisie d'un nouveau message
        nouveau_texte = st.chat_input(
            "Écrire un message aux participants de cet échange...",
            key=f"chat_input_{room_id}",
        )
        if nouveau_texte and nouveau_texte.strip():
            sender_name = map_participants[selected_email]["Nom"]
            if append_message(
                df_messages, room_id, selected_email, sender_name, nouveau_texte
            ):
                st.rerun()


# ---------------------------------------------------------------------------
# 6. CHARGEMENT INITIAL & BARRE LATÉRALE (ESPACE ADMINISTRATEUR)
# ---------------------------------------------------------------------------
df_demandes = load_demandes()
df_messages = load_messages()
matchs_binomes = compute_bilateral_matches(df_demandes)
matchs_triangulaires = compute_triangular_matches(df_demandes)

with st.sidebar:
    st.subheader("PermutStage")
    st.caption(
        "Plateforme collaborative d'échange de stages pour la promotion de 300 étudiants en médecine."
    )
    st.metric("Offres actives", len(df_demandes))
    st.metric("Matchs binômes (2 pers.)", len(matchs_binomes))
    st.metric("Matchs triangulaires (3 pers.)", len(matchs_triangulaires))

    st.divider()
    st.subheader("Espace Administrateur")
    admin_pwd_input = st.text_input(
        "Mot de passe administrateur",
        type="password",
        placeholder="st.secrets['admin']['password']",
    )

    expected_admin_pwd = ""
    try:
        expected_admin_pwd = st.secrets["admin"]["password"]
    except Exception:
        expected_admin_pwd = ""

    is_admin_authenticated = bool(
        expected_admin_pwd and admin_pwd_input == expected_admin_pwd
    )

    if admin_pwd_input and not is_admin_authenticated:
        st.error("Mot de passe administrateur invalide ou non configuré dans secrets.toml.")
    elif is_admin_authenticated:
        st.success("Mode Administrateur activé")

# ---------------------------------------------------------------------------
# 7. EN-TÊTE ÉPURÉ SANS LOGO
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="permut-banner">
        <h1 style="margin: 0; font-size: 1.65rem; font-weight: 700; color: #0f172a;">
            PermutStage — Permutation de Stages de Médecine (P3 à P8)
        </h1>
        <p style="margin: 0.35rem 0 0 0; font-size: 0.92rem; color: #475569;">
            Règle stricte : un échange n'est possible qu'au sein d'une même période et pour une même spécialité.
            Sélectionnez vos hôpitaux individuellement ou par région géographique.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Affichage du panneau Administrateur s'il est connecté via la barre latérale
if is_admin_authenticated:
    with st.expander("🛠️ Panneau d'Administration (Gestion complète & Export CSV)", expanded=True):
        st.markdown("#### Base complète des demandes (Demandes)")
        csv_bytes = df_demandes.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Télécharger l'état complet des demandes (.CSV)",
            data=csv_bytes,
            file_name=f"permutstage_demandes_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )
        st.dataframe(df_demandes, use_container_width=True, hide_index=True)

        if not df_demandes.empty:
            st.markdown("#### Supprimer n'importe quelle offre (Sans code PIN)")
            options_suppression = [
                f"{idx} | {row['Periode']} - {row['Specialite']} | {row['Nom']} ({row['Email']}) — {row['Hopital_Actuel']}"
                for idx, row in df_demandes.iterrows()
            ]
            choix_admin_del = st.selectbox(
                "Sélectionner l'annonce à supprimer", options=options_suppression
            )
            if st.button("Supprimer cette annonce (Admin)", type="primary"):
                idx_to_drop = int(choix_admin_del.split(" | ")[0])
                df_restant = df_demandes.drop(index=idx_to_drop).reset_index(drop=True)
                if save_demandes(df_restant):
                    st.success("Annonce supprimée par l'administrateur.")
                    st.rerun()

# ---------------------------------------------------------------------------
# 8. ONGLETS PRINCIPAUX DE L'APPLICATION
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "1. Déposer une demande",
        f"2. Matchs disponibles & Messagerie ({len(matchs_binomes) + len(matchs_triangulaires)})",
        f"3. Consulter toutes les offres ({len(df_demandes)})",
        "4. Gérer mon offre",
    ]
)

# ===========================================================================
# ONGLET 1 : DÉPOSER UNE DEMANDE (AVEC FILTRE ET SÉLECTION PAR RÉGION)
# ===========================================================================
with tab1:
    st.subheader("Déposer une nouvelle demande de permutation")

    # Filtres de pré-sélection par région (interactifs hors formulaire)
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
            help="Tous les hôpitaux appartenant aux régions choisies seront automatiquement pré-cochés ci-dessous.",
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
            nom = st.text_input("Nom & Prénom *", placeholder="Ex. Camille Vandenberghe")
            email = st.text_input(
                "Email institutionnel *",
                placeholder="Ex. camille.vandenberghe@student.uclouvain.be",
            )
            pin = st.text_input(
                "Code PIN à 4 chiffres (optionnel ou pour accès messagerie)",
                max_chars=4,
                type="password",
                placeholder="Ex. 1234",
            )

        with col2:
            periode = st.selectbox("Période de stage *", options=PERIODES)
            specialite = st.selectbox("Spécialité *", options=SPECIALITES)
            hopital_actuel = st.selectbox(
                "Hôpital actuel *", options=options_hopital_actuel
            )

        # On retire automatiquement l'hôpital actuel de la pré-sélection régionale
        defaut_souhaites = [
            h for h in hopitaux_preselectionnes if h != hopital_actuel
        ]

        hopitaux_souhaites = st.multiselect(
            "Hôpitaux souhaités * (choix multiples individuels ou issus des régions sélectionnées)",
            options=TOUS_LES_HOPITAUX,
            default=defaut_souhaites,
            format_func=lambda h: f"[{HOPITAL_VERS_REGION.get(h, '')}] {h}",
        )

        submitted = st.form_submit_button(
            "Enregistrer ma demande de permutation",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            erreurs = []
            nom_clean = nom.strip()
            email_clean = email.strip().lower()
            pin_clean = pin.strip()

            if len(nom_clean) < 2:
                erreurs.append("Veuillez renseigner votre Nom & Prénom complet.")
            if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email_clean):
                erreurs.append("Veuillez saisir une adresse email institutionnelle valide.")
            if pin_clean and not re.match(r"^\d{4}$", pin_clean):
                erreurs.append("Si renseigné, le code PIN doit comporter exactement 4 chiffres.")
            if not hopitaux_souhaites:
                erreurs.append("Veuillez sélectionner au moins un hôpital souhaité.")
            elif hopital_actuel in hopitaux_souhaites:
                erreurs.append(
                    "Validation refusée : votre hôpital actuel ne peut pas figurer dans la liste des hôpitaux souhaités."
                )

            if not df_demandes.empty and email_clean:
                doublon = df_demandes[
                    (df_demandes["Email"].str.lower() == email_clean)
                    & (df_demandes["Periode"] == periode)
                ]
                if not doublon.empty:
                    erreurs.append(
                        f"Une demande existe déjà pour {email_clean} sur la période {periode}. "
                        "Supprimez d'abord votre annonce existante dans l'onglet 'Gérer mon offre'."
                    )

            if erreurs:
                for err in erreurs:
                    st.error(err)
            else:
                nouvelle_demande = pd.DataFrame(
                    [
                        {
                            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Nom": nom_clean,
                            "Email": email_clean,
                            "PIN": pin_clean,
                            "Periode": periode,
                            "Specialite": specialite,
                            "Hopital_Actuel": hopital_actuel,
                            "Hopitaux_Souhaites": serialize_hospitals(hopitaux_souhaites),
                        }
                    ]
                )
                df_maj = pd.concat([df_demandes, nouvelle_demande], ignore_index=True)
                if save_demandes(df_maj):
                    st.success(
                        f"Votre demande pour la période {periode} ({specialite}) a été publiée !"
                    )
                    st.rerun()

# ===========================================================================
# ONGLET 2 : MATCHS DISPONIBLES & SALONS DE MESSAGERIE INTERNE
# ===========================================================================
with tab2:
    st.subheader("Correspondances automatiques & Salons d'échange")

    col_bi, col_tri = st.columns(2)

    with col_bi:
        st.markdown(f"### Échanges Bilatéraux — Binômes ({len(matchs_binomes)})")
        if not matchs_binomes:
            st.info("Aucun match bilatéral détecté pour le moment.")
        else:
            for m in matchs_binomes:
                a, b = m["a"], m["b"]
                st.markdown(
                    f"""
                    <div class="match-card">
                        <div style="font-weight: 700; color: #166534; margin-bottom: 0.4rem;">
                            MATCH BILATÉRAL · {m['periode']} · {m['specialite']}
                        </div>
                        <p style="margin: 0.25rem 0;">
                            <strong>{a['Nom']}</strong> ({a['Hopital_Actuel']})
                            &nbsp;&lt;-&gt;&nbsp;
                            <strong>{b['Nom']}</strong> ({b['Hopital_Actuel']})
                        </p>
                        <p style="margin: 0.4rem 0 0 0; font-size: 0.85rem; color: #15803d;">
                            Contacts : <a href="mailto:{a['Email']}">{a['Email']}</a> |
                            <a href="mailto:{b['Email']}">{b['Email']}</a>
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                render_chat_room(
                    room_id=m["room_id"],
                    participants=m["participants"],
                    df_messages=df_messages,
                    label_expander=f"Salon binôme {a['Nom']} & {b['Nom']}",
                )

    with col_tri:
        st.markdown(
            f"### Salons d'Échange Triangulaires — Cycles à 3 ({len(matchs_triangulaires)})"
        )
        if not matchs_triangulaires:
            st.info("Aucun cycle triangulaire à 3 personnes détecté pour le moment.")
        else:
            for t in matchs_triangulaires:
                a, b, c = t["a"], t["b"], t["c"]
                st.markdown(
                    f"""
                    <div class="tri-card">
                        <div style="font-weight: 700; color: #065f46; margin-bottom: 0.4rem;">
                            CYCLE TRIANGULAIRE · {t['periode']} · {t['specialite']}
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
                            Contacts :
                            <a href="mailto:{a['Email']}">{a['Email']}</a> ·
                            <a href="mailto:{b['Email']}">{b['Email']}</a> ·
                            <a href="mailto:{c['Email']}">{c['Email']}</a>
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                render_chat_room(
                    room_id=t["room_id"],
                    participants=t["participants"],
                    df_messages=df_messages,
                    label_expander=f"Salon triangulaire {a['Nom']}, {b['Nom']} & {c['Nom']}",
                )

# ===========================================================================
# ONGLET 3 : CONSULTER TOUTES LES OFFRES (AVEC FILTRE PAR RÉGION)
# ===========================================================================
with tab3:
    st.subheader("Catalogue complet des offres de stage")
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
            "Recherche libre", placeholder="Hôpital, étudiant..."
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
            df_filtre["Nom"].str.lower().str.contains(q, na=False)
            | df_filtre["Hopital_Actuel"].str.lower().str.contains(q, na=False)
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
                            {row['Periode']} · {row['Specialite']} — {row['Nom']}
                        </span>
                        <a href="mailto:{row['Email']}" style="font-size:0.85rem; color:#2563eb;">
                            {row['Email']}
                        </a>
                    </div>
                    <div style="margin-top:0.4rem; font-size:0.9rem;">
                        <strong>Hôpital actuel ({region_act}) :</strong> {row['Hopital_Actuel']}<br/>
                        <strong>Hôpitaux souhaités :</strong> {souhaites_liste}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ===========================================================================
# ONGLET 4 : GÉRER MON OFFRE (SUPPRESSION PAR EMAIL + PÉRIODE)
# ===========================================================================
with tab4:
    st.subheader("Retirer mon annonce une fois l'échange conclu")
    st.caption(
        "Saisissez votre adresse email institutionnelle et la période concernée pour retirer votre offre."
    )

    with st.form("form_suppression"):
        del_email = st.text_input("Email institutionnel utilisé lors du dépôt *")
        del_periode = st.selectbox("Période concernée *", options=PERIODES)
        btn_delete = st.form_submit_button(
            "Supprimer définitivement mon annonce", type="primary"
        )

        if btn_delete:
            email_cible = del_email.strip().lower()
            masque_offre = (df_demandes["Email"].str.lower() == email_cible) & (
                df_demandes["Periode"] == del_periode
            )
            offres_trouvees = df_demandes[masque_offre]

            if offres_trouvees.empty:
                st.error(
                    f"Aucune annonce trouvée pour l'email '{email_cible}' sur la période {del_periode}."
                )
            else:
                df_restant = df_demandes[~masque_offre].reset_index(drop=True)
                if save_demandes(df_restant):
                    st.success(
                        f"Votre annonce pour la période {del_periode} a été définitivement supprimée."
                    )
                    st.rerun()
