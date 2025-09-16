-- SQL script to initialize hr_onboarding database

CREATE DATABASE hr_onboarding;

-- Now connect manually in pgAdmin to hr_onboarding,
-- then run this second part:

CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
