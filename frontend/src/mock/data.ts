import type { Article } from '@/types/article'

export interface Source {
  id: number
  name: string
  url: string
  type: 'rss' | 'arxiv' | 'website' | 'github' | 'twitter'
  description: string
  last_fetched: string | null
  is_active: boolean
  reliability_score: number
  created_at: string
}

export const mockSources: Source[] = [
  { id: 1, name: 'arXiv AI', url: 'https://export.arxiv.org/rss/cs.AI', type: 'arxiv', description: '人工智能最新论文预印本', last_fetched: '2026-06-20T08:30:00Z', is_active: true, reliability_score: 95, created_at: '2026-06-01T00:00:00Z' },
  { id: 2, name: 'HuggingFace Blog', url: 'https://huggingface.co/blog/feed.xml', type: 'rss', description: 'HuggingFace 官方博客', last_fetched: '2026-06-20T08:00:00Z', is_active: true, reliability_score: 90, created_at: '2026-06-01T00:00:00Z' },
  { id: 3, name: 'GitHub Trending', url: 'https://github.com/trending', type: 'github', description: 'GitHub 趋势仓库', last_fetched: '2026-06-19T12:00:00Z', is_active: true, reliability_score: 85, created_at: '2026-06-02T00:00:00Z' },
  { id: 4, name: 'OpenAI Blog', url: 'https://openai.com/blog', type: 'website', description: 'OpenAI 官方发布', last_fetched: '2026-06-18T10:00:00Z', is_active: true, reliability_score: 98, created_at: '2026-06-01T00:00:00Z' },
  { id: 5, name: 'Google AI Blog', url: 'https://ai.googleblog.com', type: 'website', description: 'Google AI 研究博客', last_fetched: '2026-06-17T09:00:00Z', is_active: false, reliability_score: 92, created_at: '2026-06-03T00:00:00Z' },
  { id: 6, name: 'ML News Twitter', url: 'https://twitter.com/i/lists/ML', type: 'twitter', description: '机器学习资讯聚合', last_fetched: null, is_active: false, reliability_score: 60, created_at: '2026-06-05T00:00:00Z' },
]

export const mockArticles: Article[] = [
  {
    id: 1, title: 'Llama 4: Meta 发布新一代开源大语言模型',
    url: 'https://example.com/llama-4', content: 'Meta 正式发布 Llama 4 系列模型...',
    summary: 'Meta 发布 Llama 4，参数规模最高达 2T，采用 MoE 架构，在推理、代码生成和多模态任务上超越 GPT-4o。开源协议更宽松，支持商业使用。',
    author: 'Meta AI', published_at: '2026-06-20T10:00:00Z',
    source_id: 1, source_type: 'arxiv',
    tags: ['LLM', 'New Model', 'Open Source'], importance_score: 95,
    is_read: false, is_favorite: true, is_liked: true, notes: null,
    insight: '对你的价值：Llama 开源生态直接影响你的本地部署方案，建议重点跟进。', process_status: 'completed',
    created_at: '2026-06-20T10:05:00Z',
  },
  {
    id: 2, title: 'Diffusion Transformer 3: 图像生成新范式',
    url: 'https://example.com/dit3', content: 'DiT-3 将 Transformer 与扩散模型结合...',
    summary: 'DiT-3 在图像生成质量上超越 Stable Diffusion 3，训练效率提升 40%，支持视频生成扩展。',
    author: 'Stability AI', published_at: '2026-06-19T14:30:00Z',
    source_id: 2, source_type: 'rss',
    tags: ['Multimodal', 'Diffusion', 'Image Generation'], importance_score: 88,
    is_read: false, is_favorite: false, is_liked: false, notes: null,
    insight: '多模态生成是趋势，理解 DiT 架构对后续多模态项目有帮助。', process_status: 'completed',
    created_at: '2026-06-19T14:35:00Z',
  },
  {
    id: 3, title: 'Agentic RAG: 自主检索增强生成框架',
    url: 'https://example.com/agentic-rag', content: 'Agentic RAG 融合了 AI Agent 与检索增强生成...',
    summary: '新框架让 LLM 自主决定何时检索、检索什么、如何整合，相比传统 RAG 准确率提升 25%，幻觉降低 40%。',
    author: 'LangChain Research', published_at: '2026-06-19T09:00:00Z',
    source_id: 1, source_type: 'arxiv',
    tags: ['RAG', 'Agent', 'LLM'], importance_score: 92,
    is_read: true, is_favorite: true, is_liked: true, notes: '值得实现一个 demo',
    insight: 'RAG + Agent 是目前最实用的 AI 工程方向，可以直接用到项目中。', process_status: 'completed',
    created_at: '2026-06-19T09:05:00Z',
  },
  {
    id: 4, title: 'OpenAI 发布 GPT-5: 推理能力质的飞跃',
    url: 'https://example.com/gpt5', content: 'OpenAI 发布 GPT-5...',
    summary: 'GPT-5 在数学推理、代码生成、长文本理解上全面提升，支持 1M Token 上下文窗口，API 价格降低 50%。',
    author: 'OpenAI', published_at: '2026-06-18T16:00:00Z',
    source_id: 4, source_type: 'website',
    tags: ['LLM', 'New Model', 'GPT'], importance_score: 98,
    is_read: true, is_favorite: true, is_liked: true, notes: 'API 降价有利于项目成本控制',
    insight: 'GPT-5 的降价和长上下文能力将极大影响你的项目设计。', process_status: 'completed',
    created_at: '2026-06-18T16:10:00Z',
  },
  {
    id: 5, title: 'CrewAI v2: 多智能体协作框架重大更新',
    url: 'https://example.com/crewai-v2', content: 'CrewAI v2 带来了全新的 Agent 协作模式...',
    summary: '支持动态角色分配、Agent 间辩论机制、可视化执行图谱，与 LangChain 深度集成。',
    author: 'CrewAI', published_at: '2026-06-18T11:00:00Z',
    source_id: 3, source_type: 'github',
    tags: ['Agent', 'Framework', 'Open Source'], importance_score: 85,
    is_read: false, is_favorite: false, is_liked: false, notes: null,
    insight: '多 Agent 框架快速演进，值得在你的项目中实验。', process_status: 'completed',
    created_at: '2026-06-18T11:05:00Z',
  },
  {
    id: 6, title: 'PyTorch 3.0 发布: 原生支持量子计算后端',
    url: 'https://example.com/pytorch3', content: 'PyTorch 3.0 里程碑更新...',
    summary: 'PyTorch 3.0 引入量子计算模块、编译优化提升训练速度 60%、改进分布式训练 API。',
    author: 'Meta', published_at: '2026-06-17T15:00:00Z',
    source_id: 3, source_type: 'github',
    tags: ['Framework', 'PyTorch', 'Quantum'], importance_score: 80,
    is_read: false, is_favorite: false, is_liked: false, notes: null,
    insight: 'PyTorch 生态持续进化，编译优化值得关注。', process_status: 'completed',
    created_at: '2026-06-17T15:05:00Z',
  },
  {
    id: 7, title: 'Mamba-2: 状态空间模型挑战 Transformer',
    url: 'https://example.com/mamba2', content: 'Mamba-2 进一步优化了 SSM 架构...',
    summary: 'Mamba-2 在长序列任务上以 1/10 的计算量达到 Transformer 性能，支持 256K 上下文，推理速度提升 5x。',
    author: 'CMU + Princeton', published_at: '2026-06-17T09:30:00Z',
    source_id: 1, source_type: 'arxiv',
    tags: ['LLM', 'Architecture', 'SSM'], importance_score: 90,
    is_read: true, is_favorite: false, is_liked: true, notes: 'SSM 可能替代 Transformer',
    insight: '非 Transformer 架构进展迅速，是重要的技术趋势。', process_status: 'completed',
    created_at: '2026-06-17T09:35:00Z',
  },
  {
    id: 8, title: 'HuggingFace 推出 Gradio 5: 零代码部署 AI 应用',
    url: 'https://example.com/gradio5', content: 'Gradio 5 大幅简化部署流程...',
    summary: 'Gradio 5 支持一键部署到 HF Spaces，新增组件库，集成监控和日志功能。',
    author: 'HuggingFace', published_at: '2026-06-16T14:00:00Z',
    source_id: 2, source_type: 'rss',
    tags: ['Deployment', 'Tool', 'Open Source'], importance_score: 75,
    is_read: true, is_favorite: false, is_liked: false, notes: '',
    insight: '快速原型工具，可用于项目 Demo 展示。', process_status: 'completed',
    created_at: '2026-06-16T14:05:00Z',
  },
  {
    id: 9, title: 'Google 发布 Gemini 2.5: 原生多模态推理',
    url: 'https://example.com/gemini-25', content: 'Gemini 2.5 重新定义了多模态 AI...',
    summary: 'Gemini 2.5 支持文本、图像、音频、视频原生态理解与生成，推理能力超越人类专家基准。',
    author: 'Google DeepMind', published_at: '2026-06-16T10:00:00Z',
    source_id: 5, source_type: 'website',
    tags: ['LLM', 'Multimodal', 'New Model'], importance_score: 93,
    is_read: false, is_favorite: false, is_liked: false, notes: null,
    insight: '多模态是下一个主战场，需要跟进学习。', process_status: 'completed',
    created_at: '2026-06-16T10:05:00Z',
  },
  {
    id: 10, title: 'Rust 在 AI 工程中的应用越来越广泛',
    url: 'https://example.com/rust-ai', content: '越来越多的 AI 工具链开始使用 Rust...',
    summary: 'Tokenizers、Candle、Burn 等 Rust AI 框架性能优势明显，生态正在快速成长。',
    author: 'Tech Analysis', published_at: '2026-06-15T08:00:00Z',
    source_id: 6, source_type: 'twitter',
    tags: ['Rust', 'Performance', 'Tool'], importance_score: 70,
    is_read: false, is_favorite: false, is_liked: false, notes: null,
    insight: '如果追求极致性能，可以尝试 Rust 实现核心组件。', process_status: 'pending',
    created_at: '2026-06-15T08:05:00Z',
  },
  {
    id: 11, title: '向量数据库对比: pgvector vs Milvus vs Qdrant',
    url: 'https://example.com/vector-db-compare', content: '深度对比主流向量数据库...',
    summary: 'pgvector 在 100 万向量以下性价比最高，Milvus 适合大规模集群，Qdrant 在过滤查询上有优势。',
    author: 'Data Engineering Weekly', published_at: '2026-06-14T12:00:00Z',
    source_id: 1, source_type: 'arxiv',
    tags: ['Database', 'Vector Search', 'Comparison'], importance_score: 82,
    is_read: true, is_favorite: true, is_liked: true, notes: 'pgvector 适合本项目初期使用',
    insight: '选型对比直接指导你的数据库选择。', process_status: 'completed',
    created_at: '2026-06-14T12:05:00Z',
  },
  {
    id: 12, title: 'Fine-tuning 最佳实践: LoRA vs QLoRA vs DoRA',
    url: 'https://example.com/finetuning-compare', content: '参数高效微调方法全面评测...',
    summary: 'DoRA 在保持 LoRA 效率的同时达到全参数微调质量，QLoRA 适合显存受限场景。',
    author: 'HuggingFace', published_at: '2026-06-13T16:00:00Z',
    source_id: 2, source_type: 'rss',
    tags: ['Fine-tuning', 'LLM', 'Practice'], importance_score: 87,
    is_read: false, is_favorite: false, is_liked: false, notes: null,
    insight: 'DoRA 值得在你的模型微调流程中采用。', process_status: 'completed',
    created_at: '2026-06-13T16:05:00Z',
  },
]
