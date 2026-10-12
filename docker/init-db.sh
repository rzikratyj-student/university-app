#!/bin/sh
# Runs only when the NEW Compose volume is initialized. Never enable shell tracing.
set -eu
export PGPASSWORD="$(cat /run/secrets/admin_password)"
CAMPUS_APP_PASSWORD="$(cat /run/secrets/app_password)"
export CAMPUS_APP_PASSWORD
# psql's environment import avoids placing credentials in process arguments.
psql -X --username "$POSTGRES_USER" --dbname postgres --set ON_ERROR_STOP=1 <<'SQL'
\set ECHO none
SET log_statement = 'none';
SET log_min_duration_statement = -1;
SET log_min_error_statement = 'panic';
\getenv app_password CAMPUS_APP_PASSWORD
CREATE ROLE campus_dev LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD :'app_password';
CREATE DATABASE campus_dev OWNER campus_dev;
SQL
unset PGPASSWORD CAMPUS_APP_PASSWORD
