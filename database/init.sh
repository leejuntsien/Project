#!/bin/bash

# Check if the database is already initialized
if [ -f /var/lib/postgresql/data/initialized ]; then
  echo "Database is already initialized, skipping init.sql"
  exit 0
fi

# Run the init.sql file to initialize the database
psql -U postgres -d postgres -f /docker-entrypoint-initdb.d/init.sql

# Create a file to indicate that the database is initialized
touch /var/lib/postgresql/data/initialized