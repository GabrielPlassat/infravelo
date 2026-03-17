# 🚴 VéloScore

**Analyse IA de l'infrastructure cyclable en temps réel, depuis un smartphone fixé sur un guidon.**

VéloScore est une application web mobile qui utilise la vision par ordinateur (Claude API) pour évaluer automatiquement la qualité d'une voie cyclable à partir de photos prises pendant un trajet. Chaque tronçon reçoit un score sur 5 selon quatre critères : largeur, obstacles, signalisation et séparation avec la circulation motorisée.

---

## Aperçu

```
Smartphone sur guidon → Photo toutes les 5 sec → Claude analyse → Score 1-5 → Carte du parcours
```

Conçu pour être utilisé **en roulant** : deux gros boutons, affichage lisible en plein soleil, interface à une main.

---

## Fonctionnalités

### Sur le terrain
- **1 Photo** — capture immédiate, analyse en ~2 secondes, résultat affiché
- **Série de 10 photos** — déclenche automatiquement 10 captures espacées de 5 secondes, avec barre de progression et score moyen à la fin
- GPS intégré (via le navigateur) — chaque photo est géolocalisée automatiquement

### Analyse IA
Pour chaque photo, Claude évalue 4 critères sur une échelle de 1 (très mauvais) à 5 (excellent) :

| Critère | Ce qui est évalué |
|---|---|
| **Largeur** | < 1 m = 1 · 1–1,5 m = 2 · 1,5–2 m = 3 · 2–2,5 m = 4 · > 2,5 m = 5 |
| **Obstacles** | Présence de poteaux, voitures garées, mobilier urbain, etc. |
| **Signalisation** | Marquages au sol, panneaux, couleurs dédiées |
| **Séparation** | Aucune → marquage → bordure → barrière → piste séparée |

Le score global est la moyenne des 4 critères, accompagné d'un verdict (Dangereux / Correct / Bon / Excellent), des points positifs et négatifs détectés, et d'un conseil immédiat.

### Après la balade
- **Carte interactive** — tracé du parcours avec marqueurs colorés (🟢 Bon · 🟡 Correct · 🔴 Dangereux), clic sur chaque point pour voir le détail
- **Rapport de session** — score moyen, meilleur et pire tronçon, répartition par qualité
- **Export CSV** — toutes les analyses avec coordonnées GPS, exploitable sous Excel, QGIS ou tout SIG

---

## Stack technique

| Composant | Technologie |
|---|---|
| Interface | Streamlit (Python) |
| Analyse image | Claude API (`claude-opus-4-6`) |
| Carte | Folium + streamlit-folium |
| GPS | streamlit-js-eval (API navigateur) |
| Déploiement | Streamlit Cloud (gratuit) |

---

## Installation et déploiement

### Prérequis
- Un compte [Anthropic](https://console.anthropic.com) avec une clé API
- Un compte [GitHub](https://github.com)
- Un compte [Streamlit Cloud](https://share.streamlit.io) (gratuit)

### Étape 1 — Cloner ou forker ce repo

```bash
git clone https://github.com/votre-username/veloscore.git
cd veloscore
```

### Étape 2 — Déployer sur Streamlit Cloud

1. Allez sur [share.streamlit.io](https://share.streamlit.io)
2. Cliquez **New app**
3. Sélectionnez votre repo GitHub
4. Main file path : `app.py`
5. Cliquez **Deploy**

### Étape 3 — Configurer la clé API

Dans Streamlit Cloud → votre app → **Settings → Secrets** :

```toml
ANTHROPIC_API_KEY = "sk-ant-votre-cle-ici"
```

Votre URL publique est disponible immédiatement. Ouvrez-la sur votre smartphone.

### Optionnel — Lancer en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

Créez un fichier `.streamlit/secrets.toml` avec votre clé API :
```toml
ANTHROPIC_API_KEY = "sk-ant-votre-cle-ici"
```

---

## Utilisation sur le terrain

### Matériel recommandé
- Smartphone avec navigateur Chrome ou Safari
- Support téléphone pour guidon (type Quad Lock ou équivalent)
- Orientation **paysage** ou **portrait** selon votre support

### Procédure
1. Ouvrez l'URL de l'app sur votre smartphone
2. Autorisez la **caméra** et la **géolocalisation** quand le navigateur le demande
3. Fixez le téléphone sur le guidon, caméra orientée vers la voie
4. Pendant le trajet : appuyez sur **1 Photo** pour analyser un tronçon précis, ou **10 Photos × 5 sec** pour couvrir une section continue (~50 mètres à 15 km/h)
5. En fin de balade : consultez l'onglet **Carte** puis exportez le CSV depuis **Rapport**

### Conseils de capture
- Cadrez légèrement vers le bas pour inclure le revêtement et la séparation latérale
- Évitez les captures en virage serré (image floue)
- La série de 10 photos fonctionne mieux sur une ligne droite

---

## Coût estimé

| Scénario | Photos | Coût estimé |
|---|---|---|
| Test rapide | 10 photos | ~0,10 € |
| Balade 30 min (1 photo / 30 sec) | ~60 photos | ~0,60 € |
| Journée terrain (4h) | ~500 photos | ~5 € |

Les tarifs sont basés sur le modèle `claude-opus-4-6`. Consultez [anthropic.com/pricing](https://www.anthropic.com/pricing) pour les tarifs en vigueur.

---

## Structure du projet

```
veloscore/
├── app.py               # Application Streamlit principale
├── requirements.txt     # Dépendances Python
└── README.md            # Ce fichier
```

---

## Feuille de route

### Version actuelle — v1 (API)
- [x] Analyse photo unique
- [x] Série automatique 10 photos
- [x] Géolocalisation GPS
- [x] Carte interactive du parcours
- [x] Export CSV

### Prochaine version — v2 (embarqué, sans API)
Remplacement de l'API Claude par un modèle local embarqué sur le smartphone, fonctionnant **hors connexion** :

- [ ] Fine-tuning de LLaVA 7B sur des critères cyclables (dataset basé sur [PAVE](https://huggingface.co/datasets/rafiibnsultan/PAVE))
- [ ] Quantification 4-bit (format GGUF) via llama.cpp
- [ ] Latence cible < 1 seconde par image (Snapdragon 8 Gen 2 / Apple A16+)
- [ ] Zéro dépendance réseau — fonctionne en zone blanche

---

## Inspiration et sources

Ce projet s'appuie sur le dataset **PAVE** (Pedestrian Accessibility and Visual-grounded Evaluation), introduit dans l'article :

> **WalkGPT: Grounded Vision–Language Conversation with Depth-Aware Segmentation for Pedestrian Navigation**
> Rafi Ibn Sultan et al. — CVPR 2026
> [arxiv.org/abs/2603.10703](https://arxiv.org/abs/2603.10703)

PAVE fournit le cadre d'annotation (critères accessibilité, format JSON structuré, ontologie des éléments de voirie) adapté ici au contexte cyclable.

---

## Licence

MIT — libre d'utilisation, de modification et de redistribution avec attribution.

---

## Contact

Projet développé comme POC de cartographie participative de l'infrastructure cyclable.
Contributions, retours terrain et issues bienvenus.
