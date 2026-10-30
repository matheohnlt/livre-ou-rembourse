# Note de cadrage : Livré ou Remboursé

**Équipe :** Aziz, [prénoms à compléter] · **Dataset :** [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (Kaggle, CC BY-NC-SA 4.0) · **Client imaginé :** AssurColis, assurtech fictive partenaire de la marketplace Olist ; la décision revient à la directrice produit.

## 1. La question business, en 2 lignes

AssurColis veut proposer au paiement une garantie « Livré ou Remboursé » : si le colis arrive après la date promise, le client récupère ses frais de port et un bon de 15 R$. **Quel prix afficher pour chaque commande pour que la garantie soit rentable, sans pénaliser excessivement les clients des régions éloignées ?**

## 2. Les 5 questions du cours 1

| Question | Votre réponse |
|---|---|
| Qu'appelle-t-on exactement la cible ? | Un **sinistre** = une commande expédiée livrée **après la date promise** (`order_delivered_customer_date` > `order_estimated_delivery_date`, au jour près) **ou jamais livrée** (statut « shipped » sans date de livraison : colis perdu). 6,8 % des commandes en 2017, 8,7 % entre janvier et août 2018. |
| Que fera le client du résultat ? | Au moment du paiement, la page affiche la garantie à l'un des **3 prix** (2, 4 ou 8 R$) selon le risque de la commande. Le client l'achète ou non. |
| Combien de cas peut-il traiter ? | Toutes les commandes sont tarifées automatiquement : pas de limite de capacité. La contrainte est **un prix plafonné à 8 R$** (équité). |
| Combien coûte une erreur, combien rapporte une bonne décision ? | Un sinistre coûte **les frais de port de la commande + 15 R$** (37,8 R$ en moyenne). Prix trop bas sur une commande risquée : l'assureur perd de l'argent. Prix trop haut sur une commande sûre : le client n'achète pas (perte de prime). |
| Quelles données, depuis quand, et qui les connaît ? | 99 441 commandes Olist, de septembre 2016 à octobre 2018, en 9 tables. Données réelles anonymisées, documentées sur Kaggle. |

## 3. Les familles de méthodes prévues

| Famille (carte du data mining) | Pour répondre à quelle question du client ? |
|---|---|
| Supervisé : **classification** (régression logistique, Random Forest) | Quelle est la probabilité de sinistre de cette commande, **au moment du paiement** ? |
| Non supervisé : **K-means** (bonus) | Quels profils de commandes à risque (routes longues, colis lourds, vendeurs lents) ? |
| Bonus (associations, anomalies) | Non prévu. |

## 4. Comment saura-t-on que ça marche ?

- **Baseline** (ce qu'on fait sans modèle) : **un prix unique de 4 R$ pour tous**. Le coût moyen d'un sinistre par commande est de 3,14 R$ ; avec 30 % de marge et de frais, on arrive à 4 R$. Deuxième référence : une règle simple fondée sur la distance vendeur → client.
- **Métriques qui comptent pour le client :**
  - le **bénéfice** en R$ ;
  - le **ratio sinistres / primes** global et par niveau de prix (le prix est-il juste pour chaque groupe ?) ;
  - la **calibration** des probabilités, puisqu'elles servent à calculer un prix.
  - En appui : ROC-AUC et PR-AUC (événement rare, environ 7 %).
- **Validation :** split **temporel**. Entraînement sur 2017 (43 958 commandes), test de janvier à août 2018 (53 350 commandes). Réglages par validation croisée temporelle sur 2017 uniquement.
- **Succès :** sur 2018, un bénéfice supérieur au prix unique, avec un ratio sinistres / primes proche de la cible dans chacun des 3 niveaux de prix.

## 5. Les risques déjà vus

- **Fuite de données :** seules les informations connues **au paiement** sont autorisées. Sont exclus la date de livraison réelle, la date de remise au transporteur, l'avis du client et le statut final de la commande.
- **Équité :** le risque dépend fortement de la région (le Nord et le Nord-Est sont plus éloignés et plus pauvres). Le prix est donc plafonné à 8 R$, et un écran vérifie le prix moyen par région.
- **Crises imprévisibles :** retards de 15 à 20 % en février et mars 2018, contre 6 % habituellement. Le modèle ne peut pas prévoir ce risque : il faut une règle de surveillance et de réentraînement.
- **Hypothèses non observées :** la part des clients qui achèteraient la garantie, selon son prix, n'existe pas dans les données. Elle est fixée dans `config.py` et réglable dans le simulateur.
- **Données à fiabiliser :** plusieurs articles, paiements et avis par commande ; plusieurs points GPS par code postal ; 1 107 colis jamais livrés.

## 6. Qui fait quoi

| Membre | Rôle principal (SQL et données, modèle, application, documents et soutenance) |
|---|---|
| Aziz | SQL et données, modèle, application, documents |
| [à compléter] | [à compléter] |
