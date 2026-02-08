-- Change Visual Mode to Cake graph
-- Copy Paste the name of Bi table in your metabase implementation
-- D02 - Quantity of auth type
SELECT
	auth_mode,
	count(*) as qty_auth
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
GROUP BY auth_mode