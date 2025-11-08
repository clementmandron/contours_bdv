# 🇫🇷 Configuration Scaleway Object Storage

Guide pour héberger le fichier parquet sur Scaleway (Paris, France).

## Étape 1: Créer un compte Scaleway

1. Aller sur [console.scaleway.com/register](https://console.scaleway.com/register)
2. S'inscrire (carte bancaire requise mais free tier gratuit)
3. Vérifier votre email

## Étape 2: Créer un bucket Object Storage

1. Dans la console Scaleway, aller à **Storage** → **Object Storage**
2. Cliquer sur **"+ Create a bucket"**
3. Configuration du bucket:
   - **Name:** `contours-bureaux-vote` (ou votre choix)
   - **Region:** `fr-par` (Paris, France) ✅
   - **Visibility:** `Public` (pour permettre les téléchargements publics)
4. Cliquer sur **Create bucket**

## Étape 3: Uploader le fichier parquet

### Option A: Via l'interface web (Simple)

1. Cliquer sur votre bucket `contours-bureaux-vote`
2. Cliquer sur **Upload**
3. Sélectionner `data/contours_bureaux_vote.parquet` (317MB)
4. Attendre la fin de l'upload (~1-2 minutes)
5. Cliquer sur le fichier → Copier l'**Object URL**

### Option B: Via CLI (Avancé)

```bash
# Installer s3cmd
pip install s3cmd

# Configurer avec vos credentials Scaleway
s3cmd --configure

# Uploader le fichier
s3cmd put data/contours_bureaux_vote.parquet s3://contours-bureaux-vote/contours_bureaux_vote.parquet --acl-public
```

## Étape 4: Récupérer l'URL publique

L'URL aura ce format:
```
https://contours-bureaux-vote.s3.fr-par.scw.cloud/contours_bureaux_vote.parquet
```

Si vous avez choisi un autre nom de bucket, remplacez `contours-bureaux-vote`.

## Étape 5: Mettre à jour le code

Ouvrir `api/main.py` et vérifier que `PARQUET_URL` correspond à votre URL Scaleway:

```python
PARQUET_URL = "https://contours-bureaux-vote.s3.fr-par.scw.cloud/contours_bureaux_vote.parquet"
```

Si vous avez un nom de bucket différent, modifier cette ligne.

## Étape 6: Tester localement

```bash
# Supprimer le fichier local pour forcer le téléchargement
rm data/contours_bureaux_vote.parquet

# Lancer l'app
./start.sh
```

Vous devriez voir:
```
Data file not found, downloading from Scaleway Object Storage...
Downloading from https://contours-bureaux-vote.s3.fr-par.scw.cloud/...
✓ Data downloaded and saved to ...
✓ Loaded data into DuckDB
```

## 💰 Coûts

**Free tier Scaleway:**
- 75GB stockage gratuit
- 75GB bande passante gratuite/mois

**Votre usage estimé:**
- Stockage: 317MB → **€0/mois** ✅
- Bande passante: < 75GB/mois → **€0/mois** ✅

**Total: €0/mois** tant que vous restez sous 75GB de téléchargements/mois.

## 🔄 Mettre à jour les données

Quand de nouvelles données sont disponibles:

```bash
# 1. Télécharger depuis data.gouv.fr
python scripts/update_data.py

# 2. Re-uploader sur Scaleway
# Via web OU:
s3cmd put data/contours_bureaux_vote.parquet s3://contours-bureaux-vote/contours_bureaux_vote.parquet --acl-public

# 3. Redémarrer l'app Railway pour recharger
```

## ✅ Checklist

- [ ] Compte Scaleway créé
- [ ] Bucket créé en région `fr-par`
- [ ] Fichier parquet uploadé
- [ ] URL publique récupérée
- [ ] `PARQUET_URL` mis à jour dans `api/main.py`
- [ ] Test local réussi
- [ ] Déployé sur Railway

## 🆘 Aide

**Bucket pas accessible?**
- Vérifier que visibility = "Public"
- Vérifier l'URL dans votre navigateur

**Upload lent?**
- Normal pour 317MB, peut prendre 1-2 minutes

**Railway ne trouve pas le fichier?**
- Vérifier `PARQUET_URL` dans `api/main.py`
- Vérifier les logs Railway
