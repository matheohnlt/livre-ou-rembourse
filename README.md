# 📦 Livré ou Remboursé : une garantie retard rentable et équitable

Projet du cours Data Mining 1 (Master SEP, URCA). Client fictif : **AssurColis**, assurtech partenaire de la marketplace Olist. Données réelles : [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (CC BY-NC-SA 4.0).

## Question business

AssurColis veut proposer au paiement une garantie à **4 R$** : si le colis arrive après la date promise, le client récupère ses frais de port et un bon de 15 R$. **À quelles commandes proposer la garantie pour qu'elle soit rentable, sans exclure les clients des régions éloignées ?**

## Résultats (test : janvier à août 2018, 53 344 commandes jamais vues par le modèle)

Hypothèse : 20 % des clients achètent la garantie quand elle leur est proposée. Elle change les montants, pas le classement.

| Stratégie | Garantie proposée à | Bénéfice | Sinistres / primes |
|---|---|---|---|
| Proposer à tous (situation sans modèle) | 100 % | 5 191 R$ | 0,88 |
| Règle simple : refuser au-delà de 2 000 km | 98 % | 6 209 R$ | 0,85 |
| Contrôle : refuser au hasard autant que le modèle | 84 % | 4 295 R$ | 0,88 |
| Modèle sans règle d'équité | 61 % | 14 428 R$ | 0,44 |
| Modèle + au plus 20 % de refus par région (ancienne règle) | 80 % | 12 238 R$ | 0,64 |
| **Modèle + au plus 20 % de refus par État (recommandé)** | **84 %** | **9 417 R$** | **0,74** |

- **Le bénéfice est multiplié par 1,8.** Le gain vient bien du modèle : refuser au hasard le même nombre de commandes ne rapporte rien.
- **L'équité coûte 5 011 R$.** Sans la règle, 94 % des commandes du Nordeste et 88 % de celles du Norte seraient refusées. Un plafond par région ne suffit pas : il laisserait refuser 66 % des commandes d'Espírito Santo et 58 % de celles de Rio de Janeiro. Avec le plafond par État, chaque État a au plus 20 % de refus.
- **Modèle :** régression logistique avec 12 variables, choisie sur deux validations 2017 (ROC-AUC moyenne). ROC-AUC de 0,67 sur le test, de 0,64 ± 0,03 en validation croisée temporelle ; PR-AUC de 0,150 contre 0,087 au hasard.
- **Variables les plus utilisées :** la marge du délai promis (délai promis moins délai habituel du trajet), le taux de retard passé du trajet, le délai promis et le fait d'être dans le même État (importance par permutation).
- **5 profils de commandes (K-means, bonus) :** le plus risqué en 2018 est le « petit colis entre États » (11,7 % de retards), pas le « grand voyageur » (7,0 %), à qui Olist promet déjà un long délai.
- **63 % des commandes en retard reçoivent un avis de 1 ou 2 étoiles, contre 9 % des autres :** la garantie répond à un vrai besoin.

## Lancer le projet

Dans un environnement virtuel Python 3.12 (`python -m venv .venv`, puis `.venv\Scripts\activate` sous Windows ou `source .venv/bin/activate` sous Mac et Linux) :

```bash
pip install -r requirements.txt
python -m backend.train                  # archive -> SQLite (SQL) -> choix du modèle -> test 2018 (environ 1 min)
python -m pytest                         # 23 tests
python -m streamlit run frontend/app.py  # démonstrateur, 5 écrans
```

**Première installation, pas à pas** (récupérer la branche, créer l'environnement, résoudre les erreurs fréquentes) : voir le [guide d'installation](docs/installation.md).

**Données :** l'archive Kaggle d'origine est versionnée telle quelle dans `data/raw/olist.zip` (45 Mo, jamais modifiée). Elle est lue directement, sans décompression ni clé Kaggle.

## Architecture : backend et frontend séparés

```
backend/                       logique métier (aucun import de streamlit)
  config.py                    chemins, seed, périodes, prix, bon, marge, plafond d'équité
  sql/01_creation_tables.sql   les 9 tables Olist dans SQLite (types, clés primaires)
  sql/02_table_analyse.sql     table d'analyse : une ligne par commande, infos connues au paiement
  sql/03_dernier_avis.sql      dernier avis par commande (fonction de fenêtre), exploration seulement
  data.py                      archive -> SQLite -> table d'analyse ; distance vendeur -> client
  model.py                     variables, modèles, décision d'éligibilité, règle d'équité, métriques
  segmentation.py              K-means et personas (bonus non supervisé)
  train.py                     python -m backend.train : choix sur validation 2017, test 2018, sauvegarde
  service.py                   SEULE interface appelée par le frontend
frontend/
  app.py                       Streamlit : 5 onglets, affichage et saisie uniquement
  view/                        Devis, Simulateur, Exploration, Équité, Le modèle
tests/                         données, logique métier, service, démarrage de l'appli
docs/                          note de cadrage, Data Quality Card, Model Card, journal IA, note de synthèse
data/raw/olist.zip             données brutes
```

**Règle :** le frontend n'importe que `backend.service`, ce qu'un test vérifie. Sans le frontend, `python -m backend.train` fait tout le travail.

## Les 5 écrans

| Écran | Pour qui | Ce qu'il montre |
|---|---|---|
| 🛒 Devis | Service client, démo | Une commande → risque de retard, coût attendu, garantie proposée ou non, et pourquoi |
| 💰 Simulateur | DAF | Bénéfice et ratio sinistres / primes selon le prix, le bon, la marge, la souscription et le plafond |
| 🗺️ Exploration | Marketing | Retards et mauvais avis, évolution mensuelle, carte par État, 5 personas |
| ⚖️ Équité | DPO | Refus par région et par État avec et sans la règle, coût de l'équité, seuils par État |
| 🧠 Le modèle | DSI, jury | Choix du modèle, performances, calibration, variables importantes, limites |

## Limites

- **Hypothèse non observable :** la part de clients qui achèteraient la garantie (20 %), et le fait qu'elle soit la même quel que soit le risque du client.
- **Le modèle surestime le risque des commandes les plus risquées** (22 % prédit contre 17,6 % observé dans la tranche la plus risquée) ; en moyenne, il prédit 9,0 % de retards pour 8,7 % observés. Il classe bien : de 2,1 % à 17,6 % de retards entre la tranche la plus sûre et la plus risquée.
- **Les variables « trajet » renseignent indirectement sur l'État du client.** C'est pourquoi la règle d'équité plafonne les refus dans chaque État, et pas seulement dans chaque région.
- **Il ne prévoit pas les crises :** en février-mars 2018, les retards ont triplé. D'où le suivi mensuel et la règle de réentraînement (voir `docs/model_card.md`).
- **Une ROC-AUC de 0,67 reste modeste :** les causes des retards (grèves, transporteur, météo) ne sont pas dans les données.
- **Les données datent de 2017-2018** et forment un échantillon public d'Olist.

## Retours du COMEX et ce que nous avons changé

*À compléter après la soutenance du J3.*

| Retour | Ce que nous avons changé |
|---|---|
| | |

## Documents

[Guide d'installation](docs/installation.md) · [Note de cadrage](docs/note_cadrage.md) · [Data Quality Card](docs/data_quality_card.md) · [Model Card](docs/model_card.md) · [Journal d'usage de l'IA](docs/journal_ia.md)
