import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api'
import type { SourceItem, CustomSourceCreate } from '@/types/source'

export const useSourceStore = defineStore('source', () => {
  const sources = ref<SourceItem[]>([])
  const allTags = ref<string[]>([])
  const loading = ref(false)

  async function loadSources() {
    const [sourcesData, tagsData] = await Promise.all([
      api.getSources(),
      api.getAllTags(),
    ])
    sources.value = sourcesData
    allTags.value = tagsData
  }

  async function addCustomSource(data: CustomSourceCreate): Promise<SourceItem> {
    const created = await api.addCustomSource(data)
    sources.value = [...sources.value, created]
    return created
  }

  async function toggleSource(sourceId: number, currentActive: boolean) {
    const updated = await api.toggleSourceActive(sourceId, !currentActive)
    const idx = sources.value.findIndex(s => s.id === sourceId)
    if (idx !== -1) sources.value[idx] = updated
  }

  async function removeSource(sourceId: number) {
    await api.deleteSource(sourceId)
    sources.value = sources.value.filter(s => s.id !== sourceId)
  }

  return {
    sources, allTags, loading,
    loadSources, addCustomSource, toggleSource, removeSource,
  }
})
