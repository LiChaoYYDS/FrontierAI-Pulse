import { defineStore } from 'pinia'
import { ref } from 'vue'
import { marked } from 'marked'
import * as api from '@/api'

// 配置 marked：链接在新标签打开
marked.use({
  renderer: {
    link(token) {
      return `<a href="${token.href}" target="_blank" rel="noopener">${token.text}</a>`
    },
  },
})

export const useWeeklyReportStore = defineStore('weeklyReport', () => {
  const rawContent = ref('')   // 原始 Markdown 文本
  const html       = ref('')   // 渲染后的 HTML
  const loading    = ref(false)
  const error      = ref(false)
  const loaded     = ref(false) // 本次运行期间是否已加载过

  /**
   * 加载周报内容。
   * 若本次运行内已加载过（loaded = true），直接返回，不重复请求。
   */
  async function load() {
    if (loaded.value) return
    await _fetch()
  }

  /**
   * 强制刷新周报（右上角刷新按钮触发）。
   * 不管是否已加载，都重新请求并覆盖缓存。
   */
  async function refresh() {
    await _fetch()
  }

  async function _fetch() {
    loading.value = true
    error.value   = false
    try {
      const res      = await api.getWeeklyReport()
      rawContent.value = res.content
      html.value       = await marked(res.content) as string
      loaded.value     = true
    } catch {
      error.value = true
    } finally {
      loading.value = false
    }
  }

  return { rawContent, html, loading, error, loaded, load, refresh }
})
