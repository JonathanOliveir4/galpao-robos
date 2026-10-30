-- O schema galpao é criado pelo MYSQL_DATABASE no docker-compose.
-- O segundo schema é exclusivo para a análise de dados públicos.
CREATE DATABASE IF NOT EXISTS analise_logistica
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON analise_logistica.* TO 'galpao'@'%';
FLUSH PRIVILEGES;
