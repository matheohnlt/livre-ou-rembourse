# Data Quality Card : Olist, commandes expédiées 2017-2018

> Inspirée de Gebru et al. (2021), *Datasheets for Datasets*. Règle suivie : chaque défaut a un chiffre et un traitement.
> Tous les chiffres sont reproduits par `python -m backend.data` et vérifiés par `tests/test_data.py`.

## Identité

| Question | Réponse |
|---|---|
| Unité d'observation (une ligne = ?) | Une **commande expédiée**, vue au moment du paiement |
| Source, licence, lien | [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), Kaggle, licence CC BY-NC-SA 4.0 (usage non commercial, avec attribution). Archive versionnée telle quelle dans `data/raw/olist.zip`. |
| Période et population couvertes | Commandes passées du 05/01/2017 au 29/08/2018 sur la marketplace Olist (Brésil), aux statuts « delivered » ou « shipped ». Les données s'arrêtent le 17/10/2018. |
| Taille (lignes × colonnes) | Base brute : 9 tables, dont 99 441 commandes et 112 650 articles. Table d'analyse : **97 300 commandes × 22 colonnes**, construite en SQL (`backend/sql/02_table_analyse.sql`). |
| Cible : définition, construction, répartition | `sinistre` = 1 si la commande est livrée **après la date promise** (au jour près) **ou jamais livrée**. Construite en SQL. **7,8 %** des commandes : 6,8 % en 2017 (entraînement, 43 956 commandes) et 8,7 % de janvier à août 2018 (test, 53 344 commandes). |

## Défauts trouvés et ce qu'on en fait

| Défaut | Combien (chiffre et %) | Comment on l'a vu | Ce qu'on en fait, et pourquoi |
|---|---|---|---|
| Plusieurs articles par commande | 112 650 articles pour 98 666 commandes ; 1 274 commandes à plusieurs vendeurs | Clé primaire (`order_id`, `order_item_id`) | Agrégés à une ligne par commande **avant** la jointure (CTE `resume_articles`). Sinon, le JOIN multiplie les lignes. Testé : `commande_id` unique. |
| Plusieurs paiements par commande | 103 886 paiements pour 99 440 commandes | `GROUP BY order_id` | Agrégés : type du premier paiement, nombre maximal de mensualités |
| Plusieurs points GPS par code postal | 1 000 163 points pour 19 015 codes postaux | `GROUP BY geolocation_zip_code_prefix` | Moyenne des points par code postal (CTE `geo`) |
| Points GPS hors du Brésil | 42 points sur 1 000 163 (< 0,01 %), qui touchaient 9 commandes (latitude jusqu'à +42, soit en Europe) | Latitude et longitude hors du cadre du Brésil | Écartés en SQL avant la moyenne. Distance maximale après correction : 3 580 km, plausible. |
| Distance manquante (code postal sans point GPS) | 486 commandes (0,5 %) | `isna().sum()` | Complétée dans le pipeline du modèle par la médiane **calculée sur 2017 uniquement**, pour éviter la fuite |
| Poids impossible (0 g) ou manquant | 6 commandes à 0 g, 16 sans poids ; 22 au total après correction (< 0,1 %) | `describe()`, `isna()` | 0 g passe à manquant en SQL, puis médiane de 2017 dans le pipeline |
| Mode de paiement manquant | 78 commandes (0,1 %) | `isna()` | Modalité « inconnu » en SQL : l'absence peut porter une information |
| 0 mensualité | 2 commandes | `describe()` | Ramené à 1 (paiement comptant) en SQL |
| Modalité qui joue le rôle d'un manquant | Catégorie absente : 1 381 commandes (1,4 %) | `value_counts()` | Gardée comme modalité « inconnue » |
| Frais de port à 0 | 338 commandes (0,3 %) | `describe()` | Gardées : c'est une livraison gratuite, valeur plausible. L'indemnité vaut alors seulement le bon de 15 R$. |
| Statut et date contradictoires | 8 commandes « delivered » sans date de livraison | Requête sur `order_status` et `order_delivered_customer_date` | Exclues : impossible de savoir si elles sont arrivées à l'heure |
| Colis jamais livrés | 1 097 commandes « shipped » sans date de livraison (1,1 %) | `order_status = 'shipped'` | Comptés comme **sinistres** : pour l'assureur, un colis perdu est le pire des retards. Vérifié : leur date promise est toujours antérieure à la fin des données, il n'y a donc pas de censure. |
| Avis multiples | 547 commandes ont plusieurs avis ; 789 `review_id` en double ; 716 commandes sans avis | `GROUP BY ... HAVING COUNT(*) > 1` | Les avis ne servent **pas** au modèle (ce serait une fuite). Pour l'exploration, on garde l'avis le plus récent. |
| Classes déséquilibrées | 7,8 % de sinistres | `value_counts(normalize=True)` | Métriques adaptées (PR-AUC, calibration, bénéfice), split stratifié dans la validation croisée, pas d'accuracy |
| Instabilité dans le temps | Taux mensuel entre 1,9 % (juin 2018) et 20,5 % (mars 2018) ; 13,3 % en novembre 2017 (Black Friday) ; 14,9 % en février 2018 | `GROUP BY` mois | Split temporel obligatoire. Les pics sont présentés comme une limite, avec une règle de surveillance (voir la Model Card). |

## Les pièges pour le modèle

| Question | Réponse |
|---|---|
| Variables à risque de **fuite** (connues seulement après la décision) | **Exclues de la table d'analyse** et vérifiées par un test : date de livraison réelle, date de remise au transporteur, date de validation du paiement, statut final de la commande, avis et commentaires. Ces informations servent seulement à construire la cible. |
| Variables sensibles (sexe, origine, santé, âge...) | Aucune donnée personnelle de ce type. En revanche, l'**État du client** est un indicateur indirect de la richesse et de l'éloignement de la région : le taux de sinistre va de 2,9 % (Rondônia) à 23,2 % (Alagoas). Décision : l'État (et les coordonnées GPS) ne sont **pas** des variables du modèle, et la décision respecte **au plus 20 % de refus par région**, vérifiés sur le test (écran d'équité). |
| Biais de sélection (qui manque dans les données ?) | Seules les commandes **passées sur Olist** sont observées (pas les paniers abandonnés). On ignore donc combien de clients achèteraient la garantie : c'est une hypothèse dans `config.py` (20 %). Les données sont un échantillon public fourni par Olist, pas l'intégralité de son activité. |
| Données personnelles : base légale, anonymisation | Identifiants anonymisés (hachés) ; aucun nom, adresse ou e-mail. Le code postal est tronqué à 5 chiffres. L'usage est pédagogique et non commercial, conforme à la licence. |

## Ce qu'on attend des données

- **Les variables qui devraient être les plus utiles, et pourquoi :** la **distance** vendeur → client et le **délai promis** (plus le trajet est long, plus le retard est probable) ; le **mois** d'achat (pics du Black Friday et du début 2018) ; le **poids** et le **nombre de vendeurs** (logistique plus complexe). L'**historique de retard du vendeur** (calculé seulement sur ses commandes livrées avant l'achat) et le **mois d'achat** ont été essayés : ils n'améliorent pas la validation, et ils sont donc écartés.
- **Pourquoi la garantie a de la valeur pour le client :** 63,4 % des commandes en sinistre reçoivent un avis de 1 ou 2 étoiles, contre 9,2 % des autres (96 584 commandes avec avis).
- **Ce que les données ne permettent pas de dire :**
  - la **cause** d'un retard (grève, transporteur, vendeur) ;
  - la réaction des clients au prix de la garantie ;
  - les crises à venir : la flambée de février-mars 2018 n'était pas visible dans les données de 2017.
