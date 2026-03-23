function parseEnvMultiline(value: string | undefined, fallback: string): string {
  const raw = (value ?? "").trim()
  if (!raw) return fallback
  return raw.replace(/\\n/g, "\n")
}

export const appConfig = {
  appTitle: (import.meta.env.VITE_APP_TITLE || "Wardriving CTF").trim(),
  appFaviconUrl: (import.meta.env.VITE_APP_FAVICON_URL || "/ctf/vite.svg").trim(),
  homeTitle: (import.meta.env.VITE_EVENT_HOME_TITLE || "Platform Home").trim(),
  homeBadge: (import.meta.env.VITE_EVENT_HOME_BADGE || "Event").trim(),
  introText: parseEnvMultiline(
    import.meta.env.VITE_EVENT_INTRO_TEXT,
    "Welcome to the wardriving event platform. Here you can upload captures, review analytics, explore WiFi/LTE maps, and download your KML results.",
  ),
  dynamicsTitle: (import.meta.env.VITE_EVENT_DYNAMICS_TITLE || "Event Dynamics").trim(),
  dynamicsText: parseEnvMultiline(
    import.meta.env.VITE_EVENT_DYNAMICS_TEXT,
    "1) Collect samples using supported devices.\n2) Upload your files in the Upload section.\n3) Review findings in Maps and Analytics.\n4) Export your results from KML Downloads.",
  ),
  logoCardTitle: (import.meta.env.VITE_EVENT_LOGO_SECTION_TITLE || "Event Branding").trim(),
  logoCardText: parseEnvMultiline(
    import.meta.env.VITE_EVENT_LOGO_SECTION_TEXT,
    "Use this area to display your event logo and an optional official website link.",
  ),
  logoUrl: (import.meta.env.VITE_EVENT_LOGO_URL || "").trim(),
  logoAlt: (import.meta.env.VITE_EVENT_LOGO_ALT || "Event logo").trim(),
  logoLinkUrl: (import.meta.env.VITE_EVENT_LOGO_LINK_URL || "").trim(),
  logoLinkLabel: (import.meta.env.VITE_EVENT_LOGO_LINK_LABEL || "Open event website").trim(),
}
