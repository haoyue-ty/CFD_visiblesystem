<script setup lang="ts">
import { zh } from '../presentation/zh-CN'

/**
 * P01 — Entry (website entry).
 * Simple static identity + a single primary CTA into the system.
 * No dynamic hero: a future animated entry replaces the visuals here without
 * changing the button destination.
 */
</script>

<template>
  <main data-page="entry" class="entry">
    <div class="entry__inner">
      <p class="entry__eyebrow">{{ zh("Research digital-experiment & visual-analysis platform") }}</p>
      <h1 class="entry__title">ShockPath</h1>
      <p class="entry__tagline">
        {{ zh("Driven by a real CFD solver and frozen experiments — trace what triggers numerical dissipation, where it acts, and how it reshapes modal and macroscopic flow behaviour.") }}
      </p>
      <p class="entry__description">传统 CFD 工具主要告诉我们“流场发生了什么”。ShockPath 进一步追踪耗散由什么触发、作用在哪里、如何分配、如何影响不同模态，以及最终产生怎样的宏观响应。</p>
      <RouterLink class="entry__cta" :to="{ name: 'home' }" data-testid="enter-system">{{ zh("进入系统 / Enter the system") }}</RouterLink>
      <RouterLink class="entry__secondary" :to="{ name: 'lab' }">{{ zh('进入实验室 / Open the Lab') }}</RouterLink>
      <p class="entry__note">{{ zh("Replay-first: the platform reads already-recorded experiments. No solver is launched.") }}</p>
    </div>
  </main>
</template>

<style scoped>
.entry { display: flex; align-items: center; justify-content: center; min-height: 70vh; padding: 2rem; }
.entry__inner { max-width: 44rem; text-align: center; }
.entry__eyebrow { font-size: 0.8rem; letter-spacing: 0.08em; text-transform: uppercase; color: #666; }
.entry__title { font-size: 3rem; margin: 0.4rem 0; }
.entry__tagline { font-size: 1.05rem; color: #333; line-height: 1.6; }
.entry__cta {
  display: inline-block; margin-top: 1.5rem; padding: 0.7rem 1.6rem;
  background: #1a4f8a; color: #fff; text-decoration: none; border-radius: 4px; font-weight: 600;
}
.entry__cta:hover { background: #143c69; }
.entry__description { font-size: .95rem; color: #444; line-height: 1.8; }
.entry__secondary { display: inline-block; margin-left: 1rem; color: #1a4f8a; }
.entry__note { margin-top: 1rem; font-size: 0.8rem; color: #777; }
</style>
