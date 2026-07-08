<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useThemeStore } from '@/stores/theme'

const router = useRouter()
const route = useRoute()
const themeStore = useThemeStore()

const navItems = [
  { label: '周报',   key: '/brief',     emoji: '📊' },
  { label: '资讯',   key: '/articles',  emoji: '📰' },
  { label: '搜索',   key: '/search',    emoji: '🔍' },
  { label: '知识库', key: '/knowledge', emoji: '🧠' },
  { label: '仪表盘', key: '/dashboard', emoji: '📊' },
  { label: '来源',   key: '/sources',   emoji: '📡' },
  { label: '兴趣',   key: '/interests', emoji: '🎯' },
]

function isActive(key: string) { return route.path.startsWith(key) }
function go(key: string) { router.push(key) }
</script>

<template>
  <div class="app-shell">
    <!-- 顶部导航 -->
    <header class="topnav">
      <!-- 品牌 -->
      <div class="brand" @click="go('/brief')">
        <div class="brand-icon">F</div>
        <span class="brand-name">FrontierAI<span class="brand-sub"> Pulse</span></span>
      </div>

      <!-- 导航项 -->
      <nav class="nav-links">
        <a v-for="item in navItems" :key="item.key"
          class="nav-link" :class="{ active: isActive(item.key) }"
          @click="go(item.key)">
          <span class="nav-emoji">{{ item.emoji }}</span>
          <span>{{ item.label }}</span>
        </a>
      </nav>

      <!-- 右侧操作 -->
      <div class="nav-actions">
        <button class="theme-btn" :title="themeStore.isDark ? '切换亮色' : '切换暗色'"
          @click="themeStore.toggle()">
          <span>{{ themeStore.isDark ? '☀️' : '🌙' }}</span>
        </button>
      </div>
    </header>

    <!-- 内容区 -->
    <main class="app-main">
      <n-scrollbar style="height: 100%">
        <div class="content-wrapper">
          <router-view v-slot="{ Component }">
            <transition name="page" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </n-scrollbar>
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg);
}

/* ── 顶部导航 ────────────────────────────────────────────────── */
.topnav {
  height: 56px;
  display: flex;
  align-items: center;
  gap: 0;
  padding: 0 24px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(12px);
  background: color-mix(in srgb, var(--surface) 85%, transparent);
}

/* 品牌 */
.brand {
  display: flex;
  align-items: center;
  gap: 9px;
  cursor: pointer;
  flex-shrink: 0;
  margin-right: 28px;
  text-decoration: none;
}
.brand-icon {
  width: 30px;
  height: 30px;
  background: var(--accent);
  color: #fff;
  font-weight: 700;
  font-size: 15px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.15s;
}
.brand:hover .brand-icon { transform: rotate(-6deg) scale(1.05); }
.brand-name {
  font-weight: 600;
  font-size: 15px;
  color: var(--text-1);
  letter-spacing: -0.01em;
}
.brand-sub { color: var(--text-3); font-weight: 400; }

/* 导航链接 */
.nav-links {
  display: flex;
  align-items: center;
  gap: 2px;
  flex: 1;
  overflow-x: auto;
  scrollbar-width: none;
}
.nav-links::-webkit-scrollbar { display: none; }

.nav-link {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 11px;
  border-radius: 7px;
  font-size: 13.5px;
  font-weight: 450;
  color: var(--text-2);
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
  white-space: nowrap;
  user-select: none;
  text-decoration: none;
}
.nav-link:hover {
  background: var(--surface-2);
  color: var(--text-1);
}
.nav-link.active {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 500;
}
.nav-emoji { font-size: 13px; }

/* 右侧按钮 */
.nav-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  margin-left: 12px;
}

.theme-btn {
  width: 34px;
  height: 34px;
  border: 1px solid var(--border);
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  transition: background 0.12s, border-color 0.12s, transform 0.1s;
  color: var(--text-2);
}
.theme-btn:hover {
  background: var(--surface-2);
  border-color: var(--border-hov);
}
.theme-btn:active { transform: scale(0.93); }

/* ── 内容区 ──────────────────────────────────────────────────── */
.app-main {
  flex: 1;
  overflow: hidden;
}
.content-wrapper {
  padding: 28px 32px 48px;
  max-width: 1200px;
  margin: 0 auto;
}
</style>
