export interface SourceItem {
  id: number
  name: string
  url: string
  type: string
  description: string | null
  is_active: boolean
  last_fetched: string | null
}

export interface PresetSource {
  key: string
  name: string
  url: string
  type: string
  description: string
  category: string
}
