# ── Stage 1: build ─────────────────────────────────────────────────────────────
FROM oven/bun:1-alpine AS builder

WORKDIR /app

# Instalar dependencias primero (mejor cache de capas)
COPY package.json bun.lock* ./
RUN bun install --frozen-lockfile

# Copiar fuentes y compilar
COPY . .
RUN bun run build

# ── Stage 2: serve ─────────────────────────────────────────────────────────────
FROM nginx:1.28-alpine AS runner

# Eliminar configuracion por defecto de nginx
RUN rm /etc/nginx/conf.d/default.conf

# Copiar configuracion SPA
COPY nginx.conf /etc/nginx/conf.d/wardrive-frontend.conf

# Copiar artefactos del build
COPY --from=builder /app/dist /usr/share/nginx/html/ctf

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
