-- Create the user with login privileges and password
CREATE USER k3s_admin WITH LOGIN PASSWORD '62#_Vt3^DRSatEO|R.FmW';

alter user k3s_admin with Login password 'Thisisatestformetotryout';
-- Create the database if it doesn't exist
CREATE DATABASE k3s;

-- Grant all privileges on the database
GRANT ALL PRIVILEGES ON DATABASE k3s TO k3s_admin;
GRANT ALL PRIVILEGES ON DATABASE kubernetes TO postgres;
-- Connect to the k3s database to grant schema-level permissions

ALTER DATABASE kubernetes OWNER to postgres
-- Grant all privileges on all tables in the public schema
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO k3s_admin;

-- Grant all privileges on all sequences in the public schema
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO k3s_admin;

-- Grant all privileges on the schema
GRANT ALL PRIVILEGES ON SCHEMA public TO k3s_admin;

-- Make sure future tables and sequences are accessible
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO k3s_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO k3s_admin;

-- Grant the ability to create databases
ALTER USER k3s_admin CREATEDB;

-- Optional: Make the user a superuser (careful with this in production)
-- ALTER USER k3s_admin WITH SUPERUSER;
