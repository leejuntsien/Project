# Use the official PostgreSQL image as the base
FROM postgres:15

# Install pg_cron
RUN apt-get update && apt-get install -y postgresql-15-cron && rm -rf /var/lib/apt/lists/*

# Ensure pg_cron is enabled by modifying postgresql.conf
RUN echo "shared_preload_libraries = 'pg_cron'" >> /usr/share/postgresql/postgresql.conf.sample

# Set the default timezone for pg_cron (optional, but recommended)
RUN echo "cron.database_name = 'Patient_data_FYP'" >> /usr/share/postgresql/postgresql.conf.sample