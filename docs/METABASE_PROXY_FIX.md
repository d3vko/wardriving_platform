# Plan: Metabase changes not applying in proxy

When you update the Metabase service in `docker-compose.yml`, the proxy (nginx) must stay in sync. Follow this checklist.

---

## 1. Align nginx with docker-compose

| In docker-compose | In nginx.conf | Action |
|-------------------|---------------|--------|
| Service name (e.g. `wardrive_bi`) | `upstream metabase_upstream { server SERVICE:PORT; }` and any `proxy_pass` using it | If you renamed the service, update the upstream `server` to the new name and port. |
| Metabase port (default 3000) | Same port in `server wardrive_bi:3000` | If you changed the internal port, update the upstream. |

**File:** `nginx.conf`  
- Block: `upstream metabase_upstream { server wardrive_bi:3000; ... }`  
- Ensure `wardrive_bi` and `3000` match the `services.wardrive_bi` (or whatever you named it) and the port Metabase listens on inside the container.

---

## 2. Decide where Metabase is served (root vs subpath)

**Current nginx behavior:**  
- `location /` (catch‑all) sends all non‑matched requests to Metabase.  
- So today Metabase is at **root** (`http://host:8000/`), not at `/bi`.

If you want Metabase on a **subpath** (e.g. `http://host:8000/bi/`):

1. **docker-compose.yml** — set Metabase base URL:
   ```yaml
   wardrive_bi:
     image: metabase/metabase:latest
     environment:
       MB_SITE_URL: http://YOUR_DOMAIN_OR_HOST:8000/bi
     # ... rest
   ```

2. **nginx.conf** — add a dedicated location and remove Metabase from `location /`:
   - Add:
     ```nginx
     location /bi/ {
       proxy_set_header Host              $host;
       proxy_set_header X-Real-IP         $remote_addr;
       proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
       proxy_set_header X-Forwarded-Prefix /bi;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection $connection_upgrade;
       proxy_read_timeout 300;
       proxy_send_timeout 300;
       proxy_pass http://metabase_upstream/;
     }
     ```
   - Change the current `location /` to something that does **not** proxy to Metabase (e.g. redirect to `/wardriving/` or serve a static page). Otherwise `/` will still go to Metabase.

If you are **happy with Metabase at root** (`/`), you only need step 1 (and 3 below); no nginx location change for the path.

---

## 3. Apply proxy changes (always do this after editing nginx)

After any change to `nginx.conf`:

```bash
# If using Docker
docker-compose exec wardrive_proxy nginx -t && docker-compose exec wardrive_proxy nginx -s reload

# If using Podman
podman-compose exec wardrive_proxy nginx -t && podman-compose exec wardrive_proxy nginx -s reload
```

Or recreate the proxy container so it mounts the updated config:

```bash
podman-compose up -d --force-recreate wardrive_proxy
```

---

## 4. Restart Metabase after docker-compose changes

If you changed env vars or image for Metabase, the proxy will only “see” the new behavior after Metabase is restarted:

```bash
podman-compose up -d wardrive_bi
# or
podman-compose restart wardrive_bi
```

---

## 5. Quick checklist

- [ ] `nginx.conf` → `metabase_upstream` uses the same service name and port as in `docker-compose.yml`.
- [ ] If Metabase is under a subpath (e.g. `/bi`): `MB_SITE_URL` set in compose and `location /bi/` added in nginx; `location /` no longer points to Metabase if you don’t want root to be Metabase.
- [ ] Proxy config tested: `nginx -t` inside the proxy container.
- [ ] Proxy reloaded or `wardrive_proxy` recreated.
- [ ] Metabase container restarted after compose changes.

After this, Metabase and the proxy stay in sync and your Metabase updates will apply correctly.
