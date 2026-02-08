-- Don't Change Visual by default is table 
-- Copy Paste the name of Bi table in your metabase implementation
-- D01 - Detail table related to analysis
-- You can check/override the original sql code `wardriving_vendor` for view 
--  in wardrive/apps/wardriving/sql_views.py
SELECT
	*
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
ORDER BY first_seen DESC
