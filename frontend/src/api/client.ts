import axios from 'axios'

//axios默认配置
const client = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
  paramsSerializer: {
    indexes: null,  // 去掉数组参数的 [] 后缀：tags[]=x → tags=x
  },
})

client.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail?.[0]?.msg || err.response?.data?.detail || err.message
    console.error('[API Error]', msg)
    return Promise.reject(err)
  },
)

export default client