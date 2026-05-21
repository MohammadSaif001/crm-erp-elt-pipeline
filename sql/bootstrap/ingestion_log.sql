CREATE TABLE  IF NOT EXISTS bronze_db.ingestion_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_name VARCHAR(100),
    file_name VARCHAR(255),
    file_hash VARCHAR(64),
    row_count INT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

show tables;