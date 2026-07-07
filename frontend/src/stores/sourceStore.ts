import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api'
import type { SourceItem, PresetSource } from '@/types/source'

export const useSourceStore = defineStore('source', () => {
  const presets = ref<PresetSource[]>([])
  const sources = ref<SourceItem[]>([])
  const allTags = ref<string[]>([])
  const enabledKeys = ref<Set<string>>(new Set())
  const loading = ref(false)

  async function loadPresets() {
    const [presetsData, userData] = await Promise.all([
      api.getPresetSources(),
      api.getUserSources(),
    ])
    presets.value = presetsData
    enabledKeys.value = new Set(userData.enabled_keys)
  }

  async function loadSources() {
    const [sourcesData, tagsData] = await Promise.all([
      api.getSources(),
      api.getAllTags(),
    ])
    sources.value = sourcesData
    allTags.value = tagsData
  }

  async function toggleSource(key: string) {
    if (enabledKeys.value.has(key)) {
      enabledKeys.value.delete(key)
    } else {
      enabledKeys.value.add(key)
    }
    await api.updateUserSources([...enabledKeys.value])
  }

  async function selectAll() {
    enabledKeys.value = new Set(presets.value.map(s => s.key))
    await api.updateUserSources([...enabledKeys.value])
  }

  async function selectNone() {
    enabledKeys.value = new Set()
    await api.updateUserSources([...enabledKeys.value])
  }

  return {
    presets, sources, allTags, enabledKeys, loading,
    loadPresets, loadSources, toggleSource, selectAll, selectNone,
  }
})
