CREATE DATABASE IF NOT EXISTS websites_monitor;
use websites_monitor;

DROP TABLE IF EXISTS users;
CREATE TABLE users(
    id INT AUTO_INCREMENT NOT NULL,
    name VARCHAR(50) NOT NULL,
    email VARCHAR(50) NOT NULL,
    password VARCHAR(200) NOT NULL,
    is_admin BOOLEAN NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET = utf8;

DROP TABLE IF EXISTS status;
CREATE TABLE status(
	id INT AUTO_INCREMENT NOT NULL,
    code INT NOT NULL,
    message VARCHAR(50) NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET = utf8;

DROP TABLE IF EXISTS websites;
CREATE TABLE websites(
    id INT AUTO_INCREMENT NOT NULL,
    url VARCHAR(50) NOT NULL,
    statut_id INT,
    PRIMARY KEY (id),
    FOREIGN KEY (statut_id) REFERENCES status(id)
) ENGINE=InnoDB DEFAULT CHARSET = utf8;

INSERT INTO users (name, email, password, is_admin) VALUES (
    'toto',
    'toto@email.com',
    '$argon2i$v=19$m=512,t=2,p=2$07qXMsb4P4fQ+p9T6l3rvQ$hWU817VMNDP/E9l21rYOKQ',
    true
);