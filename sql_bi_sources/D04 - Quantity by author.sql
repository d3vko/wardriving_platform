-- Change Visual Mode to Cake graph
-- Copy Paste the name of Bi table in your metabase implementation
-- D04 - Quantity by author
SELECT
	uploaded_by,
	count(*) as qty_by_author
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
GROUP BY uploaded_by