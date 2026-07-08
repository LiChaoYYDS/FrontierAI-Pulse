export interface KnowledgeNode {
  id: number
  name: string
  type: string
  value: number
}

export interface KnowledgeEdge {
  source: number
  target: number
  strength: number
}

export interface KnowledgeGraph {
  nodes: KnowledgeNode[]
  edges: KnowledgeEdge[]
}
