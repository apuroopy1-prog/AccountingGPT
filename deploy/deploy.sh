#!/bin/bash
# Deploy ClearFlow AI — run from repo root on EC2

set -e

echo "=== Pulling latest code ==="
git pull origin main

echo "=== Building and starting containers ==="
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

echo "=== Removing unused images ==="
docker image prune -f

echo "=== Status ==="
docker-compose ps

echo ""
echo "ClearFlow AI deployed successfully."
