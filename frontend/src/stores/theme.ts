import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { darkTheme } from 'naive-ui'
import type { GlobalTheme, GlobalThemeOverrides } from 'naive-ui'

export const useThemeStore = defineStore('theme', () => {
  const isDark = ref(
    window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? true
  )

  const theme = computed<GlobalTheme | null>(() => isDark.value ? darkTheme : null)

  const themeOverrides = computed<GlobalThemeOverrides>(() => ({
    common: {
      primaryColor: isDark.value ? '#818CF8' : '#6366F1',
      primaryColorHover: isDark.value ? '#A5B4FC' : '#818CF8',
      primaryColorPressed: isDark.value ? '#6366F1' : '#4F46E5',
      borderRadius: '8px',
      fontFamily: '"Inter", "PingFang SC", "Helvetica Neue", sans-serif',
      bodyColor: isDark.value ? '#0F0F11' : '#FAFAF9',
      cardColor: isDark.value ? '#18181B' : '#FFFFFF',
      popoverColor: isDark.value ? '#1C1C1F' : '#FFFFFF',
      dividerColor: isDark.value ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.08)',
      borderColor: isDark.value ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.1)',
      textColorBase: isDark.value ? '#FAFAFA' : '#111318',
      textColor1: isDark.value ? '#FAFAFA' : '#111318',
      textColor2: isDark.value ? '#A1A1AA' : '#6B7280',
      textColor3: isDark.value ? '#52525B' : '#9CA3AF',
    },
    Card: {
      color: isDark.value ? '#18181B' : '#FFFFFF',
      borderColor: isDark.value ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
      borderRadius: '10px',
    },
    Input: {
      color: isDark.value ? '#252529' : '#FFFFFF',
      colorFocus: isDark.value ? '#2e2e33' : '#FFFFFF',
      border: isDark.value ? '1px solid rgba(255,255,255,0.1)' : '1px solid rgba(0,0,0,0.12)',
      borderFocus: isDark.value ? '1px solid #818CF8' : '1px solid #6366F1',
      textColor: isDark.value ? '#FAFAFA' : '#111318',
      placeholderColor: isDark.value ? '#52525B' : '#9CA3AF',
    },
    Select: {
      peers: {
        InternalSelection: {
          color: isDark.value ? '#252529' : '#FFFFFF',
          colorActive: isDark.value ? '#2e2e33' : '#FFFFFF',
          border: isDark.value ? '1px solid rgba(255,255,255,0.1)' : '1px solid rgba(0,0,0,0.12)',
          borderHover: isDark.value ? '1px solid rgba(255,255,255,0.25)' : '1px solid rgba(0,0,0,0.25)',
          borderActive: isDark.value ? '1px solid #818CF8' : '1px solid #6366F1',
          textColor: isDark.value ? '#FAFAFA' : '#111318',
          placeholderColor: isDark.value ? '#52525B' : '#9CA3AF',
        },
        InternalSelectMenu: {
          color: isDark.value ? '#1C1C1F' : '#FFFFFF',
          optionTextColor: isDark.value ? '#A1A1AA' : '#374151',
          optionTextColorActive: isDark.value ? '#FAFAFA' : '#111318',
          optionColorActive: isDark.value ? 'rgba(129,140,248,0.12)' : 'rgba(99,102,241,0.08)',
        },
      },
    },
    Menu: {
      color: 'transparent',
      itemColorHover: isDark.value ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)',
      itemColorActive: isDark.value ? 'rgba(129,140,248,0.12)' : 'rgba(99,102,241,0.1)',
      itemTextColor: isDark.value ? '#A1A1AA' : '#6B7280',
      itemTextColorHover: isDark.value ? '#FAFAFA' : '#111318',
      itemTextColorActive: isDark.value ? '#A5B4FC' : '#6366F1',
    },
    Progress: {
      railColor: isDark.value ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
    },
    Tag: {
      color: isDark.value ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)',
      borderColor: isDark.value ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
    },
  }))

  // 同步 data-theme 到 body，供 CSS 变量使用
  watch(isDark, (val) => {
    document.body.setAttribute('data-theme', val ? 'dark' : 'light')
  }, { immediate: true })

  function toggle() { isDark.value = !isDark.value }

  return { isDark, theme, themeOverrides, toggle }
})
