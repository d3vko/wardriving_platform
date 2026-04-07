{@config ttl = 600}

{ first_seen_start = param('first_seen_start', '2025-01-01T00:00:00-06:00') }
{ first_seen_end   = param('first_seen_end',   '2026-05-30T00:00:00-06:00') }
{ author = param('author', '') }

SELECT
    mac,
    registry,
    vendor,
    source,
    ssid,
    auth_mode,
    first_seen,
    channel,
    rssi,
    signal_streng,
    device_source,
    uploaded_by,
    type,
    current_latitude,
    current_longitude,
    altitude_meters,
    accuracy_meters
FROM wardriving_vendor
WHERE
    (first_seen at time zone 'America/Mexico_City') BETWEEN ({ first_seen_start }::timestamptz at time zone 'America/Mexico_City')
                                                     AND ({ first_seen_end }::timestamptz at time zone 'America/Mexico_City')

    {#if param('author', false)}
        AND uploaded_by = { author }
    {/if}

ORDER BY first_seen DESC
LIMIT 250;
