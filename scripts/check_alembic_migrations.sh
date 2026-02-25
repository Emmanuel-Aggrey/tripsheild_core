#!/usr/bin/env bash

# Check for new migrations
NEW_MIGRATIONS=$(alembic current | grep -v "Head")

if [ -n "$NEW_MIGRATIONS" ]; then
    echo "Found new migrations:"
    echo "$NEW_MIGRATIONS"
    exit 1
fi
echo "No new migrations detected."

# Check for migration clashes (optional, based on your setup)
MIGRATION_CLASHES=$(alembic heads | grep -o "->" | wc -l)

if [ "$MIGRATION_CLASHES" -gt 1 ]; then
    echo "Migration clashes detected!"
    exit 1
fi

echo "No migration clashes."
