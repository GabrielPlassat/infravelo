import streamlit as st
import anthropic
import base64
import json
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
from datetime import datetime
from io import StringIO
import time

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="VéloScore",
    page_icon="🚴",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* Palette vélo - fond sombre, accents verts */
    :root {
        --vert:   #00C853;
        --jaune:  #FFD600;
        --rouge:  #FF3D00;
        --fond:   #0F1117;
        --carte:  #1A1D27;
        --bord:   #2A2D3A;
    }

    .stApp { background-color: var(--fond); }

    /* Header principal */
    .header-block {
        background: linear-gradient(135deg, #0F1117 0%, #1A2744 100%);
        border: 1px solid var(--bord);
        border-radius: 16px;
        padding: 20px 28px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .header-title { font-size: 28px; font-weight: 800; color: #FFFFFF; margin: 0; letter-spacing: -0.5px; }
    .header-sub   { font-size: 13px; color: #8B8FA8; margin: 0; }

    /* Carte score */
    .score-card {
        background: var(--carte);
        border: 1px solid var(--bord);
        border-radius: 14px;
        padding: 20px;
        text-align: center;
    }
    .score-number { font-size: 56px; font-weight: 900; line-height: 1; }
    .score-label  { font-size: 12px; color: #8B8FA8; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }

    /* Badge tronçon */
    .troncon-badge {
        background: var(--carte);
        border: 1px solid var(--bord);
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 13px;
        color: #C0C4D6;
    }

    /* Bouton principale */
    .stButton > button {
        background: var(--vert) !important;
        color: #000 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 12px 24px !important;
        font-size: 15px !important;
        width: 100% !important;
    }

    /* Masquer éléments Streamlit non nécessaires sur mobile */
    #MainMenu, footer, header { visibility: hidden; }

    /* Métrique */
    [data-testid="stMetricValue"] { font-size: 28px !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"] { font-size: 11px !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# INITIALISATION SESSION
# ─────────────────────────────────────────────
if "historique" not in st.session_state:
    st.session_state.historique = []      # liste de dict {heure, lat, lng, scores, photo_b64}
if "analyse_en_cours" not in st.session_state:
    st.session_state.analyse_en_cours = False
if "derniere_analyse" not in st.session_state:
    st.session_state.derniere_analyse = None

# ─────────────────────────────────────────────
# CLIENT ANTHROPIC
# ─────────────────────────────────────────────
try:
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
except Exception:
    st.error("⚠️ Clé API manquante. Ajoutez ANTHROPIC_API_KEY dans les secrets Streamlit.")
    st.stop()

# ─────────────────────────────────────────────
# FONCTIONS
# ─────────────────────────────────────────────
PROMPT_VELO = """Tu es un expert en mobilité cyclable urbaine.
Analyse cette photo prise depuis un vélo en mouvement et évalue l'infrastructure.
Réponds UNIQUEMENT avec un objet JSON valide, sans markdown, sans texte avant ou après.

Format EXACT (respecte les types) :
{
  "score_global": 3,
  "criteres": {
    "largeur": 3,
    "obstacles": 3,
    "signalisation": 3,
    "separation": 3
  },
  "verdict": "Correct",
  "points_positifs": ["élément positif 1"],
  "points_negatifs": ["élément négatif 1"],
  "type_voie": "piste cyclable dédiée",
  "conseil_immediat": "conseil court et actionnable"
}

Règles de scoring (1=très mauvais, 5=excellent) :
- largeur : <1m=1, 1-1.5m=2, 1.5-2m=3, 2-2.5m=4, >2.5m=5
- obstacles : nombreux/graves=1, quelques-uns=3, aucun=5
- signalisation : absente=1, partielle=3, complète et visible=5
- separation : aucune=1, marquage seul=2, bordure basse=3, barrière=4, piste séparée=5
- verdict : 1-2="Dangereux", 3="Correct", 4="Bon", 5="Excellent"
- score_global : moyenne arrondie des 4 critères"""


def analyser_image(image_bytes: bytes) -> dict | None:
    """Envoie l'image à Claude et retourne le JSON parsé."""
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    try:
        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=800,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_b64
                    }},
                    {"type": "text", "text": PROMPT_VELO}
                ]
            }]
        )
        texte = message.content[0].text.strip()
        # Nettoyer si balises markdown présentes
        if texte.startswith("```"):
            lignes = [l for l in texte.split("\n") if not l.startswith("```")]
            texte = "\n".join(lignes).strip()
        return json.loads(texte)
    except Exception as e:
        st.error(f"Erreur API : {e}")
        return None


def couleur_score(score: int) -> str:
    """Retourne la couleur hex selon le score."""
    if score >= 4: return "#00C853"
    if score == 3: return "#FFD600"
    return "#FF3D00"


def emoji_score(score: int) -> str:
    if score >= 4: return "🟢"
    if score == 3: return "🟡"
    return "🔴"


def construire_carte(historique: list) -> folium.Map | None:
    """Construit la carte folium avec les points du trajet."""
    points_gps = [h for h in historique if h.get("lat") and h.get("lng")]
    if not points_gps:
        return None

    lat_moy = sum(h["lat"] for h in points_gps) / len(points_gps)
    lng_moy = sum(h["lng"] for h in points_gps) / len(points_gps)

    carte = folium.Map(
        location=[lat_moy, lng_moy],
        zoom_start=16,
        tiles="CartoDB dark_matter"
    )

    # Tracer la ligne du parcours
    if len(points_gps) > 1:
        coords = [(h["lat"], h["lng"]) for h in points_gps]
        folium.PolyLine(
            coords,
            color="#4A90E2",
            weight=3,
            opacity=0.6,
            dash_array="5 5"
        ).add_to(carte)

    # Ajouter les marqueurs colorés
    for h in points_gps:
        score = h["scores"]["score_global"]
        couleur = "#00C853" if score >= 4 else "#FFD600" if score == 3 else "#FF3D00"
        verdict = h["scores"]["verdict"]
        heure = h["heure"]
        type_voie = h["scores"].get("type_voie", "")

        popup_html = f"""
        <div style='font-family:sans-serif; min-width:180px'>
            <b style='font-size:15px'>{emoji_score(score)} {score}/5 — {verdict}</b><br>
            <small style='color:#666'>{heure} · {type_voie}</small><br><hr style='margin:6px 0'>
            📏 Largeur : {h['scores']['criteres']['largeur']}/5<br>
            ⚠️ Obstacles : {h['scores']['criteres']['obstacles']}/5<br>
            🚦 Signalisation : {h['scores']['criteres']['signalisation']}/5<br>
            🚗 Séparation : {h['scores']['criteres']['separation']}/5<br>
            <hr style='margin:6px 0'>
            <i style='color:#444'>{h['scores'].get('conseil_immediat','')}</i>
        </div>"""

        folium.CircleMarker(
            location=[h["lat"], h["lng"]],
            radius=12,
            color=couleur,
            fill=True,
            fill_color=couleur,
            fill_opacity=0.85,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"Score {score}/5 — {heure}"
        ).add_to(carte)

    return carte


def generer_rapport_csv(historique: list) -> str:
    """Génère un CSV des analyses."""
    lignes = []
    for h in historique:
        lignes.append({
            "heure": h["heure"],
            "latitude": h.get("lat", ""),
            "longitude": h.get("lng", ""),
            "score_global": h["scores"]["score_global"],
            "verdict": h["scores"]["verdict"],
            "largeur": h["scores"]["criteres"]["largeur"],
            "obstacles": h["scores"]["criteres"]["obstacles"],
            "signalisation": h["scores"]["criteres"]["signalisation"],
            "separation": h["scores"]["criteres"]["separation"],
            "type_voie": h["scores"].get("type_voie", ""),
            "conseil": h["scores"].get("conseil_immediat", ""),
            "points_positifs": " | ".join(h["scores"].get("points_positifs", [])),
            "points_negatifs": " | ".join(h["scores"].get("points_negatifs", [])),
        })
    df = pd.DataFrame(lignes)
    return df.to_csv(index=False)


def generer_rapport_texte(historique: list) -> str:
    """Génère un rapport texte lisible."""
    if not historique:
        return ""
    scores = [h["scores"]["score_global"] for h in historique]
    score_moy = sum(scores) / len(scores)
    date = datetime.now().strftime("%d/%m/%Y %H:%M")

    lines = [
        "=" * 50,
        "  RAPPORT D'ANALYSE INFRASTRUCTURE VÉLO",
        f"  {date}",
        "=" * 50,
        f"\n  Tronçons analysés : {len(historique)}",
        f"  Score moyen       : {score_moy:.1f}/5",
        f"  Meilleur tronçon  : {max(scores)}/5",
        f"  Pire tronçon      : {min(scores)}/5",
        "\n" + "─" * 50,
        "  DÉTAIL PAR TRONÇON",
        "─" * 50,
    ]
    for i, h in enumerate(historique, 1):
        s = h["scores"]
        lines += [
            f"\n  [{i}] {h['heure']} — {emoji_score(s['score_global'])} {s['score_global']}/5 {s['verdict']}",
            f"      Type : {s.get('type_voie', 'N/A')}",
            f"      Largeur {s['criteres']['largeur']}/5 · Obstacles {s['criteres']['obstacles']}/5 · "
            f"Signalisation {s['criteres']['signalisation']}/5 · Séparation {s['criteres']['separation']}/5",
        ]
        if s.get("points_negatifs"):
            lines.append(f"      ⚠️  {' · '.join(s['points_negatifs'])}")
        if s.get("conseil_immediat"):
            lines.append(f"      💡 {s['conseil_immediat']}")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# INTERFACE — HEADER
# ─────────────────────────────────────────────
nb = len(st.session_state.historique)
score_session = (
    sum(h["scores"]["score_global"] for h in st.session_state.historique) / nb
    if nb > 0 else 0
)

st.markdown(f"""
<div class="header-block">
    <div>
        <p class="header-title">🚴 VéloScore</p>
        <p class="header-sub">Analyse IA de l'infrastructure cyclable en temps réel</p>
    </div>
    <div style="margin-left:auto; text-align:right">
        <p style="font-size:22px; font-weight:800; color:{'#00C853' if score_session>=4 else '#FFD600' if score_session>=3 else '#FF3D00' if score_session>0 else '#8B8FA8'}; margin:0">
            {f'{score_session:.1f}/5' if nb > 0 else '—'}
        </p>
        <p style="font-size:11px; color:#8B8FA8; margin:0">{nb} tronçon{'s' if nb>1 else ''} analysé{'s' if nb>1 else ''}</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# INTERFACE — DEUX COLONNES
# ─────────────────────────────────────────────
col_gauche, col_droite = st.columns([1, 1], gap="large")

# ── COLONNE GAUCHE : Capture + Résultat ──────
with col_gauche:
    st.subheader("📷 Capture")

    # Récupérer la géolocalisation
    loc = get_geolocation()
    lat, lng = None, None
    if loc and "coords" in loc:
        lat = loc["coords"].get("latitude")
        lng = loc["coords"].get("longitude")
        st.caption(f"📍 GPS : {lat:.5f}, {lng:.5f}" if lat else "📍 GPS en attente...")
    else:
        st.caption("📍 GPS : Autorisez la localisation dans votre navigateur")

    # Camera
    photo = st.camera_input("", label_visibility="collapsed")

    if photo:
        with st.spinner("🔍 Analyse en cours…"):
            debut = time.time()
            resultat = analyser_image(photo.getvalue())
            duree = time.time() - debut

        if resultat:
            # Sauvegarder dans l'historique
            st.session_state.historique.append({
                "heure": datetime.now().strftime("%H:%M:%S"),
                "lat": lat,
                "lng": lng,
                "scores": resultat,
                "photo_b64": base64.standard_b64encode(photo.getvalue()).decode("utf-8")
            })
            st.session_state.derniere_analyse = resultat
            st.caption(f"⚡ Analysé en {duree:.1f}s")

    # ── Affichage du dernier résultat ────────
    if st.session_state.derniere_analyse:
        r = st.session_state.derniere_analyse
        score = r["score_global"]
        coul = couleur_score(score)

        st.markdown(f"""
        <div class="score-card" style="border-color:{coul}40">
            <div class="score-number" style="color:{coul}">{score}/5</div>
            <div class="score-label">{r['verdict']} · {r.get('type_voie','')}</div>
        </div>
        """, unsafe_allow_html=True)

        # 4 métriques
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Largeur",      f"{r['criteres']['largeur']}/5")
        c2.metric("Obstacles",    f"{r['criteres']['obstacles']}/5")
        c3.metric("Signalisation",f"{r['criteres']['signalisation']}/5")
        c4.metric("Séparation",   f"{r['criteres']['separation']}/5")

        # Points positifs / négatifs
        if r.get("points_positifs"):
            for p in r["points_positifs"]:
                st.success(f"✅ {p}")
        if r.get("points_negatifs"):
            for p in r["points_negatifs"]:
                st.warning(f"⚠️ {p}")
        if r.get("conseil_immediat"):
            st.info(f"💡 {r['conseil_immediat']}")

# ── COLONNE DROITE : Carte + Historique ──────
with col_droite:

    # CARTE
    st.subheader("🗺️ Carte du parcours")
    if st.session_state.historique:
        carte = construire_carte(st.session_state.historique)
        if carte:
            st_folium(carte, width="100%", height=360, returned_objects=[])
        else:
            st.info("📍 GPS non disponible — activez la localisation pour voir la carte")
    else:
        st.markdown("""
        <div style='background:#1A1D27;border:1px dashed #2A2D3A;border-radius:12px;
                    height:200px;display:flex;align-items:center;justify-content:center;
                    color:#4A4E6A;font-size:14px'>
            La carte apparaîtra après la première analyse
        </div>""", unsafe_allow_html=True)

    # HISTORIQUE
    if st.session_state.historique:
        st.subheader(f"📋 Tronçons ({nb})")
        for h in reversed(st.session_state.historique[-8:]):
            s = h["scores"]["score_global"]
            st.markdown(f"""
            <div class="troncon-badge">
                <span>{emoji_score(s)} <b>{h['heure']}</b> — {h['scores']['verdict']}</span>
                <span style="color:{couleur_score(s)};font-weight:700;font-size:16px">{s}/5</span>
            </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SECTION EXPORT (en bas de page)
# ─────────────────────────────────────────────
if st.session_state.historique:
    st.divider()
    st.subheader("📤 Exporter le rapport")

    col_e1, col_e2, col_e3 = st.columns(3)

    with col_e1:
        csv_data = generer_rapport_csv(st.session_state.historique)
        st.download_button(
            label="⬇️ Export CSV",
            data=csv_data,
            file_name=f"veloscore_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col_e2:
        rapport_txt = generer_rapport_texte(st.session_state.historique)
        st.download_button(
            label="⬇️ Export Rapport TXT",
            data=rapport_txt,
            file_name=f"rapport_velo_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True
        )

    with col_e3:
        if st.button("🗑️ Réinitialiser la session", use_container_width=True):
            st.session_state.historique = []
            st.session_state.derniere_analyse = None
            st.rerun()
