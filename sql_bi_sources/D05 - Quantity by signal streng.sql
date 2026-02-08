-- Change Visual Mode to Cake graph
-- Copy Paste the name of Bi table in your metabase implementation
-- D05 - Quantity by signal streng
SELECT
	signal_streng,
	count(*) as qty_by_signal
FROM wardriving_vendor
WHERE
	{{ssid}}
	AND {{device_source}}
	AND {{author}}
	AND {{first_seen}}
	AND {{bssid}}
	AND {{auth_mode}}
	AND {{vendor}}
	AND {{signal_streng}}
GROUP BY signal_streng