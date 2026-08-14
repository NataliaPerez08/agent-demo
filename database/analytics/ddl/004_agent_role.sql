DO $$
BEGIN

    IF NOT EXISTS (
        SELECT
        FROM pg_roles
        WHERE rolname = 'analyst_agent'
    ) THEN

        CREATE ROLE analyst_agent
            LOGIN
            PASSWORD 'analyst';

    END IF;

END
$$;


GRANT CONNECT
ON DATABASE analytics
TO analyst_agent;


GRANT USAGE
ON SCHEMA public
TO analyst_agent;


GRANT SELECT
ON ALL TABLES
IN SCHEMA public
TO analyst_agent;


ALTER DEFAULT PRIVILEGES
IN SCHEMA public
GRANT SELECT
ON TABLES
TO analyst_agent;