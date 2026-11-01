-- Historique des commandes expédiées, TOUTES périodes, pour calculer les variables « trajet ».
--
-- Attention : cette requête lit la date de livraison réelle. Elle ne sert JAMAIS directement de
-- variable : backend/trajets.py n'en tire que des statistiques connues AVANT le mois d'achat
-- de la commande à évaluer (photographie au 1er jour du mois).
--
-- Même filtre que la table d'analyse (02_table_analyse.sql) : commandes livrées ou expédiées,
-- sans les 8 commandes « delivered » sans date de livraison.

SELECT
    c.order_id                                    AS commande_id,
    date(c.order_purchase_timestamp)              AS jour_achat,
    date(c.order_estimated_delivery_date)         AS jour_promis,
    date(c.order_delivered_customer_date)         AS jour_livre,
    v.seller_state                                AS etat_vendeur,
    cl.customer_state                             AS etat_client
FROM commandes AS c
JOIN articles  AS a  ON a.order_id = c.order_id AND a.order_item_id = 1
JOIN vendeurs  AS v  ON v.seller_id = a.seller_id
JOIN clients   AS cl ON cl.customer_id = c.customer_id
WHERE c.order_status IN ('delivered', 'shipped')
  AND NOT (c.order_status = 'delivered' AND c.order_delivered_customer_date IS NULL);
