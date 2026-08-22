import type { ThemeConfig } from 'antd'

export type ColorMode = 'light' | 'dark'

/** Paleta RF Village MX (logo: violeta + lima neón sobre carbón). */
export const RF_VILLAGE = {
  purple: '#B026FF',
  purpleDeep: '#7B1FA2',
  neon: '#4AF626',
  cyan: '#2EE6D6',
  bgLayout: '#0B0B0D',
  bgContainer: '#16141C',
  bgElevated: '#1E1B26',
  sider: '#07060A',
  text: '#F5F5F7',
  textSecondary: '#C4C0CC',
} as const

const fontFamily =
  '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'

export function getAntdTheme(mode: ColorMode): ThemeConfig {
  if (mode === 'light') {
    return {
      token: {
        colorPrimary: RF_VILLAGE.purple,
        colorSuccess: '#22C55E',
        colorInfo: RF_VILLAGE.purple,
        colorLink: RF_VILLAGE.purpleDeep,
        borderRadius: 8,
        fontFamily,
      },
      components: {
        Menu: {
          itemSelectedBg: 'rgba(176, 38, 255, 0.12)',
          itemSelectedColor: RF_VILLAGE.purpleDeep,
        },
      },
    }
  }

  return {
    token: {
      colorPrimary: RF_VILLAGE.purple,
      colorSuccess: RF_VILLAGE.neon,
      colorInfo: RF_VILLAGE.cyan,
      colorLink: RF_VILLAGE.neon,
      colorBgLayout: RF_VILLAGE.bgLayout,
      colorBgContainer: RF_VILLAGE.bgContainer,
      colorBgElevated: RF_VILLAGE.bgElevated,
      colorText: RF_VILLAGE.text,
      colorTextSecondary: RF_VILLAGE.textSecondary,
      colorBorder: 'rgba(176, 38, 255, 0.28)',
      colorBorderSecondary: 'rgba(74, 246, 38, 0.18)',
      borderRadius: 8,
      fontFamily,
    },
    components: {
      Layout: {
        siderBg: RF_VILLAGE.sider,
        headerBg: RF_VILLAGE.bgContainer,
        bodyBg: RF_VILLAGE.bgLayout,
        triggerBg: RF_VILLAGE.sider,
      },
      Menu: {
        darkItemBg: RF_VILLAGE.sider,
        darkSubMenuItemBg: RF_VILLAGE.sider,
        darkItemSelectedBg: RF_VILLAGE.neon,
        darkItemSelectedColor: RF_VILLAGE.bgLayout,
        darkItemHoverBg: 'rgba(176, 38, 255, 0.22)',
        darkItemColor: 'rgba(245, 245, 247, 0.85)',
      },
      Button: {
        primaryShadow: '0 0 10px rgba(176, 38, 255, 0.45)',
      },
      Card: {
        colorBgContainer: RF_VILLAGE.bgContainer,
      },
    },
  }
}
