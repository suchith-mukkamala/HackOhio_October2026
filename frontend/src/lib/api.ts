// Thin fetch wrapper. All backend routes live under /api (proxied in dev, rewritten on Vercel).
export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    // FastAPI validation errors arrive as a list of {msg}
    const detail = Array.isArray(body.detail) ? body.detail.map((d: { msg: string }) => d.msg).join('. ') : body.detail
    throw new ApiError(res.status, detail ?? res.statusText)
  }
  return res.status === 204 ? (undefined as T) : res.json()
}

export const post = <T>(path: string, body?: unknown) =>
  api<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })

export const put = <T>(path: string, body?: unknown) =>
  api<T>(path, { method: 'PUT', body: body === undefined ? undefined : JSON.stringify(body) })
