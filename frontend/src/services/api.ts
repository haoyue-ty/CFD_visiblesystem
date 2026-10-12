import createClient from 'openapi-fetch'
import type { paths } from '../types/generated/api'
import { authState, expireAuthSession } from '../data/auth'

export const api = createClient<paths>({ baseUrl: '' })
api.use({
  onRequest({ request }) {
    if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method) && authState.csrfToken) request.headers.set('X-CSRF-Token', authState.csrfToken)
    return request
  },
  onResponse({ response }) {
    if (response.status === 401) expireAuthSession()
    return response
  },
})
