<script setup lang="ts">
import { useThemeStore } from '@/stores/theme'
import AppLayout from '@/layouts/AppLayout.vue'

const themeStore = useThemeStore()
</script>

<template>
  <n-config-provider :theme="themeStore.theme" :theme-overrides="themeStore.themeOverrides">
    <n-notification-provider>
      <n-message-provider>
        <n-loading-bar-provider>
          <AppLayout />
        </n-loading-bar-provider>
      </n-message-provider>
    </n-notification-provider>
  </n-config-provider>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap');

/* ── 亮色主题（默认） ──────────────────────────────────────── */
body[data-theme="light"], body:not([data-theme]) {
  --bg:          #FAFAF9;
  --surface:     #FFFFFF;
  --surface-2:   #F4F4F5;
  --border:      rgba(0, 0, 0, 0.08);
  --border-hov:  rgba(0, 0, 0, 0.15);
  --text-1:      #111318;
  --text-2:      #6B7280;
  --text-3:      #9CA3AF;
  --accent:      #6366F1;
  --accent-soft: rgba(99, 102, 241, 0.1);
  --shadow-sm:   0 1px 2px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.1);
  --shadow-md:   0 4px 6px rgba(0,0,0,0.07), 0 10px 15px rgba(0,0,0,0.1);
}

/* ── 暗色主题 ──────────────────────────────────────────────── */
body[data-theme="dark"] {
  --bg:          #0F0F11;
  --surface:     #18181B;
  --surface-2:   #252529;
  --border:      rgba(255, 255, 255, 0.08);
  --border-hov:  rgba(255, 255, 255, 0.15);
  --text-1:      #F4F4F5;
  --text-2:      #A1A1AA;
  --text-3:      #52525B;
  --accent:      #818CF8;
  --accent-soft: rgba(129, 140, 248, 0.12);
  --shadow-sm:   0 1px 3px rgba(0,0,0,0.4);
  --shadow-md:   0 4px 16px rgba(0,0,0,0.5);
}

/* ── 基础 ──────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--bg);
  color: var(--text-1);
  font-family: 'Inter', 'PingFang SC', 'Helvetica Neue', sans-serif;
  font-size: 14px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  transition: background 0.25s ease, color 0.25s ease;
}

/* ── 滚动条 ─────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-hov); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-3); }

/* ── 文字选中 ───────────────────────────────────────────────── */
::selection { background: var(--accent-soft); }

/* ── 全局 Naive UI 覆盖 ─────────────────────────────────────── */
.n-layout, .n-layout-content, .n-layout-header, .n-layout-sider {
  background: transparent !important;
}
.n-card {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  box-shadow: var(--shadow-sm) !important;
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.15s !important;
}
.n-card:hover {
  border-color: var(--border-hov) !important;
  box-shadow: var(--shadow-md) !important;
}
.n-button { transition: transform 0.1s, box-shadow 0.15s !important; }
.n-button:active { transform: scale(0.97) !important; }

/* ── 页面过渡 ───────────────────────────────────────────────── */
.page-enter-active { animation: pageIn 0.22s ease-out; }
.page-leave-active { animation: pageOut 0.15s ease-in; }
@keyframes pageIn  { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
@keyframes pageOut { from { opacity: 1; } to { opacity: 0; } }

#app { width: 100%; margin: 0; min-height: 100vh; }
</style>
