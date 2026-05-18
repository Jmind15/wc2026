# 🏆 Coupe du Monde 2026 Tracker

Application Flask (Python) de suivi des matchs et actualités de la Coupe du Monde FIFA 2026, avec IA Gemini intégrée.

## Stack technique
- **Backend** : Python + Flask
- **Frontend** : HTML / CSS / JS vanilla
- **IA** : Google Gemini 2.0 Flash

---

## 🚀 Lancer en local avec Anaconda

### 1. Ouvrir Anaconda Prompt (ou terminal)

### 2. Créer un environnement conda dédié

```bash
conda create -n wc2026 python=3.11 -y
conda activate wc2026
```

### 3. Installer Flask

```bash
pip install -r requirements.txt
```

### 4. Configurer la clé API Gemini

```bash
# Windows
copy .env.example .env

# Mac / Linux
cp .env.example .env
```

Éditez `.env` et remplacez `AIza...` par votre vraie clé :
```
GEMINI_API_KEY=AIza...
```

Obtenez votre clé sur → https://aistudio.google.com/apikey

### 5. Charger le .env et lancer

**Windows (Anaconda Prompt) :**
```bash
for /f "tokens=1,2 delims==" %i in (.env) do set %i=%j
python app.py
```

**Mac / Linux :**
```bash
export $(cat .env | xargs)
python app.py
```

Ouvrez → http://localhost:5000

---

## ☁️ Déployer sur Render

1. Poussez le projet sur GitHub

2. Sur [render.com](https://render.com), créez un **Web Service** :
   - **Runtime** : Python 3
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `python app.py`

3. Ajoutez la variable d'environnement :
   - `GEMINI_API_KEY` → votre clé

4. Déployez 🎉

---

## Structure du projet

```
wc2026-python/
├── app.py              ← Serveur Flask + routes API + proxy Gemini
├── requirements.txt    ← Flask uniquement (stdlib pour le reste)
├── .env.example        ← Template de configuration
├── .gitignore
└── public/
    └── index.html      ← Application frontend (tout-en-un)
```

## Routes API

| Route | Méthode | Description |
|-------|---------|-------------|
| `/api/matches` | GET | Liste des matchs |
| `/api/groupes` | GET | Classement des groupes |
| `/api/actualites?q=...` | GET | Actualités (filtre optionnel) |
| `/api/stats` | GET | Statistiques globales |
| `/api/gemini` | POST | Proxy IA (body JSON: `{ "message": "..." }`) |
"# wc2026" 
