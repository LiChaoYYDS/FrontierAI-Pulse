import client from './client.ts'
import type { Article, ArticleParams, ArticleResponse, ArticleUpdate } from '@/types/article'
import type { SourceItem, PresetSource } from '@/types/source'
import type { DashboardSummary } from '@/types/dashboard'
import type { KnowledgeNode, KnowledgeEdge, KnowledgeGraph } from '@/types/knowledge'
import type { AskResponse, EmbedStatus } from '@/types/rag'
import type { CloneTask } from '@/types/tools'

// ── Article ───────────────────────────────────────────────────────────────────
export const listArticles = (params: ArticleParams = {}) =>
  client.get<ArticleResponse>('/articles/list', { params }).then(r => r.data)

export const getArticle = (id: number) =>
  client.get<Article>(`/articles/${id}`).then(r => r.data)

export const updateArticle = (id: number, data: ArticleUpdate) =>
  client.patch<Article>(`/articles/${id}`, data).then(r => r.data)

export const deleteArticle = (id: number) =>
  client.delete(`/articles/${id}`)

export const processArticle = (id: number) =>
  client.post<{ message: string }>(`/articles/${id}/process`).then(r => r.data)

export const batchProcess = () =>
  client.post<{ message: string; success: number; failed: number }>('/articles/batch-process').then(r => r.data)

export const getInsight = (id: number) =>
  client.get<{ insight: string | null; process_status: string | null }>(`/articles/${id}/insight`).then(r => r.data)

// ── Sources ───────────────────────────────────────────────────────────────────
export const getSources = () =>
  client.get<SourceItem[]>('/sources/').then(r => r.data)

export const getAllTags = () =>
  client.get<string[]>('/sources/all-tags').then(r => r.data)

export const fetchSource = (sourceId: number) =>
  client.post<{ source_id: number; new_articles: number }>(`/sources/${sourceId}/fetch`).then(r => r.data)

// ── User Preferences ──────────────────────────────────────────────────────────
export const getPresetSources = () =>
  client.get<PresetSource[]>('/user/preset-sources').then(r => r.data)

export const getUserSources = () =>
  client.get<{ enabled_keys: string[] }>('/user/sources').then(r => r.data)

export const updateUserSources = (enabled_keys: string[]) =>
  client.put<{ enabled_keys: string[]; synced: number }>('/user/sources', { enabled_keys }).then(r => r.data)

// ── User Interests ────────────────────────────────────────────────────────────
export const getPresetInterests = () =>
  client.get<{ interests: string[] }>('/user/interests/preset').then(r => r.data)

export const getUserInterests = () =>
  client.get<{ interests: string[] }>('/user/interests').then(r => r.data)

export const updateUserInterests = (interests: string[]) =>
  client.put<{ interests: string[] }>('/user/interests', { interests }).then(r => r.data)

// ── Brief ─────────────────────────────────────────────────────────────────────
// 简报需要多次 LLM 调用，单独设置 60s 超时（全局默认 15s 不够用）
export const getTodayBrief = () =>
  client.get<{ content: string }>('/brief/today', { timeout: 60000 }).then(r => r.data)

// ── Dashboard ─────────────────────────────────────────────────────────────────
export const getDashboardSummary = () =>
  client.get<DashboardSummary>('/dashboard/summary').then(r => r.data)

export const getWeeklyReport = () =>
  client.get<{ content: string }>('/dashboard/weekly-report').then(r => r.data)

// ── Search ────────────────────────────────────────────────────────────────────
export interface SearchParams {
  q?: string
  tags?: string[]
  source_id?: number
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}

export const searchArticles = (params: SearchParams) =>
  client.get<import('@/types/article').ArticleResponse>('/search/', { params }).then(r => r.data)

export const searchSuggest = (q: string) =>
  client.get<{ suggestions: string[] }>('/search/suggest', { params: { q } }).then(r => r.data)

// ── Knowledge ─────────────────────────────────────────────────────────────────
export const getKnowledgeGraph = () =>
  client.get<KnowledgeGraph>('/knowledge/graph').then(r => r.data)

export const getKnowledgeNodes = (type?: string) =>
  client.get<KnowledgeNode[]>('/knowledge/nodes', { params: type ? { type } : {} }).then(r => r.data)

export const extractKnowledge = (limit = 50) =>
  client.post<{ processed: number; nodes_added: number }>('/knowledge/extract', null, { params: { limit } }).then(r => r.data)

export const getNodeArticles = (nodeId: number) =>
  client.get<import('@/types/article').Article[]>(`/knowledge/nodes/${nodeId}/articles`).then(r => r.data)

// ── RAG 知识库 ────────────────────────────────────────────────────────────────
export const askKnowledge = (question: string, history: { role: string; content: string }[] = []) =>
  client.post<AskResponse>('/rag/ask', { question, history }).then(r => r.data)

export const triggerEmbedAll = () =>
  client.post<{ message: string }>('/rag/embed-all').then(r => r.data)

export const getEmbedStatus = () =>
  client.get<EmbedStatus>('/rag/embed-status').then(r => r.data)

// ── Tools: Git Clone ──────────────────────────────────────────────────────────
export const startClone = (git_url: string, username = '', token = '') =>
  client.post<CloneTask>('/tools/clone', { git_url, username, token }).then(r => r.data)

export const getCloneStatus = (taskId: string) =>
  client.get<CloneTask>(`/tools/clone/${taskId}`).then(r => r.data)

// ── 重新导出类型（供其他模块直接从 @/api 导入时向后兼容） ────────────────────
export type { DashboardSummary, KnowledgeNode, KnowledgeEdge, KnowledgeGraph, AskResponse, EmbedStatus, CloneTask }
