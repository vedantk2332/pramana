#!/bin/bash
echo "==> Building Pramana Django project for Vercel..."

# Install dependencies from requirements.txt
python3 -m pip install -r requirements.txt

# Collect static files into staticfiles/ for Vercel CDN serving
python3 manage.py collectstatic --noinput --clear

echo "==> Pramana static build completed successfully."
