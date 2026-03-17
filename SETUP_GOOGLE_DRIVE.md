# ☁ Configuration Google Drive — Guide pas à pas

Ce guide prend environ **10 minutes**.
Vous n'avez pas besoin de compétences techniques.

---

## Ce que vous allez faire

Créer un "compte de service" Google (un robot qui a le droit
d'écrire dans votre Drive), puis dire à Streamlit comment
l'utiliser. C'est la méthode la plus simple : pas de mot de
passe à gérer, pas de connexion à renouveler.

---

## Étape 1 — Créer un projet Google Cloud

1. Allez sur : https://console.cloud.google.com
2. En haut à gauche, cliquez sur le menu déroulant du projet
3. Cliquez "Nouveau projet"
4. Nom : `veloscore` → Créer
5. Attendez 30 secondes, puis sélectionnez ce projet

---

## Étape 2 — Activer l'API Google Drive

1. Dans la barre de recherche en haut, tapez : `Google Drive API`
2. Cliquez sur le premier résultat
3. Cliquez le bouton bleu "Activer"
4. Attendez que l'activation soit confirmée

---

## Étape 3 — Créer un compte de service

1. Dans le menu gauche : IAM et administration → Comptes de service
2. Cliquez "+ Créer un compte de service"
3. Nom : `veloscore-bot` → Créer et continuer
4. Rôle : laissez vide → Continuer → OK

Vous voyez maintenant une adresse email comme :
`veloscore-bot@veloscore-xxxxx.iam.gserviceaccount.com`
**Copiez cette adresse**, vous en aurez besoin à l'étape 5.

---

## Étape 4 — Télécharger la clé JSON

1. Cliquez sur le compte de service que vous venez de créer
2. Onglet "Clés"
3. Ajouter une clé → Créer une nouvelle clé → JSON → Créer
4. Un fichier `.json` se télécharge automatiquement
5. **Ouvrez ce fichier** avec un éditeur de texte (Bloc-notes, TextEdit)

---

## Étape 5 — Partager un dossier Drive avec le bot

1. Allez sur https://drive.google.com
2. Créez un nouveau dossier nommé `VéloScore`
3. Faites un clic droit sur ce dossier → Partager
4. Dans le champ email, collez l'adresse du compte de service
   (celle copiée à l'étape 3)
5. Rôle : **Éditeur** → Envoyer
6. Ignorez le message "impossible d'envoyer l'email"

**Récupérez l'ID du dossier** : ouvrez le dossier VéloScore,
regardez l'URL : `https://drive.google.com/drive/folders/XXXXXXXXXX`
L'ID est la partie `XXXXXXXXXX`. Copiez-la.

---

## Étape 6 — Configurer les secrets Streamlit

Dans Streamlit Cloud → votre app → Settings → Secrets,
ajoutez EXACTEMENT ceci (en remplaçant les valeurs par celles
de votre fichier JSON et l'ID de votre dossier) :

```toml
ANTHROPIC_API_KEY = "sk-ant-votre-cle-anthropic"

drive_folder_id = "VOTRE_ID_DE_DOSSIER_VELOSCORE"

[google_drive]
type                        = "service_account"
project_id                  = "VALEUR_DU_JSON"
private_key_id              = "VALEUR_DU_JSON"
private_key                 = "-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----\n"
client_email                = "veloscore-bot@veloscore-xxxxx.iam.gserviceaccount.com"
client_id                   = "VALEUR_DU_JSON"
auth_uri                    = "https://accounts.google.com/o/oauth2/auth"
token_uri                   = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url        = "VALEUR_DU_JSON"
```

⚠️  Pour `private_key` : copiez la valeur du champ `private_key`
du fichier JSON. Elle commence par `-----BEGIN` et contient
des `\n`. C'est normal, copiez-la telle quelle.

---

## Vérification

Après avoir sauvegardé les secrets, Streamlit redémarre l'app.
Le badge en haut de l'écran doit afficher :

    ☁ Drive actif

Prenez une photo → après l'analyse, le badge devient :

    ✓ Drive synchronisé

Ouvrez votre dossier Google Drive → vous verrez :

    VéloScore/
    └── 2026-03-17/
        ├── photos/
        │   └── 14h32m05_photo.jpg
        ├── resultats/
        │   └── 14h32m05_resultat.json
        └── session_2026-03-17.csv

---

## En cas de problème

Le badge rouge "Drive — erreur de synchro" signifie :
- Soit l'ID de dossier est incorrect (vérifiez l'URL Drive)
- Soit le dossier n'est pas partagé avec le bon email
- Soit la clé JSON a été copiée avec des espaces en trop

L'app continue de fonctionner normalement même si Drive
ne répond pas. Utilisez le bouton "Télécharger CSV" comme
solution de secours.
