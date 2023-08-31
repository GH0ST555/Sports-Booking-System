#!/bin/sh

# Initialize the database
flask db init

# Migrate the database
flask db migrate -m "Initial migration."

# Upgrade the database
flask db upgrade

# Populate the database with sample data
python sample_sessions.py
python add_roles.py
# Start the Flask app
flask run --host=0.0.0.0 --port=5000
