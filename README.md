# 🏆 Coupe du Monde 2026 — Streamlit

## Lancer en local (Anaconda)

```bash
conda create -n wc2026 python=3.11 -y
conda activate wc2026
pip install -r requirements.txt
```

Éditez `.streamlit/secrets.toml` avec vos clés, puis :

```bash
streamlit run app.py
```

## Déployer sur Streamlit Cloud

1. Pousse le projet sur GitHub
2. Va sur **share.streamlit.io**
3. Clique **"New app"** → sélectionne ton repo
4. Dans **"Advanced settings" → "Secrets"**, ajoute :
```
FOOTBALLDATA_KEY = "ta_cle_ici"
GEMINI_API_KEY = "AIza..."
```
5. Déploie 🚀
