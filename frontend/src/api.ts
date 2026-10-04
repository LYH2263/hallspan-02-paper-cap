export async function api<T = any>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch('/api' + path, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  })
  if (!res.ok) {
    let message = res.statusText
    try {
      const j = await res.json()
      if (typeof j.detail === 'string') message = j.detail
      else if (j.detail && typeof j.detail === 'object') {
        if (typeof j.detail.message === 'string') message = j.detail.message
        else message = JSON.stringify(j.detail)
      }
    } catch { /* keep statusText */ }
    const err = new Error(message)
    ;(err as any).status = res.status
    throw err
  }
  if (res.status === 204) return undefined as T
  return res.json()
}
