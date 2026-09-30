import createClient from 'openapi-fetch'
import type { paths } from '../types/generated/api'

export const api = createClient<paths>({ baseUrl: '' })
