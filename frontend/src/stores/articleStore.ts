import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api'
import type { Article, ArticleParams, ArticleUpdate } from '@/types/article'

export const useArticleStore = defineStore('article', () => {
  const articles = ref<Article[]>([])
  const total = ref(0)
  const loading = ref(false)

  async function fetchArticles(params: ArticleParams = {}) {
    loading.value = true
    try {
      const res = await api.listArticles(params)
      articles.value = res.items
      total.value = res.total
    } finally {
      loading.value = false
    }
  }

  async function updateArticle(id: number, data: ArticleUpdate) {
    const updated = await api.updateArticle(id, data)
    const idx = articles.value.findIndex(a => a.id === id)
    if (idx !== -1) articles.value[idx] = updated
    return updated
  }

  return { articles, total, loading, fetchArticles, updateArticle }
})
