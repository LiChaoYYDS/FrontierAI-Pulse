import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api'

export const useInterestStore = defineStore('interest', () => {
  const presets = ref<string[]>([])
  const selected = ref<Set<string>>(new Set())

  async function load() {
    const [presetData, userData] = await Promise.all([
      api.getPresetInterests(),
      api.getUserInterests(),
    ])
    presets.value = presetData.interests
    selected.value = new Set(userData.interests)
  }

  async function save(interests: string[]) {
    await api.updateUserInterests(interests)
    selected.value = new Set(interests)
  }

  return { presets, selected, load, save }
})
