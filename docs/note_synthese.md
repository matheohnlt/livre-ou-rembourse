# Note de synthèse : une garantie retard rentable pour AssurColis

Pour la direction d'AssurColis. Équipe data du Master SEP (URCA). Données Olist 2017-2018.

## La décision demandée

Nous proposons de lancer la garantie « Livré ou Remboursé » à 4 R\$ pendant un pilote de 3 mois. La garantie serait proposée selon notre règle de tri, avec au plus 20 % de refus par région. Le ratio sinistres / primes serait suivi chaque mois.

## Le contexte et la question

Près de 8 % des commandes Olist arrivent en retard ou ne sont jamais livrées. Ces retards pèsent sur les avis : 63 % des commandes en retard reçoivent 1 ou 2 étoiles contre 9 % des autres. Une étude portant sur plus de 11 millions d'achats estime la perte à 0,4 étoile par retard (Nozari et Alavi, 2026).

AssurColis souhaite vendre une garantie à 4 R\$ au moment du paiement. En cas de retard, le client récupère ses frais de port et un bon d'achat de 15 R\$. La question est de savoir à quelles commandes la proposer pour qu'elle soit rentable sans exclure les régions éloignées.

## Les résultats

Nous avons travaillé sur 97 300 commandes Olist, dont 7,8 % de sinistres. Le modèle utilise seulement les informations disponibles au paiement. La date de livraison réelle et l'avis du client en sont exclus.

Les variables qui ont le plus de poids sont la distance, le délai promis et le fait que l'acheteur soit dans un autre État que le vendeur.

Sur 53 344 commandes de 2018 que le modèle n'avait pas vues, le bénéfice passe de 5 191 R\$ à 11 049 R\$, soit 2,1 fois plus. Refuser au hasard le même nombre de commandes rapporterait seulement 4 578 R\$.

Le gain dépend de la période. Pendant la crise de janvier à mars 2018, proposer la garantie à tous fait perdre 7 147 R\$ alors que le tri limite la perte à 693 R\$. D'avril à août 2018, période plus calme, les deux options rapportent à peu près autant (12 373 R\$ et 12 338 R\$).

## La recommandation

Résultats sur les commandes de janvier à août 2018, en supposant que 20 % des clients achètent la garantie :

| **Option**                                             | **Garantie proposée à** | **Bénéfice** | **Sinistres / primes** |
|--------------------------------------------------------|-------------------------|--------------|------------------------|
| Proposer à tous (situation actuelle)                   | 100 %                   | 5 191 R\$    | 0,88                   |
| Refuser au-delà de 2 000 km                            | 97 %                    | 6 721 R\$    | 0,84                   |
| Tri sans règle d'équité                                | 73 %                    | 13 329 R\$   | 0,57                   |
| Tri avec au plus 20 % de refus par région (recommandé) | 82 %                    | 11 049 R\$   | 0,68                   |

La garantie est proposée si risque de retard × (frais de port + 15 R\$) × 1,3 est inférieur ou égal à 4 R\$. Le coefficient 1,3 correspond à la marge et aux frais.

Sans règle d'équité, 83 % des commandes du Nordeste et du Norte seraient refusées. La règle réduit le bénéfice de 2 280 R\$ mais garde l'offre accessible dans toutes les régions.

## Les limites

- Le taux de souscription de 20 % est une hypothèse. Il modifie les montants mais pas le classement des options.

- Le modèle sous-estime le risque en 2018 (7,0 % prévu contre 8,7 % observé). Il classe pourtant correctement les commandes, de 3,5 % de retards pour les plus sûres à 17,6 % pour les plus risquées.

- Les causes des retards (grèves, transporteurs, météo) ne figurent pas dans les données. Le modèle ne peut donc pas anticiper une crise et sa ROC-AUC reste de 0,64.

- L'équité est contrôlée par région et non par État. Une variante du modèle refusait jusqu'à 66 % des commandes d'un même État.

- Les données couvrent 2017 et 2018 et ne sont qu'un échantillon public d'Olist.

## Les modifications après le COMEX

| **Question du COMEX**                                                           | **Réponse apportée**                                                                                                                                                             |
|---------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Pourquoi une alerte à 0,90 ?                                                    | Avec la marge, le ratio attendu ne dépasse pas 0,77. À 0,90, il ne reste que 10 % des primes pour couvrir les frais. Au-delà de 1, la garantie perd de l'argent.                 |
| Pourquoi apprendre sur 2017 et tester sur 2018 alors qu'une crise touche 2018 ? | Nous avons testé un second découpage qui inclut la crise dans l'apprentissage. Il montre que le tri est surtout utile en période de crise.                                       |
| Le modèle est-il comparé aux retards réels ?                                    | La comparaison entre retards prévus et observés a été ajoutée au dossier.                                                                                                        |
| Comment obtenir des données de météo et de grèves ?                             | Deux sources ont été identifiées : les relevés quotidiens de l'INMET et le suivi des grèves du DIEESE. Seules les informations connues au moment du paiement seraient utilisées. |

## Le suivi

| **Indicateur**                       | **Fréquence** | **Seuil d'alerte**                                        | **Responsable**        |
|--------------------------------------|---------------|-----------------------------------------------------------|------------------------|
| Ratio sinistres / primes             | Mensuelle     | Au-dessus de 0,90                                         | Direction financière   |
| Taux de retard                       | Mensuelle     | Écart de plus de 3 points avec la période d'apprentissage | Équipe data            |
| Taux de souscription                 | Mensuelle     | Écart important avec 20 %                                 | Marketing              |
| Part de refus par région et par État | Trimestrielle | Plus de 20 %                                              | Protection des données |

Pendant le pilote, les clients seront répartis par tirage au sort. Une moitié recevra l'offre selon notre règle et l'autre la recevra systématiquement. Cette comparaison mesurera le gain réel du tri.
