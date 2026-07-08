import { defineStore } from 'pinia'
import { ref }         from 'vue'
import * as api        from '@/api'
import type { WeeklyReportData } from '@/types/report'

// sessionStorage key — 页面刷新后保留，关闭标签页/浏览器后自动清除
const CACHE_KEY = 'weekly-report-cache'

function readCache(): WeeklyReportData | null {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY)
    return raw ? (JSON.parse(raw) as WeeklyReportData) : null
  } catch {
    return null
  }
}

function writeCache(d: WeeklyReportData) {
  try {
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(d))
  } catch {
    // 存储空间不足时静默忽略，不影响正常使用
  }
}

function clearCache() {
  sessionStorage.removeItem(CACHE_KEY)
}

export const useWeeklyReportStore = defineStore('weeklyReport', () => {
  // 初始化时优先从 sessionStorage 恢复（解决页面刷新后数据丢失问题）
  const cached = readCache()
  const data    = ref<WeeklyReportData | null>(cached)
  const loading = ref(false)
  const error   = ref(false)
  const loaded  = ref(cached !== null)  // 有缓存则视为已加载

  /**
   * 首次进入时调用。
   * - 内存或 sessionStorage 中有缓存 → 直接使用，不发请求
   * - 无缓存 → 请求 API 并写入 sessionStorage
   */
  async function load() {
    if (loaded.value) return
    await _fetch()
  }

  /**
   * 用户主动点击刷新按钮时调用。
   * 清除 sessionStorage 缓存，强制重新请求。
   */
  async function refresh() {
    clearCache()
    await _fetch()
  }

  async function _fetch() {
    loading.value = true
    error.value   = false
    try {
      const result = await api.getWeeklyReport()
      data.value   = result
      loaded.value = true
      writeCache(result)           // 写入 sessionStorage，页面刷新后可恢复
    } catch {
      error.value = true
    } finally {
      loading.value = false
    }
  }

  return { data, loading, error, loaded, load, refresh }
})
