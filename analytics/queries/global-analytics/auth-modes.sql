{@config ttl = 60}

-- Rango de fechas sobre wardriving_vendor.first_seen (timestamptz en PostgreSQL)
-- Formato ISO 8601 con offset de zona horaria, p.ej. 2025-01-01T00:00:00-06:00
{ first_seen_start = param('first_seen_start', '2025-01-01T00:00:00-06:00') }
{ first_seen_end   = param('first_seen_end',   '2026-05-30T00:00:00-06:00') }

SELECT
    auth_mode,
    COUNT(*) AS qty_auth
FROM wardriving_vendor
WHERE
    first_seen BETWEEN { first_seen_start }::timestamptz
                   AND { first_seen_end }::timestamptz

GROUP BY auth_mode
ORDER BY qty_auth DESC;
