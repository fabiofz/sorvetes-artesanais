-- Segredo Gelado: esquema inicial para MySQL 8.4.
-- Execute em um banco vazio exclusivo do projeto.
-- Alternativa ao comando python -m app.cli init-db.


CREATE TABLE channels (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(40) NOT NULL, 
	prepaid BOOL NOT NULL, 
	active BOOL NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)

;


CREATE TABLE customers (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(100) NOT NULL, 
	contact VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE inventory (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(100) NOT NULL, 
	category VARCHAR(20) NOT NULL, 
	unit VARCHAR(10) NOT NULL, 
	balance NUMERIC(12, 3) NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (balance >= 0), 
	UNIQUE (name)
)

;


CREATE TABLE offers (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	balls INTEGER NOT NULL, 
	price NUMERIC(10, 2) NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (balls IN (1, 3, 6)), 
	CHECK (price > 0), 
	UNIQUE (balls)
)

;


CREATE TABLE users (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	username VARCHAR(80) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	`role` VARCHAR(20) NOT NULL, 
	active BOOL NOT NULL, 
	relief BOOL NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (username)
)

;


CREATE TABLE audit (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	actor_id INTEGER, 
	action VARCHAR(60) NOT NULL, 
	entity VARCHAR(40) NOT NULL, 
	entity_id INTEGER, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_id) REFERENCES users (id)
)

;


CREATE TABLE donations (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	actor_id INTEGER NOT NULL, 
	destination VARCHAR(200) NOT NULL, 
	donated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_id) REFERENCES users (id)
)

;


CREATE TABLE orders (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	customer_id INTEGER NOT NULL, 
	channel_id INTEGER NOT NULL, 
	external_id VARCHAR(100) NOT NULL, 
	payload_hash VARCHAR(64) NOT NULL, 
	address VARCHAR(300) NOT NULL, 
	total NUMERIC(10, 2) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (channel_id, external_id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id), 
	FOREIGN KEY(channel_id) REFERENCES channels (id)
)

;


CREATE TABLE shifts (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	driver_id INTEGER NOT NULL, 
	day DATE NOT NULL, 
	working BOOL NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (driver_id, day), 
	FOREIGN KEY(driver_id) REFERENCES users (id)
)

;


CREATE TABLE deliveries (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	order_id INTEGER NOT NULL, 
	driver_id INTEGER NOT NULL, 
	result VARCHAR(20), 
	departed_at DATETIME NOT NULL, 
	ended_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (order_id), 
	FOREIGN KEY(order_id) REFERENCES orders (id), 
	FOREIGN KEY(driver_id) REFERENCES users (id)
)

;


CREATE TABLE donation_items (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	order_id INTEGER NOT NULL, 
	donation_id INTEGER, 
	description TEXT NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	`condition` VARCHAR(200), 
	received_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (order_id), 
	FOREIGN KEY(order_id) REFERENCES orders (id), 
	FOREIGN KEY(donation_id) REFERENCES donations (id)
)

;


CREATE TABLE movements (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	inventory_id INTEGER NOT NULL, 
	order_id INTEGER, 
	actor_id INTEGER NOT NULL, 
	kind VARCHAR(20) NOT NULL, 
	quantity NUMERIC(12, 3) NOT NULL, 
	reason VARCHAR(200) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (order_id, inventory_id, kind), 
	FOREIGN KEY(inventory_id) REFERENCES inventory (id), 
	FOREIGN KEY(order_id) REFERENCES orders (id), 
	FOREIGN KEY(actor_id) REFERENCES users (id)
)

;


CREATE TABLE order_items (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	order_id INTEGER NOT NULL, 
	offer_id INTEGER NOT NULL, 
	balls INTEGER NOT NULL, 
	quantity INTEGER NOT NULL, 
	unit_price NUMERIC(10, 2) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(order_id) REFERENCES orders (id), 
	FOREIGN KEY(offer_id) REFERENCES offers (id)
)

;


CREATE TABLE payments (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	order_id INTEGER NOT NULL, 
	amount NUMERIC(10, 2) NOT NULL, 
	method VARCHAR(30) NOT NULL, 
	processor VARCHAR(40) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	reference VARCHAR(120), 
	PRIMARY KEY (id), 
	UNIQUE (order_id), 
	FOREIGN KEY(order_id) REFERENCES orders (id)
)

;


CREATE TABLE flavor_items (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	item_id INTEGER NOT NULL, 
	inventory_id INTEGER NOT NULL, 
	balls INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(item_id) REFERENCES order_items (id), 
	FOREIGN KEY(inventory_id) REFERENCES inventory (id)
)

;


CREATE TABLE incidents (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	delivery_id INTEGER NOT NULL, 
	kind VARCHAR(20) NOT NULL, 
	description VARCHAR(500) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(delivery_id) REFERENCES deliveries (id)
)

;


CREATE TABLE package_uses (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	item_id INTEGER NOT NULL, 
	inventory_id INTEGER NOT NULL, 
	quantity INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(item_id) REFERENCES order_items (id), 
	FOREIGN KEY(inventory_id) REFERENCES inventory (id)
)

;


CREATE TABLE refunds (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	payment_id INTEGER NOT NULL, 
	amount NUMERIC(10, 2) NOT NULL, 
	reference VARCHAR(120) NOT NULL, 
	confirmed_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (payment_id), 
	FOREIGN KEY(payment_id) REFERENCES payments (id), 
	UNIQUE (reference)
)

;

