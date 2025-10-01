-- Schema definition for the Inter-Paws scheduling platform.

CREATE TABLE clinics (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address VARCHAR(255),
    phone_number VARCHAR(50),
    email VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    clinic_id INTEGER REFERENCES clinics (id),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'staff',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pets (
    id SERIAL PRIMARY KEY,
    clinic_id INTEGER REFERENCES clinics (id),
    owner_id INTEGER REFERENCES users (id),
    name VARCHAR(255) NOT NULL,
    species VARCHAR(100) NOT NULL,
    breed VARCHAR(100),
    sex VARCHAR(20),
    birth_date DATE,
    color VARCHAR(50),
    microchip_id VARCHAR(100) UNIQUE,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE doctors (
    id SERIAL PRIMARY KEY,
    clinic_id INTEGER NOT NULL REFERENCES clinics (id),
    user_id INTEGER REFERENCES users (id),
    display_name VARCHAR(255) NOT NULL,
    specialty VARCHAR(255),
    license_number VARCHAR(100) UNIQUE,
    biography TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rooms (
    id SERIAL PRIMARY KEY,
    clinic_id INTEGER NOT NULL REFERENCES clinics (id),
    name VARCHAR(100) NOT NULL,
    room_type VARCHAR(100),
    capacity INTEGER,
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE constraints (
    id SERIAL PRIMARY KEY,
    clinic_id INTEGER NOT NULL REFERENCES clinics (id),
    doctor_id INTEGER REFERENCES doctors (id),
    room_id INTEGER REFERENCES rooms (id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    recurrence VARCHAR(255),
    is_all_day BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE appointments (
    id SERIAL PRIMARY KEY,
    clinic_id INTEGER NOT NULL REFERENCES clinics (id),
    pet_id INTEGER REFERENCES pets (id),
    owner_id INTEGER REFERENCES users (id),
    doctor_id INTEGER REFERENCES doctors (id),
    room_id INTEGER REFERENCES rooms (id),
    constraint_id INTEGER REFERENCES constraints (id),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'scheduled',
    reason VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE feedback_events (
    id SERIAL PRIMARY KEY,
    appointment_id INTEGER NOT NULL REFERENCES appointments (id),
    user_id INTEGER REFERENCES users (id),
    rating INTEGER,
    sentiment VARCHAR(50),
    comments TEXT,
    suggestion_rank INTEGER,
    suggestion_score DOUBLE PRECISION,
    suggestion_slot_id INTEGER,
    suggestion_start_time TIMESTAMP,
    suggestion_end_time TIMESTAMP,
    suggestion_doctor_id INTEGER,
    suggestion_room_id INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    clinic_id INTEGER REFERENCES clinics (id),
    user_id INTEGER REFERENCES users (id),
    entity_type VARCHAR(100) NOT NULL,
    entity_id INTEGER,
    action VARCHAR(100) NOT NULL,
    description TEXT,
    changes JSONB,
    method VARCHAR(10) NOT NULL,
    path VARCHAR(255) NOT NULL,
    request_hash VARCHAR(128),
    response_hash VARCHAR(128),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
