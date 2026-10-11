import type { RunRecord } from '../data/v2/runs'
export function runProgress(run: Pick<RunRecord, 'physical_time' | 'requested_final_time'>): number {
  return run.requested_final_time > 0 ? Math.max(0, Math.min(100, 100 * run.physical_time / run.requested_final_time)) : 0
}
export function runCaseName(caseId: string): string { return caseId === 'case8' ? 'Case 8 · 强激波横向扰动' : caseId }
export function runDate(value: string | null): string {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '尚未开始'
}
