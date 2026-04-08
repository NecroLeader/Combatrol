# CLAUDE.md — Combatrol Project Context

Leer este archivo antes de tocar cualquier archivo del proyecto.

---

## 1. INFRAESTRUCTURA OCI VM

**VM OCI (compartida con WorldZ):**
- IP: `64.181.171.46`
- Usuario: `ubuntu`
- Shape: VM.Standard.A1.Flex — 4 OCPU / 24GB RAM / 200GB
- OS: Ubuntu 22.04 ARM64
- SSH key: `C:\Users\necroleader\Downloads\programas\oci\ssh-key.key`

**Paths en la VM:**
- Base stack: `~/stack/`
- Logs: `~/stack/logs/`
- Proyecto Combatrol: `~/stack/projects/combatrol/`

---

## 2. COMANDOS DE CONEXIÓN Y DEPLOY

### Conectarse a la VM
```bash
ssh -i "C:\Users\necroleader\Downloads\programas\oci\ssh-key.key" ubuntu@64.181.171.46
```

### Variables de entorno para scripts
```powershell
$KEY = "C:\Users\necroleader\Downloads\programas\oci\ssh-key.key"
$VM  = "ubuntu@64.181.171.46"
$DST = "/home/ubuntu/stack/projects/combatrol"
```

### Subir archivos
```bash
scp -i "$KEY" -r ./app "$VM:$DST/"
scp -i "$KEY" ./requirements.txt "$VM:$DST/"
scp -i "$KEY" ./Dockerfile "$VM:$DST/"
scp -i "$KEY" ./docker-compose.yml "$VM:$DST/"
```

### Build y deploy en la VM
```bash
cd ~/stack/projects/combatrol
docker compose build
docker compose up -d
docker compose ps
docker compose logs -f
```

---

## 3. GIT

- GitHub user: `NecroLeader`
- Branch principal: `main`
- Remote: `https://github.com/NecroLeader/combatrol` (crear si no existe)

### Comandos git habituales
```bash
git init
git add .
git commit -m "mensaje"
git push origin main
```

---

## 4. CREDENCIALES Y ENV VARS

**Admin email:** `javier.m.gallego@gmail.com`
**Google OAuth Client ID:** `14873724881-4h54fdp91rnmf3ri86u411uhn7v0dves.apps.googleusercontent.com`

> Los tokens de la app (READ_TOKEN, ADMIN_TOKEN) se definen en `.env` local — **nunca subir `.env` a Git**.

Formato `.env.example`:
```
COMBATROL_READ_TOKEN=cambia_esto
COMBATROL_ADMIN_TOKEN=cambia_esto
COMBATROL_GOOGLE_CLIENT_ID=14873724881-4h54fdp91rnmf3ri86u411uhn7v0dves.apps.googleusercontent.com
COMBATROL_ADMIN_EMAIL=javier.m.gallego@gmail.com
```

---

## 5. DOCKER COMPOSE — ESTRUCTURA BASE

```yaml
# Adaptar según el stack del proyecto
services:
  combatrol:
    build: .
    container_name: combatrol_app
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./data:/app/data

  nginx:
    image: nginx:alpine
    container_name: combatrol_nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
```

---

## 6. ESTRUCTURA DE CARPETAS RECOMENDADA

```
combatrol/
  app/           — código de la aplicación
  data/          — base de datos y persistencia
  nginx/         — config nginx
  scripts/       — scripts auxiliares (cron, backup)
  Dockerfile
  docker-compose.yml
  .env           — NO subir a git
  .env.example   — sí subir a git
  .gitignore
  requirements.txt
  CLAUDE.md
```

---

## 7. COMANDOS ÚTILES DÍA A DÍA

```bash
# Estado
docker compose ps

# Logs en vivo
docker compose logs -f

# Reiniciar
docker compose restart

# Rebuild + relanzar
docker compose down && docker compose build && docker compose up -d

# Backup DB
docker compose exec combatrol cp /app/data/combatrol.sqlite /app/data/combatrol_backup_$(date +%Y%m%d).sqlite
```

---

## 8. REFERENCIA WORLDZ (proyecto hermano en la misma VM)

- Path en VM: `~/stack/projects/worldz/`
- Puerto interno: ver docker-compose.yml de WorldZ
- Repo: `https://github.com/NecroLeader/worldz`
