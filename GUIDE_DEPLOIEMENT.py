# VéloScore — Notebook de déploiement
# =====================================
# Exécutez les cellules dans l'ordre

# ─────────────────────────────────────
# CELLULE 1 — Installation
# ─────────────────────────────────────
# !pip install streamlit anthropic folium streamlit-folium streamlit-js-eval pandas pillow -q
# print("✅ Installation terminée")


# ─────────────────────────────────────
# CELLULE 2 — Créer les fichiers du projet
# (copiez app.py et requirements.txt depuis
#  les fichiers fournis dans ce dossier)
# ─────────────────────────────────────
import os
os.makedirs("velo_score", exist_ok=True)

# Copiez le contenu de app.py et requirements.txt
# dans le dossier velo_score/
print("📁 Dossier velo_score/ créé")
print("   → Copiez app.py et requirements.txt dedans")


# ─────────────────────────────────────
# CELLULE 3 — Configurer la clé API
# ─────────────────────────────────────
import os

# Option A : variable d'environnement (pour tests locaux Colab)
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-VOTRE_CLE_ICI"

# Option B : secrets Streamlit Cloud (pour la mise en prod)
# → Dans Streamlit Cloud : Settings > Secrets > ajouter :
#   ANTHROPIC_API_KEY = "sk-ant-..."

print("✅ Clé API configurée")


# ─────────────────────────────────────
# CELLULE 4 — Lancer l'app depuis Colab
# (pour tester avant de déployer)
# ─────────────────────────────────────

# Installer localtunnel pour exposer le port Streamlit
# !npm install -g localtunnel -q

# Lancer streamlit en arrière-plan
# import subprocess, threading, time

# def run_streamlit():
#     subprocess.run(["streamlit", "run", "velo_score/app.py",
#                     "--server.port=8501",
#                     "--server.headless=true"])

# t = threading.Thread(target=run_streamlit, daemon=True)
# t.start()
# time.sleep(5)

# # Créer le tunnel public
# import subprocess
# result = subprocess.run(["lt", "--port", "8501"], capture_output=True, text=True, timeout=10)
# print("🌐 URL publique :", result.stdout)

print("""
──────────────────────────────────────────────
DÉPLOIEMENT STREAMLIT CLOUD (recommandé)
──────────────────────────────────────────────

1. Créez un repo GitHub avec ces 2 fichiers :
   - velo_score/app.py
   - requirements.txt

2. Allez sur : https://share.streamlit.io
   → New app
   → Sélectionnez votre repo GitHub
   → Main file path : velo_score/app.py

3. Settings > Secrets, ajoutez :
   ANTHROPIC_API_KEY = "sk-ant-votre_cle"

4. Cliquez Deploy → votre URL publique est prête !
   Ouvrez-la sur votre smartphone 📱

──────────────────────────────────────────────
UTILISATION SUR LE TERRAIN
──────────────────────────────────────────────

• Ouvrez l'URL sur votre smartphone
• Autorisez la caméra ET la géolocalisation
• Fixez le téléphone sur le guidon (support vélo)
• Prenez une photo → analyse en ~2 secondes
• La carte se remplit au fur et à mesure
• En fin de balade : Export CSV ou Rapport TXT

──────────────────────────────────────────────
COÛT ESTIMÉ
──────────────────────────────────────────────

• ~0.01$ par analyse (image Claude)
• Balade 30 min / 1 photo toutes les 30s = ~60 analyses
• Coût total : ~0.60$ par balade

──────────────────────────────────────────────
PROCHAINE ÉTAPE : WalkGPT embarqué
──────────────────────────────────────────────

• Modèle local LLaVA fine-tuné sur critères vélo
• Zéro dépendance réseau
• Fonctionne hors connexion
• Latence < 1s sur smartphone récent (Snapdragon 8+)
→ Guide de fine-tuning disponible sur demande

""")
