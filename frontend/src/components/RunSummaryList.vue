<script setup lang="ts">
import { statusLabels, type RunRecord } from '../data/v2/runs'
import { runProgress, runCaseName, runDate } from '../presentation/runs'
defineProps<{ runs: RunRecord[] }>()
</script>
<template>
  <ul class="run-list">
    <li v-for="run in runs" :key="run.run_id" class="run-card sp-panel" data-testid="run-list-item">
      <div class="run-card__head">
        <RouterLink :to="`/runs/${run.run_id}`" class="run-card__name">{{ runCaseName(run.experiment.normalized_config.case_id) }}</RouterLink>
        <span class="sp-badge" :data-status="run.status">{{ statusLabels[run.status] }}</span>
      </div>
      <div class="run-card__body">
        <div><p>{{ run.experiment.normalized_config.grid.nx }} × {{ run.experiment.normalized_config.grid.ny }} · CFL={{ run.experiment.normalized_config.time.cfl }} · T={{ run.requested_final_time }}</p>
          <p class="sp-muted">q_aa={{ run.experiment.normalized_config.method.q_aa }} · q_at={{ run.experiment.normalized_config.method.q_at }}</p></div>
        <div class="run-card__progress"><progress :value="runProgress(run)" max="100" aria-label="求解进度"></progress>
          <p class="sp-muted">{{ runProgress(run).toFixed(1) }}% · {{ run.completed_steps }} / {{ run.planned_steps ?? '待确定' }} 步</p></div>
      </div>
      <div class="run-card__foot"><span class="sp-muted"><time :datetime="run.created_at">{{ runDate(run.created_at) }}</time> · <code>{{ run.run_id }}</code></span>
        <RouterLink :to="`/runs/${run.run_id}`" class="sp-button">{{ run.status === 'COMPLETED' ? '查看结果' : '查看任务' }} →</RouterLink></div>
    </li>
  </ul>
</template>
<style scoped>
.run-list { list-style: none; padding: 0; margin: 0; display: grid; gap: 12px; }
.run-card { padding: 20px; }
.run-card__head, .run-card__foot { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.run-card__name { font-size: 15px; font-weight: 600; text-decoration: none; }
.run-card__body { display: grid; grid-template-columns: minmax(0, 1fr) 220px; gap: 24px; align-items: center; margin: 12px 0; }
p { margin: 4px 0; font-size: 14px; }
progress { width: 100%; height: 6px; accent-color: var(--sp-primary); }
.run-card__foot { border-top: 1px solid var(--sp-border); padding-top: 12px; }
code { font-size: 11px; overflow-wrap: anywhere; }
[data-status="COMPLETED"] { background: #eaf5ee; color: #237249; }
[data-status="FAILED"] { background: #fbecee; color: #923e47; }
[data-status="CANCELLED"] { background: #eef1f5; color: #586778; }
@media (max-width: 600px) { .run-card__body { grid-template-columns: 1fr; gap: 8px; } .run-card__foot > span { width: 100%; } }
</style>
