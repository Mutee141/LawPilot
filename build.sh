#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Apply database migrations
python manage.py migrate

# Optionally load initial data from SQLite dump
if [ "$LOAD_INITIAL_DATA" = "true" ]; then
  echo "Loading initial data from datadump.json..."
  python manage.py loaddata datadump.json
fi

# Auto-register any PDFs already on disk into the database
echo "Syncing Supreme Court PDF files from disk into database..."
python manage.py sync_judgments_from_disk
