import { reactive } from 'vue'

export type AuthUser = { id: string; email: string }
type Session = { enabled: boolean; authenticated: boolean; user: AuthUser | null; csrf_token: string; mail_configured: boolean }
export const authState = reactive({ loaded: false, enabled: true, user: null as AuthUser | null, csrfToken: '', mailConfigured: false })
let pending: Promise<void> | undefined

export class AuthError extends Error {
  constructor(message: string, public code = '', public retryAfter = 0) { super(message) }
}

function applySession(session: Session) {
  authState.enabled = session.enabled
  authState.user = session.authenticated ? session.user : null
  authState.csrfToken = session.csrf_token
  authState.mailConfigured = session.mail_configured
  authState.loaded = true
}

async function read<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null)
  if (!response.ok || !payload?.data) throw new AuthError(payload?.error?.message ?? '登录服务暂时不可用，请稍后重试。', payload?.error?.code, Number(response.headers.get('Retry-After') ?? 0))
  return payload.data as T
}

export async function loadAuthSession(force = false): Promise<void> {
  if (pending) return pending
  if (authState.loaded && !force) return
  pending = (async () => {
    const response = await fetch('/api/v1/auth/session', { credentials: 'same-origin', cache: 'no-store' })
    applySession(await read<Session>(response))
  })()
  try { await pending } finally { pending = undefined }
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  await loadAuthSession()
  const response = await fetch(`/api/v1/auth/${path}`, {
    method: 'POST', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': authState.csrfToken },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  })
  try { return await read<T>(response) }
  catch (error) {
    if (error instanceof AuthError && error.code === 'CSRF_FAILED') authState.loaded = false
    throw error
  }
}

export function sendEmailCode(email: string, purpose: 'login' | 'register') {
  return post<{ delivery_status: 'SMTP_ACCEPTED'; expires_in: number; retry_after: number }>('email-verification-challenges', { email, purpose })
}

export async function signInWithEmail(email: string, code: string, purpose: 'login' | 'register') {
  applySession(await post<Session>(purpose, { email, code }))
}

export async function logout() { applySession(await post<Session>('logout')) }

export function expireAuthSession() {
  authState.user = null
  authState.loaded = false
  window.dispatchEvent(new Event('shockpath:auth-expired'))
}

export function safeAuthRedirect(value: unknown) {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//') || /[\\\u0000-\u001f]/.test(value)) return '/home'
  if (!/^\/(home|workspace|experiments\/new|runs|sweeps)(?:[/?#]|$)/.test(value)) return '/home'
  return value
}
