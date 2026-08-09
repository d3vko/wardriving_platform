---
name: python-change-md-log
description: >-
  Document Python code changes in markdown files at the project root. Use when
  editing, adding, or deleting any .py file, Django apps, processors, migrations
  (Python), tests, management commands, or Python scripts in this repository.
---

# Documentar cambios Python en MD (raíz del proyecto)

Cuando hagas **cualquier cambio en Python** (crear, editar o borrar `.py`), **siempre** agrega un archivo Markdown en la **raíz del proyecto** que explique qué fue lo que hiciste.

## Obligatorio

- Tras cambios en archivos Python, crea (o actualiza si ya existe uno del mismo cambio en esta sesión) un `.md` en la raíz del repo (mismo nivel que `README.md`, `docker-compose.yml`, etc.).
- El MD debe describir **qué hiciste**, **por qué**, y **qué impacto** tiene (comportamiento, uploads, parsers, APIs, tests).
- No sustituyas esta nota por solo un mensaje de commit o por docs bajo `docs/` salvo que el usuario lo pida; la raíz es el destino requerido.
- Si el cambio Python es solo tipografía/formato sin comportamiento, el MD puede ser breve, pero igual es obligatorio.

## Nombre del archivo

Usa un nombre descriptivo y datado cuando sea posible:

- `CHANGE_YYYYMMDD_<slug-corto>.md` (recomendado), p. ej. `CHANGE_wifi_csv_parser.md`
- o `<tema>_cambio.md` si el usuario ya indicó un nombre

No uses nombres genéricos tipo `notes.md` / `temp.md`.

## Contenido mínimo del MD

```markdown
# <Título corto del cambio>

## Qué se hizo
- …

## Por qué
- …

## Archivos tocados
- `path/to/file.py` — …

## Cómo verificar
- …
```

## Flujo

1. Haz el cambio Python.
2. Escribe el MD en la raíz **antes** de dar por terminada la tarea.
3. Menciona en la respuesta al usuario la ruta del MD creado.
