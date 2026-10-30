-- Table d'analyse : UNE LIGNE PAR COMMANDE EXPÉDIÉE, avec la cible `sinistre`.
--
-- Règle anti-fuite : on ne garde que des informations connues AU MOMENT DU PAIEMENT,
-- quand le client voit la garantie. Sont donc exclus : la date de livraison réelle, la date
-- de remise au transporteur, l'avis du client et le statut final (ils servent seulement à
-- construire la cible).
--
-- Paramètres : :date_debut (incluse) et :date_fin (exclue), fournis par backend/config.py.

WITH
-- 1. Les commandes expédiées sur la période. Les commandes annulées ou jamais expédiées
--    sont exclues (la garantie serait remboursée). 8 commandes « delivered » sans date de
--    livraison sont exclues : statut et date se contredisent, on ne sait pas les classer.
commandes_expediees AS (
    SELECT *
    FROM commandes
    WHERE order_status IN ('delivered', 'shipped')
      AND NOT (order_status = 'delivered' AND order_delivered_customer_date IS NULL)
      AND order_purchase_timestamp >= :date_debut
      AND order_purchase_timestamp < :date_fin
),

-- 2. Les articles résumés à une ligne par commande (sinon le JOIN multiplie les lignes).
resume_articles AS (
    SELECT
        a.order_id,
        COUNT(*)                     AS nb_articles,
        COUNT(DISTINCT a.seller_id)  AS nb_vendeurs,
        COUNT(DISTINCT a.product_id) AS nb_produits,
        SUM(a.price)                 AS prix_total,
        SUM(a.freight_value)         AS frais_port,
        -- Un poids de 0 g est impossible : traité comme manquant (NULL).
        SUM(NULLIF(p.product_weight_g, 0)) AS poids_total_g,
        SUM(p.product_length_cm * p.product_height_cm * p.product_width_cm) AS volume_total_cm3
    FROM articles AS a
    LEFT JOIN produits AS p ON p.product_id = a.product_id
    GROUP BY a.order_id
),

-- 3. Le vendeur et la catégorie du premier article de la commande.
article_principal AS (
    SELECT
        a.order_id,
        a.seller_id,
        COALESCE(c.product_category_name_english, p.product_category_name, 'inconnue') AS categorie
    FROM articles AS a
    LEFT JOIN produits AS p ON p.product_id = a.product_id
    LEFT JOIN categories AS c ON c.product_category_name = p.product_category_name
    WHERE a.order_item_id = 1
),

-- 4. Le mode de paiement choisi au paiement (premier paiement) et le nombre de mensualités.
--    0 mensualité est impossible : ramené à 1 (paiement comptant).
resume_paiements AS (
    SELECT
        order_id,
        MAX(CASE WHEN payment_sequential = 1 THEN payment_type END) AS type_paiement,
        MAX(MAX(payment_installments), 1)                             AS nb_mensualites
    FROM paiements
    GROUP BY order_id
),

-- 5. Un seul point GPS par code postal : la moyenne des points disponibles, en écartant
--    les 42 points situés hors du Brésil (erreurs de géocodage).
geo AS (
    SELECT
        geolocation_zip_code_prefix AS code_postal,
        AVG(geolocation_lat)        AS lat,
        AVG(geolocation_lng)        AS lng
    FROM geolocalisation
    WHERE geolocation_lat BETWEEN -34.0 AND 5.3
      AND geolocation_lng BETWEEN -74.0 AND -34.7
    GROUP BY geolocation_zip_code_prefix
)

SELECT
    c.order_id                 AS commande_id,
    c.order_purchase_timestamp AS date_achat,
    CAST(julianday(date(c.order_estimated_delivery_date))
         - julianday(date(c.order_purchase_timestamp)) AS INTEGER) AS delai_promis_jours,
    r.nb_articles,
    r.nb_vendeurs,
    r.nb_produits,
    r.prix_total,
    r.frais_port,
    r.poids_total_g,
    r.volume_total_cm3,
    ap.categorie,
    ap.seller_id               AS vendeur_id,
    v.seller_state             AS etat_vendeur,
    cl.customer_state          AS etat_client,
    gv.lat                     AS lat_vendeur,
    gv.lng                     AS lng_vendeur,
    gc.lat                     AS lat_client,
    gc.lng                     AS lng_client,
    COALESCE(rp.type_paiement, 'inconnu') AS type_paiement,
    COALESCE(rp.nb_mensualites, 1)        AS nb_mensualites,
    -- La cible : livré après la date promise (au jour près), ou jamais livré.
    CASE
        WHEN c.order_delivered_customer_date IS NULL THEN 1
        WHEN date(c.order_delivered_customer_date) > date(c.order_estimated_delivery_date) THEN 1
        ELSE 0
    END AS sinistre
FROM commandes_expediees AS c
JOIN resume_articles   AS r  ON r.order_id = c.order_id
JOIN article_principal AS ap ON ap.order_id = c.order_id
JOIN vendeurs          AS v  ON v.seller_id = ap.seller_id
JOIN clients           AS cl ON cl.customer_id = c.customer_id
LEFT JOIN resume_paiements AS rp ON rp.order_id = c.order_id
LEFT JOIN geo AS gv ON gv.code_postal = v.seller_zip_code_prefix
LEFT JOIN geo AS gc ON gc.code_postal = cl.customer_zip_code_prefix
ORDER BY c.order_purchase_timestamp;
