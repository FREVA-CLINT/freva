USE mysql;
CREATE USER IF NOT EXISTS 'freva'@'localhost' IDENTIFIED BY 'T3st';
ALTER USER 'freva'@'localhost' IDENTIFIED BY 'T3st';
CREATE DATABASE IF NOT EXISTS freva;
GRANT ALL ON freva.* TO 'freva'@'localhost';
FLUSH PRIVILEGES;
