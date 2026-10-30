# Note de cadrage : Livré ou Remboursé

**Équipe :** Aziz, [prénoms à compléter] · **Dataset :** [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (Kaggle, CC BY-NC-SA 4.0) · **Client imaginé :** AssurColis, assurtech fictive partenaire de la marketplace Olist ; la décision revient à la directrice produit.

## 1. La question business, en 2 lignes

AssurColis veut proposer au paiement une garantie « Livré ou Remboursé » à 4 R$ : si le colis arrive après la date promise, le client récupère ses frais de port et un bon de 15 R$. **À quelles commandes proposer la garantie pour qu'elle soit rentable, sans exclure les clients des régions éloignées ?**

## 2. Les 5 questions du cours 1

| Question | Votre réponse |
|---|---|
| Qu'appelle-t-on exactement la cible ? | Un **sinistre** = une commande expédiée livrée **après la date promise** (`order_delivered_customer_date` > `order_estimated_delivery_date`, au jour près) **ou jamais livrée** (statut « shipped » sans date de livraison : colis perdu). 6,8 % des commandes en 2017, 8,7 % entre janvier et août 2018. |
| Que fera le client du résultat ? | Au moment du paiement, la page **affiche ou non** la garantie à 4 R$ selon le risque de la commande. Le client l'achète ou non. |
| Combien de cas peut-il traiter ? | Toutes les commandes sont évaluées automatiquement : pas de limite de capacité. La contrainte est l'**équité : au plus 20 % de refus dans chaque région** du Brésil. |
| Combien coûte une erreur, combien rapporte une bonne décision ? | Un sinistre coûte **les frais de port de la commande + 15 R$** (37,8 R$ en moyenne). Une garantie vendue rapporte 4 R$. Proposer à une commande trop risquée fait perdre de l'argent ; refuser une commande sûre fait perdre une prime. On propose si **probabilité × indemnité × 1,3 ≤ 4 R$** (1,3 = marge et frais de l'assureur). |
| Quelles données, depuis quand, et qui les connaît ? | 99 441 commandes Olist, de septembre 2016 à octobre 2018, en 9 tables. Données réelles anonymisées, documentées sur Kaggle. |

## 3. Les familles de méthodes prévues

| Famille (carte du data mining) | Pour répondre à quelle question du client ? |
|---|---|
| Supervisé : **classification** (régression logistique, Random Forest) | Quelle est la probabilité de sinistre de cette commande, **au moment du paiement** ? |
| Non supervisé : **K-means** (bonus) | Quels profils de commandes à risque (routes longues, colis lourds, vendeurs lents) ? |
| Bonus (associations, anomalies) | Non prévu. |

## 4. Comment saura-t-on que ça marche ?

- **Baseline** (ce qu'on fait sans modèle) : **proposer la garantie à tous à 4 R$**. En 2017, un sinistre coûte en moyenne 2,68 R$ par commande ; avec 30 % de marge et de frais, on arrive à 3,49 R$, arrondi au prix commercial de 4 R$. Deuxième référence : une règle simple (refuser au-delà de 2 000 km). Contrôle : refuser au hasard autant de commandes que le modèle.
- **Métriques qui comptent pour le client :**
  - le **bénéfice** en R$ ;
  - le **ratio sinistres / primes** (combien l'assureur rembourse pour 100 R$ encaissés) ;
  - la **part refusée par région** (équité) ;
  - la **calibration** des probabilités, puisqu'elles servent à calculer un coût.
  - En appui : ROC-AUC et PR-AUC (événement rare, environ 7 %).
- **Validation :** split **temporel**. Choix du modèle sur une validation interne à 2017 (appris de janvier à septembre, jugé d'octobre à décembre), validation croisée temporelle sur 2017, puis entraînement sur tout 2017 (43 956 commandes) et test, regardé une seule fois, de janvier à août 2018 (53 344 commandes).
- **Succès :** sur 2018, un bénéfice nettement supérieur à « proposer à tous » et au refus au hasard, avec au plus 20 % de refus dans chaque région.

## 5. Les risques déjà vus

- **Fuite de données :** seules les informations connues **au paiement** sont autorisées. Sont exclus la date de livraison réelle, la date de remise au transporteur, l'avis du client et le statut final de la commande.
- **Équité :** le risque dépend fortement de la région (le Nord et le Nord-Est sont plus éloignés et plus pauvres). Sans précaution, le modèle refuserait plus de 80 % de leurs commandes. D'où le plafond de 20 % de refus par région, et l'État du client exclu des variables du modèle.
- **Crises imprévisibles :** retards de 15 à 20 % en février et mars 2018, contre 6 % habituellement. Le modèle ne peut pas prévoir ce risque : il faut une règle de surveillance et de réentraînement.
- **Hypothèses non observées :** la part des clients qui achèteraient la garantie (20 % par défaut) n'existe pas dans les données. Elle multiplie tous les bénéfices sans changer le classement des stratégies. Elle est fixée dans `config.py` et réglable dans le simulateur.
- **Données à fiabiliser :** plusieurs articles, paiements et avis par commande ; plusieurs points GPS par code postal ; 1 107 colis jamais livrés.

## 6. Qui fait quoi

| Membre | Rôle principal (SQL et données, modèle, application, documents et soutenance) |
|---|---|
| Aziz | SQL et données, modèle, application, documents |
| [à compléter] | [à compléter] |
