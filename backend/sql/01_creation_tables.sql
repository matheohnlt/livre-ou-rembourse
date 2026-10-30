-- Création des 9 tables Olist dans SQLite (une table par fichier CSV de l'archive Kaggle).
-- Les noms de colonnes sont ceux des fichiers d'origine. Les dates restent au format texte
-- ISO « AAAA-MM-JJ HH:MM:SS », que les fonctions date() et julianday() de SQLite lisent.
-- Les clés primaires vérifient l'unicité au chargement : un doublon fait échouer l'import.

DROP TABLE IF EXISTS commandes;
DROP TABLE IF EXISTS articles;
DROP TABLE IF EXISTS produits;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS vendeurs;
DROP TABLE IF EXISTS clients;
DROP TABLE IF EXISTS geolocalisation;
DROP TABLE IF EXISTS paiements;
DROP TABLE IF EXISTS avis;

-- Une ligne = une commande.
CREATE TABLE commandes (
    order_id                      TEXT PRIMARY KEY,
    customer_id                   TEXT NOT NULL,
    order_status                  TEXT NOT NULL,
    order_purchase_timestamp      TEXT NOT NULL,
    order_approved_at             TEXT,
    order_delivered_carrier_date  TEXT,
    order_delivered_customer_date TEXT,
    order_estimated_delivery_date TEXT NOT NULL
);

-- Une ligne = un article d'une commande.
CREATE TABLE articles (
    order_id            TEXT NOT NULL,
    order_item_id       INTEGER NOT NULL,
    product_id          TEXT NOT NULL,
    seller_id           TEXT NOT NULL,
    shipping_limit_date TEXT,
    price               REAL,
    freight_value       REAL,
    PRIMARY KEY (order_id, order_item_id)
);

-- Une ligne = un produit.
CREATE TABLE produits (
    product_id                 TEXT PRIMARY KEY,
    product_category_name      TEXT,
    product_name_lenght        INTEGER,
    product_description_lenght INTEGER,
    product_photos_qty         INTEGER,
    product_weight_g           REAL,
    product_length_cm          REAL,
    product_height_cm          REAL,
    product_width_cm           REAL
);

-- Une ligne = une catégorie (traduction portugais -> anglais).
CREATE TABLE categories (
    product_category_name         TEXT PRIMARY KEY,
    product_category_name_english TEXT
);

-- Une ligne = un vendeur.
CREATE TABLE vendeurs (
    seller_id              TEXT PRIMARY KEY,
    seller_zip_code_prefix TEXT,
    seller_city            TEXT,
    seller_state           TEXT
);

-- Une ligne = un client PAR COMMANDE (customer_unique_id identifie la personne).
CREATE TABLE clients (
    customer_id              TEXT PRIMARY KEY,
    customer_unique_id       TEXT NOT NULL,
    customer_zip_code_prefix TEXT,
    customer_city            TEXT,
    customer_state           TEXT
);

-- Une ligne = un point GPS : plusieurs points par code postal (pas de clé unique).
CREATE TABLE geolocalisation (
    geolocation_zip_code_prefix TEXT,
    geolocation_lat             REAL,
    geolocation_lng             REAL,
    geolocation_city            TEXT,
    geolocation_state           TEXT
);

-- Une ligne = un paiement d'une commande (une commande peut être payée en plusieurs fois).
CREATE TABLE paiements (
    order_id             TEXT NOT NULL,
    payment_sequential   INTEGER NOT NULL,
    payment_type         TEXT,
    payment_installments INTEGER,
    payment_value        REAL,
    PRIMARY KEY (order_id, payment_sequential)
);

-- Une ligne = un avis. Attention : review_id et order_id ne sont pas uniques.
CREATE TABLE avis (
    review_id               TEXT NOT NULL,
    order_id                TEXT NOT NULL,
    review_score            INTEGER,
    review_comment_title    TEXT,
    review_comment_message  TEXT,
    review_creation_date    TEXT,
    review_answer_timestamp TEXT
);

-- Index sur les clés de jointure, pour que la table d'analyse se construise vite.
CREATE INDEX idx_articles_commande ON articles (order_id);
CREATE INDEX idx_paiements_commande ON paiements (order_id);
CREATE INDEX idx_avis_commande ON avis (order_id);
CREATE INDEX idx_geo_code_postal ON geolocalisation (geolocation_zip_code_prefix);
