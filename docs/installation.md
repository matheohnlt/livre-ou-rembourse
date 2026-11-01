# Installer et lancer le projet, étape par étape

Ce guide part d'un ordinateur sans le projet. Comptez 5 minutes, dont environ 1 minute d'entraînement du modèle.

## Avant de commencer

- **Python 3.12.** Vérifiez avec `python --version`. Si vous n'avez pas Python 3.12, installez-le depuis [python.org](https://www.python.org/downloads/) et cochez « Add Python to PATH » pendant l'installation sous Windows.
- **Git.** Vérifiez avec `git --version`.
- Tapez toutes les commandes dans un terminal (PowerShell sous Windows, Terminal sous Mac), **depuis le dossier `data_mining_m2`**, la racine du projet, jamais depuis `backend/` ou `frontend/`.

## 1. Récupérer le projet

Si vous n'avez pas encore le dépôt :

```bash
git clone https://gitlab-mi.univ-reims.fr/hena0006/data_mining_m2.git
cd data_mining_m2
git checkout feat/livre-ou-rembourse
```

Si vous avez déjà le dépôt :

```bash
cd data_mining_m2
git fetch
git checkout feat/livre-ou-rembourse
git pull
```

## 2. Créer l'environnement Python (une seule fois)

```bash
python -m venv .venv
```

Puis activez-le. **À refaire à chaque nouveau terminal.**

| Système | Commande |
|---|---|
| Windows (PowerShell) | `.venv\Scripts\activate` |
| Mac ou Linux | `source .venv/bin/activate` |

Le début de la ligne du terminal affiche alors `(.venv)`.

Installez ensuite les paquets :

```bash
pip install -r requirements.txt
```

## 3. Entraîner le modèle

```bash
python -m backend.train
```

Cette commande charge les données dans SQLite (en SQL), choisit le modèle, l'évalue sur 2018 et sauvegarde le tout dans `models/`. Elle dure environ 1 minute.

À la fin, vous devez voir notamment :

```
Modèle retenu (sur la validation 2017) : foret_100
  modèle, plafond de refus par région (recommandé)   proposée à  81.8%  bénéfice    11,049 R$  S/P 0.68
```

Un avertissement `OptimizeWarning: Unknown solver options: iprint` peut s'afficher. Il est sans effet sur les résultats.

## 4. Lancer les tests

```bash
python -m pytest
```

Résultat attendu : `18 passed`. Le test de démarrage de l'application peut prendre une minute.

## 5. Ouvrir l'application

```bash
python -m streamlit run frontend/app.py
```

L'application s'ouvre dans le navigateur, à l'adresse `http://localhost:8501`. Au premier lancement, Streamlit peut demander une adresse e-mail : appuyez simplement sur Entrée.

Pour arrêter l'application, revenez dans le terminal et appuyez sur `Ctrl + C`.

## Les prochaines fois

Il suffit d'ouvrir un terminal dans `data_mining_m2`, d'activer l'environnement, puis de lancer l'application :

```bash
.venv\Scripts\activate                    # Windows ; sous Mac ou Linux : source .venv/bin/activate
python -m streamlit run frontend/app.py
```

Relancez `python -m backend.train` seulement si le code du backend ou les données ont changé.

## En cas de problème

| Message | Cause | Solution |
|---|---|---|
| `No module named 'backend'` | La commande est lancée depuis le mauvais dossier | Revenez à la racine `data_mining_m2`, puis relancez |
| `No module named 'pandas'` (ou `streamlit`, `sklearn`) | L'environnement n'est pas activé, ou les paquets ne sont pas installés | Activez `.venv`, puis `pip install -r requirements.txt` |
| `Modèle absent. Lancer d'abord : python -m backend.train` | Le modèle n'a pas encore été entraîné | `python -m backend.train` |
| `Archive introuvable : data/raw/olist.zip` | Les données ne sont pas là (ancienne branche, ou clone incomplet) | Vérifiez que vous êtes sur `feat/livre-ou-rembourse`, puis `git pull` |
| Sous Windows : « l'exécution de scripts est désactivée sur ce système » à l'activation | Une règle de sécurité de PowerShell | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, répondez « O », puis réactivez |
| `pip install` échoue sur un paquet | Version de Python différente de 3.12 | Installez Python 3.12 et recréez `.venv` |
