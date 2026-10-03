# Podemos Peru API

API para el registro, validacion y analisis en tiempo real de resultados de
elecciones regionales y municipales del Peru.

## Stack

- FastAPI + SQLAlchemy 2.0 + Alembic
- PostgreSQL 16
- JWT (python-jose) + bcrypt
- WebSockets para resultados en tiempo real

## Requisitos

- Docker Desktop (recomendado) o Python 3.12 + uv

## Levantar con Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

La API queda en `http://localhost:8000` y aplica migraciones + seed
automaticamente al arrancar.

- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Desarrollo local (sin Docker)

```bash
uv sync
copy .env.example .env
docker compose up -d db        # solo la base de datos
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

## Usuarios iniciales (seed)

La base de datos arranca **limpia**: el seed solo crea el administrador.
No hay procesos, geografia, partidos, mesas ni personeros precargados.

| Rol           | Credencial     |
| ------------- | -------------- |
| Administrador | admin/admin123 |

Se recomienda cambiar `ADMIN_PASSWORD` en produccion.

## Consulta de DNI (apisperu)

El backend expone `GET /api/v1/admin/dni/{dni}` (solo admin) que consulta
apisperu y devuelve el nombre completo en mayusculas. El **token nunca se
expone al frontend**; se configura via `.env`:

```
APISPERU_TOKEN=tu_token
APISPERU_BASE_URL=https://dniruc.apisperu.com/api/v1
```

## Flujo principal

1. El administrador carga procesos, geografia (provincia/distrito), centros,
   mesas, partidos, candidatos y asigna partidos por mesa y categoria.
2. El personero inicia sesion con su DNI y solo puede registrar mesas dentro de
   su scope (su mesa, o cualquier mesa de su local).
3. Al registrar votos se valida que, por cada una de las 4 categorias
   (GOBERNADOR, CONSEJERO, PROVINCIA, DISTRITO), la suma de validos + nulos +
   blancos sea igual al total de asistentes. Si no cuadra, la API responde 422.
4. Las ediciones quedan registradas en el historial con el usuario que modifico.
5. Los dashboards se actualizan en tiempo real por WebSocket en `/api/v1/ws/results`.

## Tests

```bash
uv run pytest
```

## Despliegue en VPS

1. Clona el repo y copia el entorno:

   ```bash
   cp .env.example .env
   ```

2. Edita `.env` con valores de produccion:

   ```
   SECRET_KEY=<clave-larga-y-aleatoria>
   ADMIN_PASSWORD=<contrasena-fuerte>
   CORS_ORIGINS=https://tudominio.com
   APISPERU_TOKEN=<tu_token>
   API_PORT=8477
   ```

3. Levanta el stack:

   ```bash
   docker compose up -d --build
   ```

   La API queda escuchando **solo** en `127.0.0.1:8477` (no se expone a
   internet) y PostgreSQL no publica puerto al host. El `entrypoint.sh` espera
   la base de datos y aplica las migraciones.

4. Nginx como proxy inverso (TLS con certbot):

   ```nginx
   server {
       listen 443 ssl;
       server_name tudominio.com;

       location /api/ {
           proxy_pass http://127.0.0.1:8477;
           proxy_set_header Host $host;
           proxy_set_header X-Forwarded-Proto $scheme;
       }

       location /api/v1/ws/results {
           proxy_pass http://127.0.0.1:8477;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_read_timeout 3600s;
       }
   }
   ```

5. Firewall: abre solo `80`, `443` y `22`. Nunca expongas `8477` ni `5432`.

Si cambias `API_PORT`, actualiza tambien el `proxy_pass` de Nginx.

