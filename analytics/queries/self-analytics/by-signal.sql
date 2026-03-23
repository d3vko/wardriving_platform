{@config ttl = 60}

{ first_seen_start = param('first_seen_start', '2025-01-01T00:00:00-06:00') }
{ first_seen_end   = param('first_seen_end',   '2026-05-30T00:00:00-06:00') }
{ author = param('author', '') }

SELECT
    signal_streng,
    COUNT(*) AS qty_by_signal
FROM wardriving_vendor
WHERE
    first_seen BETWEEN { first_seen_start }::timestamptz AND { first_seen_end }::timestamptz

    {#if param('author', false)}
        AND uploaded_by = { author }
    {/if}

GROUP BY signal_streng
ORDER BY qty_by_signal DESC;
