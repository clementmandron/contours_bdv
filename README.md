# Contours Bureaux de Vote

Téléchargez les contours géographiques des bureaux de vote en France au format GeoJSON pour un département, une circonscription ou une commune.

## 🚀 Application

Interface web pour rechercher et télécharger les contours géographiques des bureaux de vote en France.

## ✨ Fonctionnalités

- **Recherche rapide** par département, circonscription ou commune
- **Recherche insensible aux accents** (ex: "fleville" trouve "Fléville")
- **Export GeoJSON** pour chaque zone géographique
- **Performance optimale** avec DuckDB (lecture directe depuis Object Storage)
- **Données à jour** : 08/11/2025

## 📊 À propos des données

Ces contours ont été générés à partir du jeu de données [Bureau de vote et adresses de leurs électeurs](https://www.data.gouv.fr/fr/datasets/bureau-de-vote-et-adresses-de-leurs-electeurs/) publié par l'INSEE, issu du REU (Répertoire Electoral Unique).

### ⚠️ Précautions d'usage

La génération de ces contours est une approche qui comporte des imprécisions en raison de la nature même des données (le REU est constitué d'adresses affiliées à un bureau de vote mais n'est pas en soi une définition de contours géographiques) et de la méthode utilisée. Elle est mise à disposition pour favoriser la réutilisation des données sources de l'INSEE mais n'a pas vocation à faire autorité.

### 📐 Méthodologie

Les contours sont calculés à partir de la méthode des **Diagrammes de Voronoi** appliqués sur les adresses et calqués sur les contours des communes françaises. Le code source de génération des contours est disponible sur [GitHub](https://github.com/datagouv/bureau-vote).

### 📍 Source

Données provenant de [data.gouv.fr - Proposition de contours des bureaux de vote](https://www.data.gouv.fr/fr/datasets/proposition-de-contours-des-bureaux-de-vote/)

## 🏗️ Architecture

```
FastAPI + DuckDB + Vanilla JS
- API REST pour recherche et téléchargement
- DuckDB avec extension httpfs pour lecture directe depuis Scaleway Object Storage
- Frontend léger sans framework
- Aucun stockage local requis (données lues à la demande)
```

## 📦 Installation Locale

```bash
# Cloner le repo
git clone https://github.com/clementmandron/contours_bdv.git
cd contours_bdv

# Créer environnement virtuel
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Installer dépendances
pip install -r requirements.txt

# Lancer l'API (les données sont chargées automatiquement depuis Scaleway)
uvicorn api.main:app --reload
```

Ouvrir http://localhost:8000 dans votre navigateur.

## 🚢 Deployment

### Railway (Recommandé)

1. Créer un compte sur [Railway](https://railway.app)
2. Connecter votre repo GitHub
3. Railway détectera automatiquement la configuration
4. Déployer !

### Variables d'environnement

Aucune variable nécessaire pour le moment.

## 🔄 Stockage des données

Les données sont hébergées sur **Scaleway Object Storage** (Paris, France) et lues directement par DuckDB via l'extension httpfs.

**URL actuelle:** `https://contours-bureaux-vote.s3.fr-par.scw.cloud/20251108_contours_bureaux_vote.parquet`

Pour changer l'URL, modifier `PARQUET_URL` dans `api/main.py`

## 📚 API Endpoints

- `GET /` - Interface utilisateur
- `GET /api` - Informations sur l'API
- `GET /api/info` - Informations sur le dataset (date MAJ, source, etc.)
- `GET /search?q={query}&type={all|departement|circonscription|commune}` - Recherche (insensible aux accents)
- `GET /download/departement/{code}` - Télécharger GeoJSON d'un département
- `GET /download/circonscription/{name}` - Télécharger GeoJSON d'une circonscription
- `GET /download/commune/{code}` - Télécharger GeoJSON d'une commune

## 🛠️ Stack Technique

- **Backend**: FastAPI, DuckDB (avec extension httpfs)
- **Frontend**: HTML/CSS/JS vanilla
- **Data**: GeoPandas, Parquet
- **Storage**: Scaleway Object Storage
- **Hosting**: Railway

## 👨‍💻 Auteur

Développé par **Clément Mandron**
