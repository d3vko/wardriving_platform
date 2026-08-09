---
name: mcp-api-user-docs
description: >-
  Obliga a documentar en docs/ toda operación hecha vía MCP o API, con los
  pasos/tareas que el usuario debe completar. Use when calling MCP tools,
  Metabase/API REST, external APIs, automation that mutates remote systems, or
  when finishing create_dashboard / update_dashboard / MCP setups.
---

# MCP/API → documentación obligatoria en docs/

## Regla dura

**Toda operación realizada mediante MCP o API necesita forzosamente crear una documentación que se deposite en `docs/` de las tareas o pasos que realiza para completar por parte del usuario.**

Sin doc en `docs/`, la operación **no se considera cerrada**.

## When to use

- Antes/durante/después de cualquier `CallMcpTool` o llamada HTTP/API que cree, actualice, archive o configure algo remoto
- Dashboards, questions, collections, syncs, pipelines, webhooks, BI, etc.
- Aunque el MCP haya “terminado” con éxito: igual documentar resultado + pasos humanos restantes

## Qué documentar (mínimo)

1. **Contexto:** qué se pidió y por qué.
2. **Hecho por el agente:** tools MCP / endpoints, ids creados, URLs, nombres de recursos.
3. **Tareas del usuario:** checklist accionable de lo que **falta** o debe verificar (UI, secrets, sync, permisos, params no soportados por MCP).
4. **Verificación:** cómo comprobar que quedó bien.
5. **Riesgos / no hechos:** límites del MCP/API, datos sensibles omitidos, rollbacks.

No pegar secrets, tokens ni API keys. Sí: paths, nombres públicos, ids no secretos, comandos sin credenciales.

## Dónde y cómo nombrar

| Caso | Ruta sugerida |
|------|----------------|
| Metabase / BI | `docs/metabase/<slug>.md` |
| Ops / infra API | `docs/ops/<slug>.md` |
| Otro dominio | `docs/<area>/<slug>.md` |
| One-shot corto | `docs/<AREA>_<SLUG>.md` si ya hay ese estilo en el repo |

- `slug`: kebab-case, descriptivo (`db00-dashboard-mcp-setup`, `create-lte-collection`).
- Si `docs/<area>/` no existe, créalo.
- Un runbook por operación lógica (un dashboard, un sync, un lote); no mezclar temas no relacionados.
- Actualizar el mismo fichero si se re-ejecuta la misma operación (añadir sección “Actualización YYYY-MM-DD”).

## Plantilla obligatoria

Crear o actualizar el markdown con esta estructura:

```markdown
# <Título de la operación>

- **Fecha:** YYYY-MM-DD
- **Canal:** MCP (`<server>`) | API (`<servicio>`)
- **Estado:** hecho | parcial | bloqueado
- **Recursos:** ids, URLs, collection_path (sin secretos)

## Objetivo

<1–3 frases>

## Realizado vía MCP/API

1. …
2. …

## Tareas / pasos para el usuario

- [ ] …
- [ ] …

## Verificación

- [ ] …
- [ ] …

## Notas / limitaciones

- …
```

La sección **Tareas / pasos para el usuario** es obligatoria aunque esté vacía: en ese caso escribir `- [x] Ningún paso manual restante` y justificar en una línea.

## Orden de trabajo

```
1. Planear la mutación MCP/API
2. Ejecutar tools / API
3. Inmediatamente escribir o actualizar docs/…
4. En el chat: enlazar la ruta del runbook + resumir solo lo crítico
5. No marcar la tarea como completa sin el fichero en docs/
```

Si la operación falla a mitad: igual documentar en `docs/` lo intentado, el error y los pasos de recuperación para el usuario.

## Relación con otras skills

- `mcp-dashboard-autoconfig`: tras crear/configurar dashboard, el runbook es obligatorio.
- `metabase-wardriving-bi`: si hay pasos manuales de field filters / virtual cards, van en `docs/` con este formato.

## Anti-patterns

- Solo explicar pasos en el chat sin fichero en `docs/`
- Docs sin checklist de usuario
- Commitear `.env`, tokens o respuestas de API con credenciales
- Nombrar el fichero de forma opaca (`tmp.md`, `notes.md`)
