"""
drive_manager.py
────────────────
Gère la sauvegarde automatique sur Google Drive.

Structure créée dans Drive :
  VéloScore/
  └── 2026-03-17/          ← un dossier par jour
      ├── photos/
      │   ├── 14h32m05_photo.jpg
      │   └── 14h32m31_photo.jpg
      ├── resultats/
      │   ├── 14h32m05_resultat.json
      │   └── 14h32m31_resultat.json
      └── session_2026-03-17.csv   ← mis à jour après chaque analyse
"""

import json
import io
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


# ─────────────────────────────────────────────
# CONNEXION
# ─────────────────────────────────────────────

def get_service(secrets: dict):
    """
    Crée un client Drive authentifié avec le compte de service.
    `secrets` est le dict st.secrets["google_drive"].
    """
    info = {
        "type":                        secrets["type"],
        "project_id":                  secrets["project_id"],
        "private_key_id":              secrets["private_key_id"],
        "private_key":                 secrets["private_key"].replace("\\n", "\n"),
        "client_email":                secrets["client_email"],
        "client_id":                   secrets["client_id"],
        "auth_uri":                    secrets["auth_uri"],
        "token_uri":                   secrets["token_uri"],
        "auth_provider_x509_cert_url": secrets["auth_provider_x509_cert_url"],
        "client_x509_cert_url":        secrets["client_x509_cert_url"],
    }
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


# ─────────────────────────────────────────────
# UTILITAIRES DOSSIERS
# ─────────────────────────────────────────────

def _trouver_ou_creer_dossier(service, nom: str, parent_id: str | None = None) -> str:
    """
    Cherche un dossier par nom (et parent optionnel).
    Le crée s'il n'existe pas. Retourne son ID Drive.
    """
    query = f"name='{nom}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    res = service.files().list(q=query, fields="files(id, name)").execute()
    fichiers = res.get("files", [])

    if fichiers:
        return fichiers[0]["id"]

    # Créer le dossier
    meta = {"name": nom, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        meta["parents"] = [parent_id]
    dossier = service.files().create(body=meta, fields="id").execute()
    return dossier["id"]


def _preparer_arborescence(service, racine_id: str) -> dict:
    """
    Crée/récupère l'arborescence du jour.
    Retourne un dict avec les IDs des dossiers utiles.
    """
    aujourd_hui = datetime.now().strftime("%Y-%m-%d")

    id_jour    = _trouver_ou_creer_dossier(service, aujourd_hui, racine_id)
    id_photos  = _trouver_ou_creer_dossier(service, "photos",    id_jour)
    id_results = _trouver_ou_creer_dossier(service, "resultats", id_jour)

    return {
        "racine":    racine_id,
        "jour":      id_jour,
        "photos":    id_photos,
        "resultats": id_results,
        "date":      aujourd_hui,
    }


# ─────────────────────────────────────────────
# UPLOAD FICHIERS
# ─────────────────────────────────────────────

def _uploader(service, contenu: bytes, nom: str, mime: str, parent_id: str) -> str:
    """Upload un fichier et retourne son ID."""
    meta  = {"name": nom, "parents": [parent_id]}
    media = MediaIoBaseUpload(io.BytesIO(contenu), mimetype=mime)
    f = service.files().create(body=meta, media_body=media, fields="id").execute()
    return f["id"]


def _mettre_a_jour_csv(service, dossiers: dict, nouvelle_ligne: dict):
    """
    Ajoute une ligne au CSV de session.
    Crée le fichier s'il n'existe pas encore.
    """
    nom_csv = f"session_{dossiers['date']}.csv"

    # Chercher le CSV existant
    query = (f"name='{nom_csv}' and '{dossiers['jour']}' in parents "
             f"and trashed=false")
    res = service.files().list(q=query, fields="files(id)").execute()
    fichiers = res.get("files", [])

    entetes = ["horodatage", "heure", "lat", "lng", "score_global", "verdict",
               "largeur", "obstacles", "signalisation", "separation",
               "type_voie", "conseil", "positifs", "negatifs"]

    if fichiers:
        # Télécharger l'existant et ajouter la ligne
        fid = fichiers[0]["id"]
        contenu_bytes = service.files().get_media(fileId=fid).execute()
        texte_existant = contenu_bytes.decode("utf-8")
        nouvelle_ligne_csv = _ligne_csv(nouvelle_ligne, entetes)
        texte_final = texte_existant.rstrip("\n") + "\n" + nouvelle_ligne_csv + "\n"
        # Mettre à jour
        media = MediaIoBaseUpload(
            io.BytesIO(texte_final.encode("utf-8")), mimetype="text/csv"
        )
        service.files().update(fileId=fid, media_body=media).execute()
    else:
        # Créer avec entêtes + première ligne
        entetes_csv = ",".join(entetes) + "\n"
        premiere_ligne = _ligne_csv(nouvelle_ligne, entetes) + "\n"
        contenu = (entetes_csv + premiere_ligne).encode("utf-8")
        _uploader(service, contenu, nom_csv, "text/csv", dossiers["jour"])


def _ligne_csv(ligne: dict, entetes: list) -> str:
    """Formate une ligne CSV en échappant les virgules."""
    def echapper(v):
        v = str(v) if v is not None else ""
        if "," in v or '"' in v or "\n" in v:
            v = '"' + v.replace('"', '""') + '"'
        return v
    return ",".join(echapper(ligne.get(k, "")) for k in entetes)


# ─────────────────────────────────────────────
# FONCTION PRINCIPALE
# ─────────────────────────────────────────────

def sauvegarder(
    secrets: dict,
    racine_id: str,
    photo_bytes: bytes,
    resultat: dict,
    lat: float | None,
    lng: float | None,
) -> bool:
    """
    Sauvegarde une photo + son résultat JSON + met à jour le CSV de session.

    Paramètres :
      secrets    : st.secrets["google_drive"]
      racine_id  : ID du dossier "VéloScore" partagé avec le compte de service
      photo_bytes: les bytes de l'image JPEG
      resultat   : le dict JSON retourné par Claude
      lat, lng   : coordonnées GPS (peuvent être None)

    Retourne True si succès, False sinon.
    """
    try:
        service  = get_service(secrets)
        dossiers = _preparer_arborescence(service, racine_id)

        horodatage = datetime.now().strftime("%Y-%m-%d_%Hh%Mm%Ss")
        heure      = datetime.now().strftime("%H:%M:%S")

        # 1. Sauvegarder la photo
        _uploader(
            service,
            photo_bytes,
            f"{horodatage}_photo.jpg",
            "image/jpeg",
            dossiers["photos"]
        )

        # 2. Sauvegarder le JSON
        json_bytes = json.dumps(resultat, ensure_ascii=False, indent=2).encode("utf-8")
        _uploader(
            service,
            json_bytes,
            f"{horodatage}_resultat.json",
            "application/json",
            dossiers["resultats"]
        )

        # 3. Mettre à jour le CSV de session
        crit = resultat.get("criteres", {})
        ligne = {
            "horodatage":   horodatage,
            "heure":        heure,
            "lat":          lat or "",
            "lng":          lng or "",
            "score_global": resultat.get("score_global", ""),
            "verdict":      resultat.get("verdict", ""),
            "largeur":      crit.get("largeur", ""),
            "obstacles":    crit.get("obstacles", ""),
            "signalisation":crit.get("signalisation", ""),
            "separation":   crit.get("separation", ""),
            "type_voie":    resultat.get("type_voie", ""),
            "conseil":      resultat.get("conseil", ""),
            "positifs":     " | ".join(resultat.get("positifs", [])),
            "negatifs":     " | ".join(resultat.get("negatifs", [])),
        }
        _mettre_a_jour_csv(service, dossiers, ligne)

        return True

    except Exception as e:
        # On log l'erreur mais on ne bloque pas l'app
        print(f"[Drive] Erreur sauvegarde : {e}")
        return False
