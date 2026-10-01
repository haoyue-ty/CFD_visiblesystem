/** CONTENT02/03 and mechanism evidence are API-only, including development. */
import { api } from '../services/api'
import type { components } from '../types/generated/api'
import type { Loaded } from './domain'

type S = components['schemas']
export type MechanismContent = S['MechanismContent']
export type ScenePreset = S['ScenePreset']
export type SceneList = S['SceneList']
export type MechanismEvidence = S['EvidenceRecord']

async function load<T>(request: Promise<{ data?: unknown; error?: unknown; response: Response }>, origin: Loaded<T>['origin']): Promise<Loaded<T>> {
  try {
    const result = await request
    const envelope = (result.data ?? result.error) as { data?: T; availability?: string; error?: S['ErrorBody'] }
    if (!result.response.ok || envelope?.availability !== 'AVAILABLE' || !envelope.data) {
      return { state: 'ERROR', data: null, origin, reason: envelope?.error?.message ?? `API request failed (${result.response.status})` }
    }
    return { state: 'READY', data: envelope.data, origin, reason: null }
  } catch (error) {
    if ((error as Error).name === 'AbortError') throw error
    return { state: 'ERROR', data: null, origin, reason: (error as Error).message }
  }
}

export const contentService = {
  scenes: (signal?: AbortSignal) => load<SceneList>(api.GET('/api/v1/explore/scenes', { signal }), 'SCHEMATIC'),
  gateComparison: (signal?: AbortSignal) => load<S['AllocationComparison']>(api.GET('/api/v1/allocations/comparison', { params: { query: { experiment_id: 'gate', representation_type: 'CELL_FIELD' } }, signal }), 'FROZEN_PRODUCTION'),
  mechanism: async (signal?: AbortSignal): Promise<Loaded<MechanismContent>> => {
    const result = await load<MechanismContent>(api.GET('/api/v1/mechanism', { signal }), 'SCHEMATIC')
    if (result.data && result.data.data_origin !== 'SCHEMATIC') return { state: 'ERROR', data: null, origin: 'SCHEMATIC', reason: 'Mechanism content must be SCHEMATIC' }
    return result
  },
  scene: (scene_id: number, signal?: AbortSignal) => load<ScenePreset>(api.GET('/api/v1/explore/scenes/{scene_id}', { params: { path: { scene_id } }, signal }), 'SCHEMATIC'),
  evidence: (evidence_id: string, signal?: AbortSignal) => load<MechanismEvidence>(api.GET('/api/v1/evidence/{evidence_id}', { params: { path: { evidence_id } }, signal }), 'VERIFIED_PRODUCTION'),
}
