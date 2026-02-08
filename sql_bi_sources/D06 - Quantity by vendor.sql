-- Change Visual Mode to Cake graph
-- Copy Paste the name of Bi table in your metabase implementation
-- D06 - Quantity by vendor
SELECT
	vendor,
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
GROUP BY vendor