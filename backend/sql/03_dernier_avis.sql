-- L'avis le plus récent de chaque commande (547 commandes ont plusieurs avis).
-- Sert uniquement à l'EXPLORATION (pourquoi la garantie intéresse le client) : jamais au
-- modèle, car l'avis est écrit après la livraison (ce serait une fuite).
WITH avis_classes AS (
    SELECT
        order_id,
        review_score,
        ROW_NUMBER() OVER (
            PARTITION BY order_id
            ORDER BY review_creation_date DESC, review_answer_timestamp DESC
        ) AS rang
    FROM avis
)
SELECT
    order_id     AS commande_id,
    review_score AS note
FROM avis_classes
WHERE rang = 1;
