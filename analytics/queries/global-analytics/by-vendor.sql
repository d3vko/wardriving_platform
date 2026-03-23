{@config ttl = 60}

{ first_seen_start = param('first_seen_start', '2025-01-01T00:00:00-06:00') }
{ first_seen_end   = param('first_seen_end',   '2026-05-30T00:00:00-06:00') }

SELECT
    vendor,
    COUNT(*) AS qty_by_vendor
FROM wardriving_vendor
WHERE
    first_seen BETWEEN { first_seen_start }::timestamptz AND { first_seen_end }::timestamptz

GROUP BY vendor
ORDER BY qty_by_vendor DESC
LIMIT 15;
