CREATE USER IF NOT EXISTS test_user IDENTIFIED BY 'test_password_please_ignore';
CREATE DATABASE IF NOT EXISTS freva;
GRANT ALL PRIVILEGES ON freva.* TO 'test_user'@'%' IDENTIFIED BY 'test_password_please_ignore';
FLUSH PRIVILEGES;
