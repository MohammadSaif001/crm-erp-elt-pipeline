DROP VIEW IF EXISTS gold_db.dim_customers;

CREATE VIEW gold_db.dim_customers AS
SELECT
    ROW_NUMBER() OVER (ORDER BY ci.cst_id) AS customer_key,

    ci.cst_id           AS customer_id,
    ci.cst_key          AS customer_number,
    ci.cst_firstname    AS first_name,
    ci.cst_lastname     AS last_name,

    la.country_name     AS country,
    ci.cst_marital_status AS marital_status,

    CASE 
        -- CRM is the master for gender information
        WHEN ci.cst_gender != 'n/a' THEN ci.cst_gender
        ELSE COALESCE(ca.gender_raw, 'n/a')
    END AS gender,

    ca.birth_date_raw   AS birthday,
    ci.cst_create_date  AS create_date

FROM silver_db.crm_customers_info AS ci
LEFT JOIN silver_db.erp_cust_az12 AS ca
       ON ci.cst_key = ca.cid
LEFT JOIN silver_db.erp_location_a101 AS la
       ON ci.cst_key = la.cid;


DROP VIEW IF EXISTS gold_db.dim_products;

CREATE VIEW gold_db.dim_products AS
SELECT 
    ROW_NUMBER() OVER( ORDER BY pn.prd_start_dt,
    pn.prd_key) AS product_key,
    pn.prd_id AS product_id,
    pn.prd_key AS product_number,
    pn.prd_name AS product_name,
    pn.cat_id AS category_id,
    pc.cat AS category_name, 
    pc.subcat AS subcategory_name,   
    pn.prd_cost AS product_cost,
    pn.prd_line AS product_line,
    
    pc.maintenance_raw AS maintenance,
    pn.prd_start_dt AS product_start_date
FROM silver_db.crm_prd_info pn
LEFT JOIN silver_db.erp_px_cat_g1v2 pc
ON pn.cat_id = pc.id
WHERE pn.prd_end_dt IS NULL ;

DROP VIEW IF EXISTS gold_db.fact_sales;

CREATE VIEW gold_db.fact_sales AS
SELECT 
    sd.sales_ord_num AS order_number,
    pr.product_key ,
    cu.customer_key ,
    sd.sales_order_date AS order_date,
    sd.sales_ship_date AS shipping_date,
    sd.sales_due_date AS due_date, 
    sd.sales_sales AS sales_amount,   
    sd.sales_quantity AS quantity ,
    sd.sales_price AS price 
FROM silver_db.crm_sales_details sd
LEFT JOIN gold_db.dim_products pr
ON sd.sales_prd_key = pr.product_number
LEFT JOIN gold_db.dim_customers cu
ON sd.sales_cust_id = cu.customer_id
;