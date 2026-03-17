import streamlit as st
import anthropic
import base64
import json
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
from datetime import datetime
import time
import threading

import drive_manager  # module local

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="VéloScore",
    page_icon="🚴",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;700;900&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

.stApp { background: #0A0C10; }
#MainMenu, footer, header, [data-testid="stToolbar"] { visibility: hidden; }
[data-testid="stSidebar"] { display: none; }

.block-container { padding: 16px 16px 80px 16px !important; max-width: 480px !important; margin: 0 auto; }

.topbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 0 18px 0; border-bottom: 1px solid #1E2130; margin-bottom: 18px;
}
.topbar-title { font-size: 22px; font-weight: 900; color: #FFFFFF; letter-spacing: -0.5px; }
.topbar-score { font-size: 28px; font-weight: 900; background: #1A1D27; border-radius: 12px; padding: 4px 14px; }
.topbar-meta  { font-size: 11px; color: #555A72; text-align: right; margin-top: 2px; }

/* Indicateur Drive */
.drive-badge {
    display: inline-flex; align-items: center; gap: 5px;
    background: #0D2B1A; border-radius: 20px;
    padding: 3px 10px; font-size: 11px; font-weight: 700;
    color: #00C853; margin-bottom: 10px;
}
.drive-badge.off { background: #2B1A0D; color: #FF8C00; }
.drive-badge.err { background: #2B0D0D; color: #FF5252; }

div[data-testid="stButton"] > button {
    border-radius: 20px !important; font-family: 'DM Sans', sans-serif !important;
    font-weight: 900 !important; font-size: 20px !important; border: none !important;
    width: 100% !important; padding: 0 !important; height: 110px !important;
    letter-spacing: -0.3px !important; transition: transform 0.1s, opacity 0.1s !important;
    cursor: pointer !important;
}
div[data-testid="stButton"] > button:active { transform: scale(0.97) !important; opacity: 0.85 !important; }

div[data-testid="stButton"]:nth-of-type(1) > button { background: #00C853 !important; color: #002B0F !important; }
div[data-testid="stButton"]:nth-of-type(2) > button { background: #2979FF !important; color: #00144A !important; }
div[data-testid="stButton"]:nth-of-type(3) > button {
    background: #1A1D27 !important; color: #8B8FA8 !important;
    font-size: 13px !important; height: 44px !important; border-radius: 10px !important;
}

.result-card {
    background: #1A1D27; border-radius: 18px; padding: 18px 20px;
    margin: 14px 0; border-left: 5px solid #00C853;
}
.result-score-big { font-size: 52px; font-weight: 900; line-height: 1; }
.result-verdict   { font-size: 14px; color: #8B8FA8; margin-top: 2px; }

.pill { display: inline-block; border-radius: 20px; padding: 4px 12px; font-size: 12px; font-weight: 700; margin: 3px 3px 0 0; }
.pill-ok  { background: #0D2B1A; color: #00C853; }
.pill-bad { background: #2B0D0D; color: #FF5252; }

.criteres-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 12px; }
.critere-box { background: #12151E; border-radius: 12px; padding: 10px 12px; text-align: center; }
.critere-val  { font-size: 22px; font-weight: 900; }
.critere-name { font-size: 10px; color: #555A72; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }

.progress-serie { background: #1A1D27; border-radius: 14px; padding: 14px 18px; margin: 10px 0; text-align: center; }
.progress-bar-bg   { background: #12151E; border-radius: 8px; height: 10px; margin-top: 10px; overflow: hidden; }
.progress-bar-fill { background: #2979FF; height: 10px; border-radius: 8px; transition: width 0.4s; }

.histo-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 8px 12px; background: #12151E; border-radius: 10px;
    margin-bottom: 6px; font-size: 13px; color: #C0C4D6;
}
.histo-score { font-weight: 900; font-size: 16px; }

[data-baseweb="tab-list"] { background: #12151E !important; border-radius: 12px !important; padding: 4px !important; gap: 4px !important; }
[data-baseweb="tab"] { border-radius: 9px !important; color: #555A72 !important; font-weight: 700 !important; }
[aria-selected="true"][data-baseweb="tab"] { background: #1A1D27 !important; color: #FFFFFF !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SESSION
# ─────────────────────────────────────────────
for k, v in [("historique", []), ("derniere", None), ("serie_active", False),
             ("serie_restant", 0), ("serie_scores", []), ("drive_ok", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
# CLIENTS
# ─────────────────────────────────────────────
try:
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
except Exception:
    st.error("⚠️ Clé API Anthropic manquante — ajoutez ANTHROPIC_API_KEY dans Streamlit Secrets")
    st.stop()

# Vérifier si Drive est configuré
DRIVE_ACTIF = "google_drive" in st.secrets and "drive_folder_id" in st.secrets
DRIVE_FOLDER_ID = st.secrets.get("drive_folder_id", "") if DRIVE_ACTIF else ""

# ─────────────────────────────────────────────
# FONCTIONS ANALYSE
# ─────────────────────────────────────────────
PROMPT = """Tu es un expert en mobilité cyclable. Analyse cette photo prise depuis un vélo.
Réponds UNIQUEMENT avec un objet JSON valide, sans markdown.

{"score_global":3,"criteres":{"largeur":3,"obstacles":3,"signalisation":3,"separation":3},
"verdict":"Correct","type_voie":"piste cyclable","positifs":["..."],"negatifs":["..."],"conseil":"..."}

Scoring 1-5 : largeur (<1m=1 à >2.5m=5), obstacles (nombreux=1 à aucun=5),
signalisation (absente=1 à complète=5), separation (aucune=1 à piste séparée=5).
verdict : 1-2=Dangereux, 3=Correct, 4=Bon, 5=Excellent"""


def analyser(image_bytes: bytes) -> dict | None:
    b64 = base64.standard_b64encode(image_bytes).decode()
    try:
        msg = client.messages.create(
            model="claude-opus-4-6", max_tokens=600,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": PROMPT}
            ]}]
        )
        texte = msg.content[0].text.strip()
        if texte.startswith("```"):
            texte = "\n".join(l for l in texte.split("\n") if not l.startswith("```")).strip()
        return json.loads(texte)
    except Exception as e:
        st.error(f"Erreur analyse : {e}")
        return None


def couleur(s):
    return "#00C853" if s >= 4 else "#FFD600" if s == 3 else "#FF3D00"

def emoji_s(s):
    return "🟢" if s >= 4 else "🟡" if s == 3 else "🔴"


# ─────────────────────────────────────────────
# SAUVEGARDE (locale + Drive en arrière-plan)
# ─────────────────────────────────────────────

def _sauver_drive_bg(photo_bytes: bytes, resultat: dict, lat, lng):
    """Upload Drive dans un thread séparé pour ne pas bloquer l'UI."""
    ok = drive_manager.sauvegarder(
        secrets=st.secrets["google_drive"],
        racine_id=DRIVE_FOLDER_ID,
        photo_bytes=photo_bytes,
        resultat=resultat,
        lat=lat,
        lng=lng,
    )
    st.session_state.drive_ok = ok


def sauver(r: dict, photo_bytes: bytes, lat, lng):
    """Sauvegarde en session + déclenche l'upload Drive en parallèle."""
    st.session_state.historique.append({
        "heure": datetime.now().strftime("%H:%M:%S"),
        "lat": lat, "lng": lng,
        "scores": r,
        "b64": base64.standard_b64encode(photo_bytes).decode()
    })
    st.session_state.derniere = r

    # Upload Drive en arrière-plan (ne bloque pas l'affichage du résultat)
    if DRIVE_ACTIF:
        t = threading.Thread(
            target=_sauver_drive_bg,
            args=(photo_bytes, r, lat, lng),
            daemon=True
        )
        t.start()


# ─────────────────────────────────────────────
# AFFICHAGE RÉSULTAT
# ─────────────────────────────────────────────

def afficher_resultat(r):
    s = r["score_global"]
    c = couleur(s)
    positifs = "".join(f'<span class="pill pill-ok">✓ {p}</span>' for p in r.get("positifs", []))
    negatifs = "".join(f'<span class="pill pill-bad">✗ {p}</span>' for p in r.get("negatifs", []))
    crit = r["criteres"]
    st.markdown(f"""
    <div class="result-card" style="border-left-color:{c}">
        <div style="display:flex;align-items:flex-start;justify-content:space-between">
            <div>
                <div class="result-score-big" style="color:{c}">{s}/5</div>
                <div class="result-verdict">{r['verdict']} · {r.get('type_voie','')}</div>
            </div>
            <div style="font-size:42px;margin-top:-4px">{emoji_s(s)}</div>
        </div>
        <div style="margin-top:10px">{positifs}{negatifs}</div>
        <div class="criteres-grid">
            <div class="critere-box"><div class="critere-val" style="color:{couleur(crit['largeur'])}">{crit['largeur']}</div><div class="critere-name">Largeur</div></div>
            <div class="critere-box"><div class="critere-val" style="color:{couleur(crit['obstacles'])}">{crit['obstacles']}</div><div class="critere-name">Obstacles</div></div>
            <div class="critere-box"><div class="critere-val" style="color:{couleur(crit['signalisation'])}">{crit['signalisation']}</div><div class="critere-name">Signalisation</div></div>
            <div class="critere-box"><div class="critere-val" style="color:{couleur(crit['separation'])}">{crit['separation']}</div><div class="critere-name">Séparation</div></div>
        </div>
        {f'<div style="margin-top:12px;font-size:13px;color:#8B8FA8">💡 {r["conseil"]}</div>' if r.get("conseil") else ""}
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# CARTE
# ─────────────────────────────────────────────

def construire_carte(historique):
    pts = [h for h in historique if h.get("lat") and h.get("lng")]
    if not pts:
        return None
    lat_m = sum(h["lat"] for h in pts) / len(pts)
    lng_m = sum(h["lng"] for h in pts) / len(pts)
    m = folium.Map(location=[lat_m, lng_m], zoom_start=16, tiles="CartoDB dark_matter")
    if len(pts) > 1:
        folium.PolyLine([(h["lat"], h["lng"]) for h in pts],
                        color="#4A90E2", weight=3, opacity=0.5, dash_array="5 5").add_to(m)
    for h in pts:
        s = h["scores"]["score_global"]
        c = couleur(s)
        folium.CircleMarker(
            location=[h["lat"], h["lng"]], radius=11,
            color=c, fill=True, fill_color=c, fill_opacity=0.9,
            tooltip=f"{emoji_s(s)} {s}/5 — {h['heure']}"
        ).add_to(m)
    return m


def export_csv(historique):
    rows = []
    for h in historique:
        s = h["scores"]
        rows.append({
            "heure": h["heure"], "lat": h.get("lat",""), "lng": h.get("lng",""),
            "score": s["score_global"], "verdict": s["verdict"],
            "largeur": s["criteres"]["largeur"], "obstacles": s["criteres"]["obstacles"],
            "signalisation": s["criteres"]["signalisation"], "separation": s["criteres"]["separation"],
            "type_voie": s.get("type_voie",""), "conseil": s.get("conseil",""),
        })
    return pd.DataFrame(rows).to_csv(index=False)


# ─────────────────────────────────────────────
# GPS
# ─────────────────────────────────────────────
loc = get_geolocation()
lat = loc["coords"]["latitude"]  if loc and "coords" in loc else None
lng = loc["coords"]["longitude"] if loc and "coords" in loc else None

# ─────────────────────────────────────────────
# INTERFACE
# ─────────────────────────────────────────────
nb = len(st.session_state.historique)
score_moy = sum(h["scores"]["score_global"] for h in st.session_state.historique) / nb if nb else 0
coul_moy  = couleur(round(score_moy)) if nb else "#555A72"

# TOP BAR
st.markdown(f"""
<div class="topbar">
    <div class="topbar-title">🚴 VéloScore</div>
    <div>
        <div class="topbar-score" style="color:{coul_moy}">
            {f'{score_moy:.1f}' if nb else '—'}
        </div>
        <div class="topbar-meta">{nb} analyse{'s' if nb!=1 else ''}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# BADGE DRIVE
if DRIVE_ACTIF:
    if st.session_state.drive_ok is True:
        badge_cls, badge_txt = "drive-badge", "✓ Drive synchronisé"
    elif st.session_state.drive_ok is False:
        badge_cls, badge_txt = "drive-badge err", "✗ Drive — erreur de synchro"
    else:
        badge_cls, badge_txt = "drive-badge", "☁ Drive actif"
else:
    badge_cls, badge_txt = "drive-badge off", "Drive non configuré"

st.markdown(f'<div class="{badge_cls}">{badge_txt}</div>', unsafe_allow_html=True)

# ONGLETS
onglet_terrain, onglet_carte, onglet_rapport = st.tabs(["📷 Terrain", "🗺️ Carte", "📊 Rapport"])


# ══════════════════════════════════════════════
# ONGLET 1 — TERRAIN
# ══════════════════════════════════════════════
with onglet_terrain:

    st.caption(f"📍 {lat:.4f}, {lng:.4f}" if lat else "📍 GPS non disponible — autorisez la localisation")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="medium")
    with col1:
        btn_photo = st.button("📷\n1 Photo", use_container_width=True)
    with col2:
        btn_serie = st.button("🔄\n10 Photos\n(×5 sec)", use_container_width=True)

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # MODE 1 PHOTO
    if btn_photo:
        photo = st.camera_input("", label_visibility="collapsed", key="cam_unique")
        if photo:
            with st.spinner("Analyse…"):
                t0 = time.time()
                r = analyser(photo.getvalue())
            if r:
                sauver(r, photo.getvalue(), lat, lng)
                st.caption(f"⚡ {time.time()-t0:.1f}s · {'☁ sauvegardé sur Drive' if DRIVE_ACTIF else '💾 session uniquement'}")

    # MODE SÉRIE
    if btn_serie:
        st.session_state.serie_active  = True
        st.session_state.serie_restant = 10
        st.session_state.serie_scores  = []
        st.rerun()

    if st.session_state.serie_active and st.session_state.serie_restant > 0:
        n_fait = 10 - st.session_state.serie_restant
        pct = int(n_fait / 10 * 100)
        st.markdown(f"""
        <div class="progress-serie">
            <div style="font-size:15px;font-weight:700;color:#2979FF">Photo {n_fait+1} / 10</div>
            <div style="font-size:12px;color:#555A72;margin-top:2px">Prochaine dans 5 secondes…</div>
            <div class="progress-bar-bg"><div class="progress-bar-fill" style="width:{pct}%"></div></div>
        </div>
        """, unsafe_allow_html=True)

        photo_serie = st.camera_input("", label_visibility="collapsed", key=f"cam_serie_{n_fait}")
        if photo_serie:
            with st.spinner(f"Analyse {n_fait+1}/10…"):
                r = analyser(photo_serie.getvalue())
            if r:
                sauver(r, photo_serie.getvalue(), lat, lng)
                st.session_state.serie_scores.append(r["score_global"])
                st.session_state.serie_restant -= 1
                if st.session_state.serie_restant > 0:
                    time.sleep(5)
                    st.rerun()
                else:
                    st.session_state.serie_active = False
                    sc = st.session_state.serie_scores
                    st.success(f"✅ Série terminée — Score moyen : {sum(sc)/len(sc):.1f}/5 ({min(sc)} → {max(sc)})")

    # DERNIER RÉSULTAT
    if st.session_state.derniere:
        afficher_resultat(st.session_state.derniere)

    # HISTORIQUE COMPACT
    if nb > 0:
        st.markdown(f"""
        <div style="font-size:12px;color:#555A72;text-transform:uppercase;
                    letter-spacing:1px;margin:18px 0 8px 0">Historique ({nb})</div>
        """, unsafe_allow_html=True)
        for h in reversed(st.session_state.historique[-6:]):
            s = h["scores"]["score_global"]
            st.markdown(f"""
            <div class="histo-row">
                <span>{emoji_s(s)} {h['heure']} · {h['scores'].get('type_voie','')[:22]}</span>
                <span class="histo-score" style="color:{couleur(s)}">{s}/5</span>
            </div>""", unsafe_allow_html=True)

        if st.button("Effacer la session", use_container_width=True):
            for k in ["historique","derniere","serie_active","serie_restant","serie_scores","drive_ok"]:
                st.session_state[k] = [] if k in ["historique","serie_scores"] else \
                                      (False if "active" in k else (0 if "restant" in k else None))
            st.rerun()


# ══════════════════════════════════════════════
# ONGLET 2 — CARTE
# ══════════════════════════════════════════════
with onglet_carte:
    if nb == 0:
        st.markdown("""
        <div style='text-align:center;padding:60px 20px;color:#555A72'>
            <div style='font-size:48px'>🗺️</div>
            <div style='margin-top:12px;font-size:15px'>La carte apparaît après la première analyse</div>
        </div>""", unsafe_allow_html=True)
    else:
        carte = construire_carte(st.session_state.historique)
        if carte:
            st_folium(carte, width="100%", height=420, returned_objects=[])
        else:
            st.info("📍 GPS non disponible — activez la localisation pour voir la carte")
        sc_list = [h["scores"]["score_global"] for h in st.session_state.historique]
        c1, c2, c3 = st.columns(3)
        c1.metric("Moy.", f"{sum(sc_list)/len(sc_list):.1f}/5")
        c2.metric("Meilleur", f"{max(sc_list)}/5")
        c3.metric("Pire", f"{min(sc_list)}/5")


# ══════════════════════════════════════════════
# ONGLET 3 — RAPPORT
# ══════════════════════════════════════════════
with onglet_rapport:
    if nb == 0:
        st.markdown("""
        <div style='text-align:center;padding:60px 20px;color:#555A72'>
            <div style='font-size:48px'>📊</div>
            <div style='margin-top:12px;font-size:15px'>Le rapport se remplit au fil des analyses</div>
        </div>""", unsafe_allow_html=True)
    else:
        sc_list   = [h["scores"]["score_global"] for h in st.session_state.historique]
        moy       = sum(sc_list) / len(sc_list)
        dangereux = sum(1 for s in sc_list if s <= 2)
        corrects  = sum(1 for s in sc_list if s == 3)
        bons      = sum(1 for s in sc_list if s >= 4)

        st.markdown(f"""
        <div style="background:#1A1D27;border-radius:16px;padding:20px;margin-bottom:16px">
            <div style="font-size:13px;color:#555A72;text-transform:uppercase;letter-spacing:1px">Score moyen</div>
            <div style="font-size:48px;font-weight:900;color:{couleur(round(moy))};margin:4px 0">{moy:.1f}/5</div>
            <div style="display:flex;gap:12px;margin-top:10px">
                <span style="color:#FF5252;font-size:13px">🔴 {dangereux} dangereux</span>
                <span style="color:#FFD600;font-size:13px">🟡 {corrects} corrects</span>
                <span style="color:#00C853;font-size:13px">🟢 {bons} bons</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Lien direct vers le dossier Drive
        if DRIVE_ACTIF:
            st.markdown(f"""
            <a href="https://drive.google.com/drive/folders/{DRIVE_FOLDER_ID}"
               target="_blank"
               style="display:block;background:#0D2B1A;border-radius:12px;padding:12px 16px;
                      text-decoration:none;color:#00C853;font-weight:700;font-size:14px;
                      margin-bottom:16px;text-align:center">
               ☁ Ouvrir le dossier Google Drive →
            </a>""", unsafe_allow_html=True)

        with st.expander("Voir le détail des tronçons"):
            for i, h in enumerate(st.session_state.historique, 1):
                s = h["scores"]
                g = s["score_global"]
                st.markdown(f"""
                <div class="histo-row" style="flex-direction:column;align-items:flex-start;gap:4px">
                    <div style="display:flex;justify-content:space-between;width:100%">
                        <b>{i}. {h['heure']} — {s.get('type_voie','')}</b>
                        <span style="color:{couleur(g)};font-weight:900">{g}/5</span>
                    </div>
                    <div style="font-size:11px;color:#555A72">
                        Largeur {s['criteres']['largeur']} · Obstacles {s['criteres']['obstacles']} ·
                        Signalisation {s['criteres']['signalisation']} · Séparation {s['criteres']['separation']}
                    </div>
                    {f'<div style="font-size:12px;color:#8B8FA8;margin-top:2px">💡 {s["conseil"]}</div>' if s.get("conseil") else ""}
                </div>
                """, unsafe_allow_html=True)

        date_str = datetime.now().strftime("%Y%m%d_%H%M")
        st.download_button(
            "⬇️ Télécharger CSV (session actuelle)",
            data=export_csv(st.session_state.historique),
            file_name=f"veloscore_{date_str}.csv",
            mime="text/csv",
            use_container_width=True
        )
