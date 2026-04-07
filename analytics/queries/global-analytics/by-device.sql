{@config ttl = 600}

{ first_seen_start = param('first_seen_start', '2025-01-01T00:00:00-06:00') }
{ first_seen_end   = param('first_seen_end',   '2026-05-30T00:00:00-06:00') }

SELECT
    device_source,
    COUNT(*) AS qty_device
FROM wardriving_vendor
WHERE
    (first_seen at time zone 'America/Mexico_City') BETWEEN ({ first_seen_start }::timestamptz at time zone 'America/Mexico_City')
                                                     AND ({ first_seen_end }::timestamptz at time zone 'America/Mexico_City')

GROUP BY device_source
ORDER BY qty_device DESC;
