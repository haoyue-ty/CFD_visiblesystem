/** EVI01/02 use the complete frozen DTOs. No synthetic evidence fallback. */
import { api } from '../services/api'
import { zh, factLabels, verificationLabels as statusLabels } from '../presentation/zh-CN'
import type { components, operations } from '../types/generated/api'
import type { Loaded } from './domain'
type S = components['schemas']
export type EvidenceRecord = S['EvidenceRecord']
export type EvidenceItem = S['EvidenceIndexItem']
export type EvidenceIndex = S['EvidenceIndex']
export type EvidenceQuery = NonNullable<operations['EVI01']['parameters']['query']>
export type Fact<T> = { state: 'KNOWN'; value: T } | { state: 'UNKNOWN' | 'MISSING' | 'NOT_APPLICABLE'; reason: string }
export function knownValue<T>(fact: Fact<T>): T | null { return fact.state === 'KNOWN' ? fact.value : null }
export function factText(fact: Fact<unknown>): string {
  if (fact.state !== 'KNOWN') return `${factLabels[fact.state]} — ${zh(fact.reason)}`
  return typeof fact.value === 'object' ? JSON.stringify(fact.value) : typeof fact.value === 'boolean' ? (fact.value ? '是' : '否') : zh(fact.value)
}
export function safeText(text: string): string {
  return text.replace(/file:\/\/[^\s]+|\b[A-Za-z]:[\\/][^\s]+|\\\\[^\s]+|\/(?:home|Users|tmp|var|mnt|opt|workspace)\/[^\s]+/gi, zh('[source locator withheld]'))
}
function publicCopy<T>(value: T): T {
  return JSON.parse(JSON.stringify(value, (_, v) => typeof v === 'string' ? safeText(v) : v)) as T
}
async function load<T>(request: Promise<{ data?: unknown; error?: unknown; response: Response }>): Promise<Loaded<T>> {
  try {
    const result = await request
    const body = (result.data ?? result.error) as { availability?: string; data?: T; error?: S['ErrorBody'] }
    if (!result.response.ok || body?.availability !== 'AVAILABLE' || !body.data) {
      return { state: result.response.status === 404 ? 'MISSING' : 'ERROR', data: null, origin: 'VERIFIED_PRODUCTION',
        reason: safeText(body?.error?.message ?? `API request failed (${result.response.status})`) }
    }
    return { state: 'READY', data: publicCopy(body.data), origin: 'VERIFIED_PRODUCTION', reason: null }
  } catch (error) {
    if ((error as Error).name === 'AbortError') throw error
    return { state: 'ERROR', data: null, origin: 'VERIFIED_PRODUCTION', reason: safeText(String(error)) }
  }
}
export const evidenceService = {
  index: (query: EvidenceQuery, signal?: AbortSignal) => load<EvidenceIndex>(api.GET('/api/v1/evidence', { params: { query }, signal })),
  record: (id: string, signal?: AbortSignal) => load<EvidenceRecord>(api.GET('/api/v1/evidence/{evidence_id}', { params: { path: { evidence_id: id } }, signal })),
  provenance: (id: string, signal?: AbortSignal) => load<S['ResultProvenance']>(api.GET('/api/v1/results/{result_id}/provenance', { params: { path: { result_id: id } }, signal })),
}
export function supports(record: EvidenceRecord): string {
  return record.definitions.map(d => zh(d.definition)).join('；') || record.verification.basis.map(zh).join('；') || zh('Unknown — support is not recorded.')
}
export function nonNumerical(record: EvidenceRecord): boolean { return record.result_ids.length === 0 }
export const verificationLabels: Record<S['Verification']['status'], string> = {
  FROZEN_VERIFIED: statusLabels.FROZEN_VERIFIED, VERIFIED_NOT_FROZEN: statusLabels.VERIFIED_NOT_FROZEN, DERIVED_VERIFIED: statusLabels.DERIVED_VERIFIED,
  AVAILABLE_UNVERIFIED: statusLabels.AVAILABLE_UNVERIFIED, PARTIAL: statusLabels.PARTIAL, MISSING: statusLabels.MISSING, LEGACY: statusLabels.LEGACY,
  SUPERSEDED: statusLabels.SUPERSEDED, NOT_APPLICABLE: statusLabels.NOT_APPLICABLE,
}
/** One presentation vocabulary; keep source status visible without promoting it. */
export function verificationText(verification: Pick<S['Verification'], 'status'> & Partial<Pick<S['Verification'], 'canonical_status'>>): string {
  return `${verification.canonical_status ? statusLabels[verification.canonical_status] : verificationLabels[verification.status]} · 来源状态：${verificationLabels[verification.status]}`
}
