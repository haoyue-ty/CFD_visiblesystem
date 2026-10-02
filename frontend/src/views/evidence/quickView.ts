import { shallowRef } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
export const quickView = shallowRef<{ id: string; target: RouteLocationRaw; trigger: HTMLElement | null } | null>(null)
export function openEvidence(id: string, target: RouteLocationRaw) {
  quickView.value = { id, target, trigger: document.activeElement instanceof HTMLElement ? document.activeElement : null }
}
export function closeEvidence() {
  const trigger = quickView.value?.trigger
  quickView.value = null
  requestAnimationFrame(() => trigger?.isConnected && trigger.focus())
}
