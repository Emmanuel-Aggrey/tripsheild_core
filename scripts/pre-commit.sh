#!/usr/bin/env bash
# call this in yer /.git/hooks/pre-commit

echo "Doing pre-commit check..."

echo "Checking code smells..."
source ./scripts/check_code_smells.sh

echo "Checking code style..."
source ./scripts/check_style.sh

echo "Checking for conflicting migrations..."
source scripts/check_alembic_migrations.sh

echo "Passed pre-commit check"
