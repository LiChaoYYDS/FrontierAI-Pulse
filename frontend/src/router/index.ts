import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/brief' },
  { path: '/brief',        name: 'Brief',         component: () => import('@/views/Brief/WeeklyReportPage.vue') },
  { path: '/weekly-report', redirect: '/brief' },
  { path: '/history',      name: 'History',       component: () => import('@/views/History/HistoryPage.vue') },
  { path: '/articles',     name: 'Articles',       component: () => import('@/views/Article/ArticlePage.vue') },
  { path: '/articles/:id', name: 'ArticleDetail',  component: () => import('@/views/Article/ArticleDetailPage.vue') },
  { path: '/sources',      name: 'Sources',        component: () => import('@/views/Source/SourcePage.vue') },
  { path: '/interests',    name: 'Interests',      component: () => import('@/views/Interest/InterestPage.vue') },
  { path: '/dashboard',    name: 'Dashboard',      component: () => import('@/views/Dashboard/DashboardPage.vue') },
  { path: '/search',       name: 'Search',         component: () => import('@/views/Search/SearchPage.vue') },
  { path: '/knowledge',    name: 'Knowledge',      component: () => import('@/views/Knowledge/KnowledgePage.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
