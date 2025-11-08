# Contours Bureaux de Vote

Téléchargez les contours géographiques des bureaux de vote en France au format GeoJSON pour un département, une circonscription ou une commune.

## 🚀 Applications

- **Nouvelle version (FastAPI + DuckDB)**: [Déployez sur Railway](#deployment)
- **Version Streamlit (legacy)**: [cliquez ici](https://contoursbdv-3vukdh6np9rqntr94d5yhh.streamlit.app/)

## ✨ Fonctionnalités

- **Recherche rapide** par département, circonscription ou commune
- **Export GeoJSON** pour chaque zone géographique
- **Données à jour** : mise à jour automatique mensuelle depuis [data.gouv.fr](https://www.data.gouv.fr/fr/datasets/proposition-de-contours-des-bureaux-de-vote/)
- **Performance optimale** avec DuckDB (faible consommation mémoire)

## 🏗️ Architecture

```
FastAPI + DuckDB + Vanilla JS
- API REST pour recherche et téléchargement
- DuckDB pour requêtes SQL rapides sur données géographiques
- Frontend léger sans framework
- GitHub Actions pour mises à jour automatiques
```

## 📦 Installation Locale

```bash
# Cloner le repo
git clone https://github.com/votre-username/contours_bdv.git
cd contours_bdv

# Créer environnement virtuel
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Installer dépendances
pip install -r requirements.txt

# Télécharger les données (optionnel si déjà dans data/)
python scripts/update_data.py

# Lancer l'API
uvicorn api.main:app --reload
```

Ouvrir http://localhost:8000/app dans votre navigateur.

## 🚢 Deployment

### Railway (Recommandé)

1. Créer un compte sur [Railway](https://railway.app)
2. Connecter votre repo GitHub
3. Railway détectera automatiquement la configuration
4. Déployer !

### Variables d'environnement

Aucune variable nécessaire pour le moment.

## 🔄 Mise à jour des données

Les données sont hébergées sur **Scaleway Object Storage** (Paris, France).

### Manuel - Mettre à jour les données

```bash
# 1. Télécharger les nouvelles données
python scripts/update_data.py

# 2. Uploader sur Scaleway
# Via interface web: https://console.scaleway.com/object-storage/buckets
# Ou via CLI:
# s3cmd put data/contours_bureaux_vote.parquet s3://contours-bureaux-vote/
```

### Configuration Scaleway

Le fichier parquet (317MB) est téléchargé depuis Scaleway au premier démarrage de l'app.

**URL:** `https://contours-bureaux-vote.s3.fr-par.scw.cloud/contours_bureaux_vote.parquet`

Pour changer l'URL, modifier `PARQUET_URL` dans `api/main.py`

## 📚 API Endpoints

- `GET /` - Informations sur l'API
- `GET /search?q={query}&type={all|departement|circonscription|commune}` - Recherche
- `GET /download/departement/{code}` - Télécharger GeoJSON d'un département
- `GET /download/circonscription/{name}` - Télécharger GeoJSON d'une circonscription
- `GET /download/commune/{code}` - Télécharger GeoJSON d'une commune
- `GET /app` - Interface utilisateur

## 🛠️ Stack Technique

- **Backend**: FastAPI, DuckDB
- **Frontend**: HTML/CSS/JS vanilla
- **Data**: GeoPandas, Parquet
- **CI/CD**: GitHub Actions
- **Hosting**: Railway

## 📊 Source de données

Données officielles de [data.gouv.fr](https://www.data.gouv.fr/fr/datasets/proposition-de-contours-des-bureaux-de-vote/)

## 📝 Migration depuis Streamlit

L'ancienne version Streamlit (`app.py`) est conservée pendant la transition. Pour l'utiliser :

```bash
streamlit run app.py
```

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.
