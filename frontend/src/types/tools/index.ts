export interface CloneTask {
  task_id?: string
  repo?: string
  target?: string
  status: string
  progress: number
  message: string
  error?: string
}
