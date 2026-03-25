{@config ttl = 60}

{ first_seen_start = param('first_seen_start', '2025-01-01T00:00:00-06:00') }
{ first_seen_end   = param('first_seen_end',   '2026-05-30T00:00:00-06:00') }
{ author = param('author', '') }

SELECT
    vendor,
    COUNT(*) AS qty_by_vendor
FROM wardriving_vendor
WHERE
    (first_seen at time zone 'America/Mexico_City') BETWEEN ({ first_seen_start }::timestamptz at time zone 'America/Mexico_City')
                                                     AND ({ first_seen_end }::timestamptz at time zone 'America/Mexico_City')

    {#if param('author', false)}
        AND uploaded_by = { author }
    {/if}

GROUP BY vendor
ORDER BY qty_by_vendor DESC
LIMIT 15;
