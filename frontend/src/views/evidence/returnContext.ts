import type { RouteLocationRaw } from 'vue-router'
/** Query data may select an internal route, never an external URL or filesystem path. */
export function returnContext(raw: unknown): RouteLocationRaw | null {
  if (typeof raw !== 'string' || raw.length > 12000) return null
  try {
    const value = JSON.parse(raw)
    const names = ['entry', 'home', 'lab', 'experiment', 'cross-flow', 'explore', 'mechanism', 'evidence-center']
    if (!value || !names.includes(value.name) || Object.keys(value).some(k => !['name', 'params', 'query'].includes(k))) return null
    for (const obj of [value.params, value.query]) {
      if (obj === undefined) continue
      if (obj === null || typeof obj !== 'object' || Array.isArray(obj)) return null
      if (Object.values(obj).some(v => !(v === null || typeof v === 'string' || typeof v === 'number' || (Array.isArray(v) && v.every(x => x === null || typeof x === 'string'))))) return null
    }
    if (value.name === 'experiment' && typeof value.params?.experiment_id !== 'string') return null
    return value as RouteLocationRaw
  } catch { return null }
}
