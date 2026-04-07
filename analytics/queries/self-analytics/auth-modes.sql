{@config ttl = 600}

-- Rango de fechas sobre wardriving_vendor.first_seen (timestamptz en PostgreSQL)
-- Formato ISO 8601 con offset de zona horaria, p.ej. 2025-01-01T00:00:00-06:00
{ first_seen_start = param('first_seen_start', '2025-01-01T00:00:00-06:00') }
{ first_seen_end   = param('first_seen_end',   '2026-05-30T00:00:00-06:00') }

-- Autor (uploaded_by): opcional — si no se envía, el bloque AND se omite del SQL
{ author = param('author', '') }

SELECT
    auth_mode,
    COUNT(*) AS qty_auth
FROM wardriving_vendor
WHERE
    (first_seen at time zone 'America/Mexico_City') BETWEEN ({ first_seen_start }::timestamptz at time zone 'America/Mexico_City')
                                                     AND ({ first_seen_end }::timestamptz at time zone 'America/Mexico_City')

    {#if param('author', false)}
        AND uploaded_by = { author }
    {/if}

GROUP BY auth_mode
ORDER BY qty_auth DESC;
