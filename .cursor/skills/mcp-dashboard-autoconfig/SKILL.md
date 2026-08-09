---
name: mcp-dashboard-autoconfig
description: >-
  Crea y configura dashboards de forma automática vía MCP (Metabase primero:
  create_dashboard, update_dashboard, create_question, create_collection,
  search, read_resource), con notas para extender a otros MCP de BI. Use when
  creating or configuring dashboards, Metabase DB00 cards/params/tabs, MCP
  dashboard setup, or BI layout via MCP/API.
---

# MCP Dashboard Autoconfig

## When to use

- Crear o reconfigurar un dashboard Metabase vía MCP
- Montar colección + questions + dashboard + parámetros en un solo flujo
- Extender el mismo patrón a otro MCP de BI/analytics (ver sección final)

Complementa (no sustituye) `metabase-wardriving-bi` para el contenido canónico SQL/field-filters de DB00.

**Obligatorio:** al terminar (o si quedan pasos manuales), aplicar `mcp-api-user-docs` y dejar runbook en `docs/`.

## Prerequisites

1. `GetMcpTools` del server MCP antes de cualquier `CallMcpTool`.
2. Server Metabase: `user-metabase-mcp` (si `needsAuth` → `mcp_auth` una vez).
3. No inventar ids: descubrir con `search` / `read_resource` (`metabase://…`).
4. En este repo: orquestación con `podman-compose`; SQL canónico en `sql_bi_sources/`.

## Hard rules (Metabase)

1. **Nunca** use `construct_native_query` / `update_question` para reescribir cards nativas con Field Filters dimension — degradan tags a `type: text` y rompen filtros del dashboard.
2. Para SQL nativo con `{{tags}}` dimension: preferir REST cuidado / copiar SQL preservando template-tags, o UI; MCP solo para layout/colección cuando no toque tags.
3. MBQL nuevo: `construct_query` → `create_question` (o `create_metric` si aplica).
4. `update_dashboard` **no** crea virtual cards (`heading`/`text`); documentar paso manual o REST en el runbook `docs/`.
5. No commitear API keys / session tokens.

## Workflow automático (checklist)

```
Dashboard MCP:
- [ ] 0. Docs skill activa (mcp-api-user-docs)
- [ ] 1. Descubrir: search / read_resource (DB, collection, cards existentes)
- [ ] 2. Colección: create_collection si falta
- [ ] 3. Questions: crear o reutilizar ids
- [ ] 4. Dashboard: create_dashboard (+ question_ids)
- [ ] 5. Ajustar: update_dashboard (add/remove/move dashcards)
- [ ] 6. Parámetros / tabs / mappings (MCP si existe; si no → REST/UI + docs)
- [ ] 7. Verificar: read_resource dashboard + cards; smoke de filtros
- [ ] 8. Escribir docs/ runbook con pasos restantes para el usuario
```

### 1. Descubrir

- `search` por nombre de dashboard, colección, DB.
- `read_resource` en `metabase://dashboard/{id}` y `…/items` para `dashcard_id`.
- Anotar `collection_id`, `database_id`, card ids, `collection_path` de respuestas.

### 2. Colección

`create_collection` con `name`, `description`, `parent_collection_id` (null = root).

### 3. Questions

| Caso | Camino |
|------|--------|
| MBQL nuevo | `construct_query` → `create_question` (`query` = query_handle) |
| SQL ad-hoc sin field filters | `construct_native_query` → `create_question` |
| SQL canónico DB00 / dimension tags | **No** vía `construct_native_query`; seguir `metabase-wardriving-bi` |
| Ya existe | Reutilizar id (`search` / resource) |

Pasar `display`, `collection_id`, `visualization_settings` según schema del tool.

### 4. Crear dashboard

`create_dashboard`:

- `name`, `description`, `collection_id` (null = root; omitir deja personal — preferir id explícito)
- `question_ids`: lista de cards a añadir (auto-grid)
- Reportar URL / `collection_path` al usuario

### 5. Reconfigurar

`update_dashboard` (patch):

- `dashcards`: `[{"action":"add","card_id":N,"display_size":"wide"|"tall"|"full"}]`, `remove`/`move` con `dashcard_id`
- Obtener `dashcard_id` desde `metabase://dashboard/{id}/items`
- `archived: true` solo si el usuario lo pide

### 6. Parámetros, tabs, mappings

Si el tool MCP no expone tabs/parameter_mappings:

1. No fingir que quedó hecho.
2. Completar por REST Metabase o UI.
3. En el runbook `docs/`: comandos/pasos exactos, nombres de tags, y mappings esperados (`["dimension", ["template-tag", "<name>"]]` para DB00).

### 7. Verificar

- Dashboard y cards legibles vía `read_resource`
- Template-tags dimension intactos (si aplica)
- Filtros de smoke no fallan por “missing field filter”
- Entregar URL + path + ids creados

## Tool map (user-metabase-mcp)

| Objetivo | Tool |
|----------|------|
| Auth | `mcp_auth` |
| Hallar entidades | `search`, `read_resource` |
| Colección | `create_collection` |
| Query MBQL | `construct_query` |
| Query SQL nativo (sin dims) | `construct_native_query` |
| Guardar card | `create_question` |
| Dashboard nuevo | `create_dashboard` |
| Layout cards | `update_dashboard` |
| Probar datos | `execute_question` / `execute_query` / `visualize_query` |

Schemas: siempre `GetMcpTools` del server antes de llamar.

## Extender a otros MCP de BI

Mismo esqueleto; cambiar solo el adaptador:

1. Identificar server (`GetMcpTools` / pattern).
2. Mapear: create workspace → create tiles/widgets → attach to board → set filters.
3. Sustituir nombres de tools en el checklist; mantener descubrimiento por nombre, no ids inventados.
4. Documentar limitaciones del MCP en `docs/` (qué no puede hacer el tool y qué debe hacer el usuario).

## Anti-patterns

- Crear dashboard sin documentar en `docs/`
- Usar MCP para reescribir SQL de `sql_bi_sources` con field filters
- Inventar `database_id` / `card_id` / nombres de tabla
- Dar el trabajo por cerrado si faltan tabs, filtros o virtual cards sin runbook
