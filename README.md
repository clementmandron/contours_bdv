# Contours Bureaux de Vote

Téléchargez les contours géographiques des bureaux de vote en France au format GeoJSON pour un département, une circonscription ou une commune.

**Application en ligne** : https://contoursbdvprod69q919vs-contours-bdv-prod.functions.fnc.fr-par.scw.cloud

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
├── api/main.py      # API REST (recherche, téléchargement GeoJSON)
├── static/          # Frontend HTML/CSS/JS
├── Dockerfile       # Image Docker optimisée pour serverless
└── .env.example     # Template de configuration
```

- **DuckDB** avec extension `httpfs` pour lecture directe depuis Scaleway Object Storage
- **Aucun stockage local requis** : données lues à la demande via HTTP
- **Serverless-ready** : cold start ~3-5s, scale to zero

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

# Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec l'URL du fichier parquet

# Lancer l'API
uvicorn api.main:app --reload
```

Ouvrir http://localhost:8000 dans votre navigateur.

## 🚢 Déploiement

### Variables d'environnement

| Variable | Description | Requis |
|----------|-------------|--------|
| `PARQUET_URL` | URL du fichier parquet des contours de bureaux de vote | Oui |

### Docker

```bash
# Build l'image
docker build -t contours-bdv .

# Option 1 : Run avec --env-file (recommandé)
docker run -p 8000:8000 --env-file .env contours-bdv

# Option 2 : Run avec variable explicite
docker run -p 8000:8000 \
  -e PARQUET_URL="https://mon-bucket.s3.fr-par.scw.cloud/contours.parquet" \
  contours-bdv
```

### Scaleway Serverless Containers

```bash
# 1. Se connecter au registry Scaleway
docker login rg.fr-par.scw.cloud/<namespace> -u nologin --password-stdin <<< "$SCW_SECRET_KEY"

# 2. Build l'image
docker build -t rg.fr-par.scw.cloud/<namespace>/app:latest .

# 3. Push vers le registry
docker push rg.fr-par.scw.cloud/<namespace>/app:latest

# 4. Créer le container serverless via l'interface web Scaleway :
#    - Image: rg.fr-par.scw.cloud/<namespace>/app:latest
#    - Port: 8000
#    - Memory: 1024 MB
#    - vCPU: 1000 mVCPU
#    - Min scale: 0 (scale to zero)
#    - Privacy: Public
#    - Variables d'environnement: PARQUET_URL
```

## 🔄 Stockage des données

Les données sont hébergées sur **Scaleway Object Storage** (Paris, France) et lues directement par DuckDB via l'extension httpfs. L'URL est configurée via la variable d'environnement `PARQUET_URL` (voir `.env.example`).

## 📚 API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Interface utilisateur |
| `GET /api` | Informations sur l'API |
| `GET /api/info` | Informations sur le dataset (date MAJ, source) |
| `GET /search?q={query}&type={type}` | Recherche (type: all, departement, circonscription, commune) |
| `GET /download/departement/{code}` | Télécharger GeoJSON d'un département |
| `GET /download/circonscription/{dept}/{name}` | Télécharger GeoJSON d'une circonscription |
| `GET /download/commune/{code}` | Télécharger GeoJSON d'une commune |

## 🛠️ Stack Technique

- **Backend** : FastAPI, DuckDB (avec extensions httpfs et spatial)
- **Frontend** : HTML/CSS/JS vanilla
- **Storage** : Scaleway Object Storage (Parquet)
- **Hosting** : Scaleway Serverless Containers

## 👨‍💻 Auteur

Développé par **Clément Mandron**

## Licence

MIT License

Copyright (c) 2025 Clément Mandron

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
