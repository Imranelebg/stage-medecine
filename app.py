"""
PermutStage — Application Collaborative d'Échange de Lieux de Stage (Médecine P3 à P8)
Exécution : streamlit run app.py
"""

import re
from datetime import datetime
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# ---------------------------------------------------------------------------
# 1. CONFIGURATION DE LA PAGE & STYLE (Palette Bleue & Blanche Minimaliste)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="PermutStage — Échange de Stages Médecine",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    .permut-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e40af 100%);
        color: #ffffff;
        padding: 1.5rem 2rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .match-card {
        background-color: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 8px;
        padding: 1.25rem;
        margin-bottom: 1rem;
    }
    .tri-card {
        background-color: #ecfdf5;
        border: 1px solid #6ee7b7;
        border-radius: 8px;
        padding: 1.25rem;
        margin-bottom: 1rem;
    }
    .offer-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1.15rem;
        margin-bottom: 0.75rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 2. CONSTANTES OFFICIELLES
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

HOPITAUX = [
    "Centre gériatrique Scheutbos Silva Médical", "Centre Hospitalier de Luxembourg",
    "Centre Hospitalier de Mouscron", "Centre Hospitalier Reine Astrid - Malmédy",
    "Centre Hospitalier Sambre & Meuse - Site Meuse", "Centre Hospitalier Sambre & Meuse - Site Sambre",
    "Centre Hospitalier VALIDA", "Centre Psychiatrique Saint Bernard", "Centre William Lennox",
    "CHIREC - Clinique Sainte Anne - Saint Remi", "CHIREC - Hôpital Braine-l'Alleud",
    "CHR de la Citadelle Site Citadelle", "CHR Haute-Senne - Soignies", "CHR HUY", "CHR Verviers",
    "CHU HELORA - Hôpital de La Louvière - Site Jolimont", "CHU HELORA - Hôpital de Lobbes",
    "CHU HELORA - Hôpital de Mons", "CHU HELORA - Hôpital de Mons - Site Kennedy",
    "CHU HELORA - Hôpital de Nivelles-Tubize", "CHU UCL NAMUR - Foyer Saint François",
    "CHU UCL NAMUR - Site Dinant", "CHU UCL NAMUR - Site Mont-Godinne",
    "CHU UCL NAMUR - Site Sainte Elisabeth - Namur", "CHwapi",
    "Clinique N. Dame de Grâce Gosselies", "Clinique Saint Jean - Bruxelles",
    "Clinique Saint Luc - Bouge", "Clinique Saint Pierre - Ottignies", "Clinique Sanatia",
    "Clinique Zitha-Hôpitaux Robert Schumann", "Cliniques de l'Europe site Sainte Elisabeth",
    "Cliniques de l'Europe site Saint Michel", "Cliniques Universitaires Saint Luc",
    "CNP Saint Martin", "EPICURA - site du Grand Hornu", "EPSYLON - La Ramée-FOND'ROY - AREA+",
    "GHdC - Centre Psychothérapeutique Charles Albert Frère", "GHdC - Les Viviers",
    "Groupe Santé CHC MontLégia", "Hôpital Psychiatrique Le Beau Vallon",
    "Hôpital psychiatrique La Petite Maison", "Hôpital Sint Nikolaus - Eupen",
    "HUmani - Centre de Santé des Fagnes - Chimay", "K.U.L.", "Université de Gand",
    "Vivalia - Hôpital d'Arlon", "Vivalia - Hôpital de Libramont", "Vivalia - Hôpital de Marche"
]

COLUMNS = [
    "nom_prenom",
    "email",
    "pin",
    "periode",
    "specialite",
    "hopital_actuel",
    "hopitaux_souhaites",
    "date_creation",
]

WORKSHEET_NAME = "Demandes"

# ---------------------------------------------------------------------------
# 3. CONNEXION GOOGLE SHEETS & UTILITAIRES DE DONNÉES
# ---------------------------------------------------------------------------
def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)


def load_data() -> pd.DataFrame:
    """Charge les demandes depuis Google Sheets et normalise les colonnes."""
    try:
        conn = get_connection()
        df = conn.read(worksheet=WORKSHEET_NAME, ttl=5)
        if df is None or df.empty:
            return pd.DataFrame(columns=COLUMNS)
        df = df.dropna(how="all")
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = ""
        # Forcer le code PIN en chaîne de 4 chiffres (évite la perte du 0 initial)
        df["pin"] = (
            df["pin"]
            .astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.strip()
            .str.zfill(4)
        )
        for col in ["nom_prenom", "email", "periode", "specialite", "hopital_actuel", "hopitaux_souhaites"]:
            df[col] = df[col].fillna("").astype(str).str.strip()
        return df[COLUMNS]
    except Exception as exc:
        st.error(f"Erreur de lecture Google Sheets : {exc}")
        return pd.DataFrame(columns=COLUMNS)


def save_data(df: pd.DataFrame) -> bool:
    """Sauvegarde l'intégralité du DataFrame dans Google Sheets."""
    try:
        conn = get_connection()
        conn.update(worksheet=WORKSHEET_NAME, data=df[COLUMNS])
        st.cache_data.clear()
        return True
    except Exception as exc:
        st.error(f"Erreur d'écriture Google Sheets : {exc}")
        return False


def serialize_hospitals(hospitals: list[str]) -> str:
    """Sérialise la liste des hôpitaux souhaités avec un point-virgule."""
    return "; ".join([h.strip() for h in hospitals if h.strip()])


def parse_hospitals(raw_str: str) -> list[str]:
    """Désérialise la chaîne séparée par des points-virgules en liste."""
    if not raw_str or pd.isna(raw_str):
        return []
    return [h.strip() for h in str(raw_str).split(";") if h.strip()]


# ---------------------------------------------------------------------------
# 4. MOTEUR DE MATCHING AUTOMATIQUE (BILATÉRAL & TRIANGULAIRE)
# ---------------------------------------------------------------------------
def compute_bilateral_matches(df: pd.DataFrame) -> list[dict]:
    """
    Match bilatéral (2 personnes) :
    Même Période ET Même Spécialité,
    Hôpital actuel de A dans souhaités de B ET Hôpital actuel de B dans souhaités de A.
    """
    matches = []
    records = df.to_dict("records")
    n = len(records)

    for i in range(n):
        for j in range(i + 1, n):
            a, b = records[i], records[j]
            if a["periode"] != b["periode"] or a["specialite"] != b["specialite"]:
                continue
            if a["hopital_actuel"] == b["hopital_actuel"]:
                continue

            souhaites_a = set(parse_hospitals(a["hopitaux_souhaites"]))
            souhaites_b = set(parse_hospitals(b["hopitaux_souhaites"]))

            if (
                a["hopital_actuel"] in souhaites_b
                and b["hopital_actuel"] in souhaites_a
            ):
                matches.append(
                    {
                        "periode": a["periode"],
                        "specialite": a["specialite"],
                        "a": a,
                        "b": b,
                    }
                )
    return matches


def compute_triangular_matches(df: pd.DataFrame) -> list[dict]:
    """
    Match triangulaire / cycle à 3 personnes :
    Même Période ET Même Spécialité,
    A donne son hôpital actuel à B (actuel A in souhaités B),
    B donne son hôpital actuel à C (actuel B in souhaités C),
    C donne son hôpital actuel à A (actuel C in souhaités A).
    """
    matches = []
    seen_cycles = set()
    records = df.to_dict("records")
    n = len(records)

    souhaites_map = {
        idx: set(parse_hospitals(rec["hopitaux_souhaites"]))
        for idx, rec in enumerate(records)
    }

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            a, b = records[i], records[j]
            if a["periode"] != b["periode"] or a["specialite"] != b["specialite"]:
                continue
            if a["hopital_actuel"] == b["hopital_actuel"]:
                continue
            if a["hopital_actuel"] not in souhaites_map[j]:
                continue

            for k in range(n):
                if k in (i, j):
                    continue
                c = records[k]
                if c["periode"] != a["periode"] or c["specialite"] != a["specialite"]:
                    continue
                if (
                    c["hopital_actuel"] == a["hopital_actuel"]
                    or c["hopital_actuel"] == b["hopital_actuel"]
                ):
                    continue

                if (
                    b["hopital_actuel"] in souhaites_map[k]
                    and c["hopital_actuel"] in souhaites_map[i]
                ):
                    # Clé canonique pour éviter les 3 rotations du même cycle (A->B->C, B->C->A, C->A->B)
                    id_a = f"{a['email'].lower()}_{a['periode']}"
                    id_b = f"{b['email'].lower()}_{b['periode']}"
                    id_c = f"{c['email'].lower()}_{c['periode']}"
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
                        matches.append(
                            {
                                "periode": a["periode"],
                                "specialite": a["specialite"],
                                "a": a,
                                "b": b,
                                "c": c,
                            }
                        )
    return matches


# ---------------------------------------------------------------------------
# 5. EN-TÊTE & LOGO SOBRE "PermutStage"
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="permut-header">
        <div>
            <span style="font-size: 1.75rem; font-weight: 700; letter-spacing: -0.03em;">
                Permut<span style="color: #93c5fd;">Stage</span>
            </span>
            <p style="margin: 0.25rem 0 0 0; font-size: 0.9rem; color: #dbeafe;">
                Plateforme officielle d'échange de lieux de stage en médecine (P3 à P8) — Même période &amp; même spécialité
            </p>
        </div>
        <div style="text-align: right; font-size: 0.85rem; color: #bfdbfe;">
            Promotion de 300 étudiants<br/>Matching bilatéral &amp; triangulaire temps réel
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Chargement des données
df_demandes = load_data()
matchs_binomes = compute_bilateral_matches(df_demandes)
matchs_triangulaires = compute_triangular_matches(df_demandes)

# ---------------------------------------------------------------------------
# 6. NAVIGATION PAR ONGLETS
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Déposer une demande",
        f"Matchs disponibles ({len(matchs_binomes) + len(matchs_triangulaires)})",
        f"Consulter toutes les offres ({len(df_demandes)})",
        "Gérer mon offre",
    ]
)

# ===========================================================================
# ONGLET 1 : DÉPOSER UNE DEMANDE
# ===========================================================================
with tab1:
    st.subheader("Déposer une nouvelle demande de permutation")
    st.caption(
        "Règle stricte : un échange n'est possible qu'au sein d'une même période (P3–P8) et pour une même spécialité. "
        "Une seule demande active est autorisée par étudiant et par période."
    )

    with st.form("form_depot_demande", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            nom_prenom = st.text_input(
                "Nom & Prénom *", placeholder="Ex. Camille Vandenberghe"
            )
            email = st.text_input(
                "Email institutionnel *",
                placeholder="Ex. camille.vandenberghe@student.uclouvain.be",
            )
            pin = st.text_input(
                "Code PIN à 4 chiffres * (requis pour supprimer l'offre)",
                max_chars=4,
                type="password",
                placeholder="1234",
            )

        with col2:
            periode = st.selectbox("Période de stage *", options=PERIODES)
            specialite = st.selectbox("Spécialité *", options=SPECIALITES)
            hopital_actuel = st.selectbox("Hôpital actuel *", options=HOPITAUX)

        hopitaux_souhaites = st.multiselect(
            "Hôpitaux souhaités * (sélection multiple possible)",
            options=HOPITAUX,
            help="Sélectionnez un ou plusieurs hôpitaux vers lesquels vous acceptez de permuter.",
        )

        submitted = st.form_submit_button(
            "Publier ma demande d'échange", type="primary", use_container_width=True
        )

        if submitted:
            erreurs = []
            nom_clean = nom_prenom.strip()
            email_clean = email.strip().lower()
            pin_clean = pin.strip()

            if len(nom_clean) < 2:
                erreurs.append("Veuillez renseigner votre Nom et Prénom complet.")
            if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email_clean):
                erreurs.append("Veuillez saisir une adresse email institutionnelle valide.")
            if not re.match(r"^\d{4}$", pin_clean):
                erreurs.append("Le code PIN doit contenir exactement 4 chiffres (0-9).")
            if not hopitaux_souhaites:
                erreurs.append("Veuillez sélectionner au moins un hôpital souhaité.")
            elif hopital_actuel in hopitaux_souhaites:
                erreurs.append(
                    "Validation refusée : votre hôpital actuel ne peut pas figurer dans la liste des hôpitaux souhaités."
                )

            # Vérification unicité (Email + Période)
            if not df_demandes.empty and email_clean:
                doublon = df_demandes[
                    (df_demandes["email"].str.lower() == email_clean)
                    & (df_demandes["periode"] == periode)
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
                nouvelle_ligne = pd.DataFrame(
                    [
                        {
                            "nom_prenom": nom_clean,
                            "email": email_clean,
                            "pin": pin_clean,
                            "periode": periode,
                            "specialite": specialite,
                            "hopital_actuel": hopital_actuel,
                            "hopitaux_souhaites": serialize_hospitals(hopitaux_souhaites),
                            "date_creation": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        }
                    ]
                )
                df_maj = pd.concat([df_demandes, nouvelle_ligne], ignore_index=True)
                if save_data(df_maj):
                    st.success(
                        f"Votre demande pour {periode} ({specialite}) a été enregistrée avec succès !"
                    )
                    st.rerun()

# ===========================================================================
# ONGLET 2 : MATCHS DISPONIBLES (BINÔMES & CYCLES À 3)
# ===========================================================================
with tab2:
    st.subheader("Correspondances automatiques détectées en temps réel")

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
                        <div style="font-weight: 700; color: #166534; margin-bottom: 0.5rem;">
                            MATCH BILATÉRAL · {m['periode']} · {m['specialite']}
                        </div>
                        <p style="margin: 0.25rem 0;">
                            <strong>{a['nom_prenom']}</strong> ({a['hopital_actuel']})
                            &nbsp;⟷&nbsp;
                            <strong>{b['nom_prenom']}</strong> ({b['hopital_actuel']})
                        </p>
                        <p style="margin: 0.4rem 0 0 0; font-size: 0.85rem; color: #15803d;">
                            Contacts : <a href="mailto:{a['email']}">{a['email']}</a> |
                            <a href="mailto:{b['email']}">{b['email']}</a>
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
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
                        <div style="font-weight: 700; color: #065f46; margin-bottom: 0.5rem;">
                            CYCLE TRIANGULAIRE · {t['periode']} · {t['specialite']}
                        </div>
                        <p style="margin: 0.35rem 0; font-size: 0.92rem; line-height: 1.5;">
                            <strong>{a['nom_prenom']}</strong> ({a['hopital_actuel']})
                            &nbsp;-&gt;&nbsp;
                            <strong>{b['nom_prenom']}</strong> ({b['hopital_actuel']})
                            &nbsp;-&gt;&nbsp;
                            <strong>{c['nom_prenom']}</strong> ({c['hopital_actuel']})
                            &nbsp;-&gt;&nbsp;
                            <strong>{a['nom_prenom']}</strong>
                        </p>
                        <p style="margin: 0.4rem 0 0 0; font-size: 0.85rem; color: #047857;">
                            Contacts :
                            <a href="mailto:{a['email']}">{a['email']}</a> ·
                            <a href="mailto:{b['email']}">{b['email']}</a> ·
                            <a href="mailto:{c['email']}">{c['email']}</a>
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

# ===========================================================================
# ONGLET 3 : CONSULTER TOUTES LES OFFRES
# ===========================================================================
with tab3:
    st.subheader("Catalogue complet des demandes de permutation")
    f_col1, f_col2, f_col3 = st.columns([1, 1, 2])
    with f_col1:
        filtre_periode = st.selectbox(
            "Filtrer par Période", options=["Toutes"] + PERIODES
        )
    with f_col2:
        filtre_specialite = st.selectbox(
            "Filtrer par Spécialité", options=["Toutes"] + SPECIALITES
        )
    with f_col3:
        filtre_recherche = st.text_input(
            "Rechercher un hôpital ou un étudiant",
            placeholder="Ex. Saint Luc, MontLégia, Namur...",
        )

    df_filtre = df_demandes.copy()
    if filtre_periode != "Toutes":
        df_filtre = df_filtre[df_filtre["periode"] == filtre_periode]
    if filtre_specialite != "Toutes":
        df_filtre = df_filtre[df_filtre["specialite"] == filtre_specialite]
    if filtre_recherche.strip():
        q = filtre_recherche.strip().lower()
        df_filtre = df_filtre[
            df_filtre["nom_prenom"].str.lower().str.contains(q, na=False)
            | df_filtre["hopital_actuel"].str.lower().str.contains(q, na=False)
            | df_filtre["hopitaux_souhaites"].str.lower().str.contains(q, na=False)
        ]

    if df_filtre.empty:
        st.info("Aucune offre ne correspond aux critères sélectionnés.")
    else:
        for _, row in df_filtre.iterrows():
            souhaites_liste = ", ".join(parse_hospitals(row["hopitaux_souhaites"]))
            st.markdown(
                f"""
                <div class="offer-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; color:#1e3a8a;">
                            {row['periode']} · {row['specialite']} — {row['nom_prenom']}
                        </span>
                        <a href="mailto:{row['email']}" style="font-size:0.85rem; color:#2563eb;">
                            {row['email']}
                        </a>
                    </div>
                    <div style="margin-top:0.4rem; font-size:0.9rem;">
                        <strong>Hôpital actuel :</strong> {row['hopital_actuel']}<br/>
                        <strong>Hôpitaux souhaités :</strong> {souhaites_liste}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ===========================================================================
# ONGLET 4 : GÉRER MON OFFRE (SUPPRESSION SÉCURISÉE PAR PIN)
# ===========================================================================
with tab4:
    st.subheader("Supprimer définitivement mon annonce")
    st.caption(
        "Une fois votre échange conclu ou si vous ne souhaitez plus permuter, saisissez vos identifiants "
        "pour retirer votre demande du Google Sheet."
    )

    with st.form("form_suppression"):
        del_email = st.text_input("Email institutionnel utilisé lors du dépôt *")
        del_periode = st.selectbox("Période concernée *", options=PERIODES)
        del_pin = st.text_input(
            "Code PIN à 4 chiffres *", max_chars=4, type="password"
        )
        btn_delete = st.form_submit_button(
            "Supprimer définitivement mon annonce", type="primary"
        )

        if btn_delete:
            email_cible = del_email.strip().lower()
            pin_cible = del_pin.strip()

            masque_offre = (df_demandes["email"].str.lower() == email_cible) & (
                df_demandes["periode"] == del_periode
            )
            offres_trouvees = df_demandes[masque_offre]

            if offres_trouvees.empty:
                st.error(
                    f"Aucune annonce trouvée pour l'email '{email_cible}' sur la période {del_periode}."
                )
            else:
                pin_enregistre = str(offres_trouvees.iloc[0]["pin"]).strip()
                if pin_enregistre != pin_cible:
                    st.error("Code PIN incorrect. Suppression refusée.")
                else:
                    df_restant = df_demandes[~masque_offre].reset_index(drop=True)
                    if save_data(df_restant):
                        st.success(
                            f"Votre annonce pour la période {del_periode} a été définitivement supprimée."
                        )
                        st.rerun()
