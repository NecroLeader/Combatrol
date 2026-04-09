#!/bin/bash
# Obtiene el certificado Let's Encrypt por primera vez.
# Correr UNA vez desde ~/stack/projects/combatrol/ antes del primer docker compose up.
#
# Requisitos:
#   - combatrol.duckdns.org apunta a esta IP en DuckDNS
#   - Puerto 80 abierto en el firewall de OCI
#   - .env con COMBATROL_ADMIN_EMAIL seteado

set -e

DOMAIN="combatrol.duckdns.org"
EMAIL=$(grep COMBATROL_ADMIN_EMAIL .env | cut -d= -f2)

if [ -z "$EMAIL" ]; then
  echo "[ERROR] COMBATROL_ADMIN_EMAIL no está en .env"
  exit 1
fi

echo "[init_ssl] Dominio: $DOMAIN"
echo "[init_ssl] Email:   $EMAIL"

# Crear volúmenes si no existen
docker volume create combatrol_certbot_certs 2>/dev/null || true
docker volume create combatrol_certbot_www   2>/dev/null || true

# Levantar nginx solo en HTTP (necesita estar up para el challenge)
docker compose up -d nginx

echo "[init_ssl] Esperando que nginx levante..."
sleep 3

# Obtener certificado vía webroot
docker run --rm \
  -v combatrol_certbot_certs:/etc/letsencrypt \
  -v combatrol_certbot_www:/var/www/certbot \
  certbot/certbot certonly \
    --webroot -w /var/www/certbot \
    -d "$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos \
    --non-interactive

echo "[init_ssl] Certificado obtenido. Levantando stack completo..."
docker compose up -d

echo "[init_ssl] Listo. https://$DOMAIN"
