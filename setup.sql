-- ==========================================================
-- CLEAN RESET DATABASE
-- ==========================================================

DROP DATABASE IF EXISTS metro_ticketing;
CREATE DATABASE metro_ticketing;
USE metro_ticketing;

-- ==========================================================
-- TABLE: roles
-- ==========================================================
CREATE TABLE roles (
    role_id INT AUTO_INCREMENT PRIMARY KEY,
    role_name ENUM('admin','user') NOT NULL
);

INSERT INTO roles (role_name) VALUES ('admin'), ('user');

-- ==========================================================
-- TABLE: users
-- ==========================================================
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(80) UNIQUE,
    password_hash VARCHAR(200),
    role_id INT DEFAULT 2,  -- 1 = admin, 2 = user
    signup_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(role_id)
);

-- Default admin user
INSERT INTO users (name, email, password_hash, role_id)
VALUES ('Admin', 'admin@metro.com', '$2b$12$abcdefghijkFakeHashForAdmin', 1);

-- ==========================================================
-- TABLE: metro_lines
-- ==========================================================
CREATE TABLE metro_lines (
    line_id INT AUTO_INCREMENT PRIMARY KEY,
    line_name VARCHAR(80) NOT NULL UNIQUE
);

-- 3 Simple Lines
INSERT INTO metro_lines (line_name) VALUES
('PCMC - Swargate'),
('Vanaz - Ramwadi'),
('Hinjawadi - Shivajinagar');

-- ==========================================================
-- TABLE: stops
-- ==========================================================
CREATE TABLE stops (
    stop_id INT AUTO_INCREMENT PRIMARY KEY,
    line_id INT NOT NULL,
    stop_name VARCHAR(80) NOT NULL,
    stop_order INT NOT NULL,
    FOREIGN KEY (line_id) REFERENCES metro_lines(line_id)
);

-- -----------------------------
-- LINE 1: PCMC - Swargate
-- -----------------------------
INSERT INTO stops (line_id, stop_name, stop_order) VALUES
(1, 'PCMC', 1),
(1, 'Kasarwadi', 2),
(1, 'Khadki', 3),
(1, 'Shivajinagar', 4),
(1, 'Swargate', 5);

-- -----------------------------
-- LINE 2: Vanaz - Ramwadi
-- -----------------------------
INSERT INTO stops (line_id, stop_name, stop_order) VALUES
(2, 'Vanaz', 1),
(2, 'Nal Stop', 2),
(2, 'Deccan', 3),
(2, 'PMC', 4),
(2, 'Ramwadi', 5);

-- -----------------------------
-- LINE 3: Hinjawadi - Shivajinagar
-- -----------------------------
INSERT INTO stops (line_id, stop_name, stop_order) VALUES
(3, 'Hinjawadi Phase 3', 1),
(3, 'Hinjawadi Phase 1', 2),
(3, 'Wakad', 3),
(3, 'Baner', 4),
(3, 'Shivajinagar', 5);

-- ==========================================================
-- TABLE: passes
-- ==========================================================
CREATE TABLE passes (
    pass_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    line_id INT NOT NULL,
    balance DECIMAL(8,2) DEFAULT 0,
    start_date DATE,
    end_date DATE,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (line_id) REFERENCES metro_lines(line_id)
);

-- ==========================================================
-- TABLE: tickets
-- ==========================================================
CREATE TABLE tickets (
    ticket_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    line_id INT NOT NULL,
    from_stop INT NOT NULL,
    to_stop INT NOT NULL,
    travel_date DATETIME NOT NULL,
    fare DECIMAL(6,2),
    use_pass ENUM('Y','N') DEFAULT 'N',
    is_used TINYINT DEFAULT 0,
    used_at DATETIME NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (line_id) REFERENCES metro_lines(line_id),
    FOREIGN KEY (from_stop) REFERENCES stops(stop_id),
    FOREIGN KEY (to_stop) REFERENCES stops(stop_id)
);

-- ==========================================================
-- TABLE: train_schedule
-- ==========================================================
CREATE TABLE train_schedule (
    schedule_id INT AUTO_INCREMENT PRIMARY KEY,
    line_id INT NOT NULL,
    stop_id INT NOT NULL,
    arrival_time TIME NOT NULL,
    departure_time TIME NOT NULL,
    direction ENUM('UP','DOWN') NOT NULL,
    FOREIGN KEY (line_id) REFERENCES metro_lines(line_id),
    FOREIGN KEY (stop_id) REFERENCES stops(stop_id)
);

-- ==========================================================
-- DB READY FOR PYTHON SCHEDULE GENERATOR
-- ==========================================================

