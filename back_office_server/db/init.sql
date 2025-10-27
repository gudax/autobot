-- Initial database setup for AutoBot Trading System
-- This script is run when PostgreSQL container is first created

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search optimizations

-- Create database if not exists (handled by POSTGRES_DB env var)
-- CREATE DATABASE autobot_trading;

-- Connect to database
\c autobot_trading;

-- Create roles (optional)
-- CREATE ROLE autobot_readonly;
-- CREATE ROLE autobot_readwrite;

-- Grant privileges
-- GRANT CONNECT ON DATABASE autobot_trading TO autobot_readonly;
-- GRANT CONNECT ON DATABASE autobot_trading TO autobot_readwrite;

-- Create schemas (if needed for multi-tenancy)
-- CREATE SCHEMA IF NOT EXISTS trading;
-- CREATE SCHEMA IF NOT EXISTS analytics;

-- Set timezone
SET timezone = 'UTC';

-- Performance tuning (optional)
ALTER DATABASE autobot_trading SET log_statement = 'all';
ALTER DATABASE autobot_trading SET log_duration = on;

-- Comments
COMMENT ON DATABASE autobot_trading IS 'AutoBot Multi-Account Trading System Database';

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully';
END $$;
