# ── Stage 1: build ─────────────────────────────────────────────────────────────
FROM oven/bun:1-alpine AS builder

WORKDIR /app

# Build-time env received from compose root `.env`
ARG VITE_ANALYTICS_DEFAULT_START_DATE
ARG VITE_ANALYTICS_DEFAULT_END_DATE
ARG VITE_ANALYTICS_API_URL
ARG VITE_APP_TITLE
ARG VITE_APP_FAVICON_URL
ARG VITE_EVENT_HOME_TITLE
ARG VITE_EVENT_HOME_BADGE
ARG VITE_EVENT_INTRO_TEXT
ARG VITE_EVENT_DYNAMICS_TITLE
ARG VITE_EVENT_DYNAMICS_TEXT
ARG VITE_EVENT_LOGO_SECTION_TITLE
ARG VITE_EVENT_LOGO_SECTION_TEXT
ARG VITE_EVENT_LOGO_URL
ARG VITE_EVENT_LOGO_ALT
ARG VITE_EVENT_LOGO_LINK_URL
ARG VITE_EVENT_LOGO_LINK_LABEL

ENV VITE_ANALYTICS_DEFAULT_START_DATE=$VITE_ANALYTICS_DEFAULT_START_DATE \
    VITE_ANALYTICS_DEFAULT_END_DATE=$VITE_ANALYTICS_DEFAULT_END_DATE \
    VITE_ANALYTICS_API_URL=$VITE_ANALYTICS_API_URL \
    VITE_APP_TITLE=$VITE_APP_TITLE \
    VITE_APP_FAVICON_URL=$VITE_APP_FAVICON_URL \
    VITE_EVENT_HOME_TITLE=$VITE_EVENT_HOME_TITLE \
    VITE_EVENT_HOME_BADGE=$VITE_EVENT_HOME_BADGE \
    VITE_EVENT_INTRO_TEXT=$VITE_EVENT_INTRO_TEXT \
    VITE_EVENT_DYNAMICS_TITLE=$VITE_EVENT_DYNAMICS_TITLE \
    VITE_EVENT_DYNAMICS_TEXT=$VITE_EVENT_DYNAMICS_TEXT \
    VITE_EVENT_LOGO_SECTION_TITLE=$VITE_EVENT_LOGO_SECTION_TITLE \
    VITE_EVENT_LOGO_SECTION_TEXT=$VITE_EVENT_LOGO_SECTION_TEXT \
    VITE_EVENT_LOGO_URL=$VITE_EVENT_LOGO_URL \
    VITE_EVENT_LOGO_ALT=$VITE_EVENT_LOGO_ALT \
    VITE_EVENT_LOGO_LINK_URL=$VITE_EVENT_LOGO_LINK_URL \
    VITE_EVENT_LOGO_LINK_LABEL=$VITE_EVENT_LOGO_LINK_LABEL

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
