FROM node:20-slim AS base

RUN apt-get update && apt-get install -y curl perl
RUN npm install -g @latitude-data/cli@1.10.6

FROM base AS builder

ENV NODE_OPTIONS=--experimental-global-webcrypto

WORKDIR /usr/src/app

COPY package.json .
COPY latitude.json .

RUN latitude telemetry --disable
RUN latitude setup

FROM builder AS runner

WORKDIR /usr/src/app

COPY --from=builder /usr/src/app/node_modules ./node_modules
COPY --from=builder /usr/src/app/.latitude ./
COPY --from=builder /usr/src/app/latitude.json ./latitude.json
COPY . .

RUN latitude build && \
    find .latitude -name '_server.ts-*.js' -exec sed -i 's/compiledQuery/sql/g' {} + && \
    find .latitude -name '_server.ts-*.js' -exec perl -i -0777 -pe \
      's/(connector\.runCompiled\(\{\s*\n\s*sql: sql,\s*\n\s*)params: resolvedParams/$1resolvedParams/' {} +

WORKDIR /usr/src/app/build

EXPOSE 3000

CMD ["node", "build"]
