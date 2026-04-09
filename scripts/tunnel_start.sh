#!/bin/bash
# scripts/tunnel_start.sh
# Uso: ./scripts/tunnel_start.sh
# Sobe os containers e inicia o tunnel em sequência.
# Ctrl+C encerra o tunnel (containers continuam rodando).

set -e

echo "Subindo containers..."
docker compose up -d

echo "Aguardando API ficar pronta..."
until curl -sf http://localhost:8000/health > /dev/null 2>&1; do
  printf "."
  sleep 2
done
echo " OK"

echo "Iniciando Cloudflare Tunnel..."
echo "API disponível em: $(grep API_PUBLIC_URL .env | cut -d= -f2)"
echo "GeoServer em:      $(grep GEO_PUBLIC_URL .env | cut -d= -f2)/geoserver"

cloudflared tunnel --config cloudflared/config.yml run somap
