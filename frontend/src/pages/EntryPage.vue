<script setup lang="ts">
import { useRoute } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import AuthControls from '../components/AuthControls.vue'
const route = useRoute()
</script>

<template>
  <main class="entry" data-page="entry" aria-labelledby="entry-heading">
    <header class="entry__masthead">
      <span class="entry__brand"><AppIcon name="layers" />ShockPath</span>
      <div class="entry__top-right"><span class="entry__category">CFD 数值实验与可视分析</span><AuthControls /></div>
    </header>

    <section class="entry__poster" aria-labelledby="entry-heading">
      <p class="entry__eyebrow">熵稳定框架 · 跨模态耗散路径</p>
      <h1 id="entry-heading">让数值耗散<span>可调、可辨、可追溯</span></h1>
      <p class="entry__summary">从参数调节到空间分配，再到流动响应，<br class="entry__desktop-break" />让每一条耗散路径都有据可查。</p>
      <div class="entry__actions">
        <RouterLink :to="{ name: 'home', query: route.query, hash: route.hash }" class="entry__button entry__start" data-testid="start-experiment">开始实验<AppIcon name="arrow" /></RouterLink>
        <RouterLink :to="{ name: 'research-details', query: route.query }" class="entry__button entry__details" data-testid="research-details-link">了解详情<AppIcon name="book" /></RouterLink>
      </div>
    </section>

    <footer class="entry__footer">
      <dl class="entry__advantages" aria-label="论文与求解器的核心优势">
        <div><dt><span aria-hidden="true">01</span>耗散可调</dt><dd>分别调节声学与切向耗散路径</dd></div>
        <div><dt><span aria-hidden="true">02</span>机制可辨</dt><dd>区分触发信息与作用方向</dd></div>
        <div><dt><span aria-hidden="true">03</span>证据可追溯</dt><dd>连接熵预算、空间分配与真实结果</dd></div>
      </dl>
      <p class="entry__signature">论文方法 × 真实 CFD 求解 × 可视分析</p>
    </footer>
  </main>
</template>

<style scoped>
#app main.entry { display: flex; flex-direction: column; min-height: 100svh; max-width: none; padding: 32px clamp(24px, 5vw, 80px) 24px; background: #edf3fb url('/images/entry-atmosphere.webp') center / cover no-repeat; }
.entry__masthead { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.entry__brand { display: inline-flex; align-items: center; gap: 10px; color: #315ecb; font-size: 24px; font-weight: 650; letter-spacing: -.7px; }
.entry__brand .sp-icon { width: 28px; height: 28px; }
.entry__category { color: #536780; font-size: 12px; letter-spacing: 1px; }
.entry__top-right { display: flex; align-items: center; gap: 28px; }
.entry__poster { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: clamp(40px, 6vh, 80px) 0; text-align: center; }
.entry__eyebrow { margin: 0 0 24px; color: #47648a; font-size: 13px; letter-spacing: 3px; }
.entry__poster h1 { margin: 0; font-size: clamp(38px, 5.2vw, 76px); font-weight: 650; line-height: 1.3; letter-spacing: -.025em; color: #243955; }
.entry__poster h1 span { display: block; color: #315ecb; margin-top: 8px; }
.entry__summary { margin: 28px 0 0; color: #536780; font-size: clamp(14px, 1.3vw, 17px); line-height: 1.9; }
.entry__actions { display: flex; justify-content: center; flex-wrap: wrap; gap: 16px; margin-top: 36px; }
.entry__button { display: inline-flex; justify-content: center; align-items: center; gap: 20px; min-width: 176px; min-height: 56px; padding: 14px 28px; border: 1px solid transparent; border-radius: 999px; font-size: 16px; font-weight: 500; text-decoration: none; transition: background .2s, transform .2s, box-shadow .2s; }
.entry__start { background: var(--sp-primary); color: white; box-shadow: 0 8px 28px #4d6bfe26; }
.entry__start:hover { background: var(--sp-primary-hover); transform: translateY(-2px); box-shadow: 0 12px 32px #4d6bfe35; }
.entry__details { background: #ffffffb3; border-color: #a7bbdb; color: #315ecb; }
.entry__details:hover { background: white; transform: translateY(-2px); }
.entry__button:active { transform: translateY(0); }
.entry__footer { width: min(100%, 980px); align-self: center; }
.entry__advantages { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 32px; margin: 0; padding: 24px 0; border-top: 1px solid #b3c6de; }
.entry__advantages dt { display: flex; align-items: center; gap: 12px; font-size: 15px; font-weight: 600; color: #2c4668; }
.entry__advantages dt span { color: #5375a6; font-size: 11px; font-weight: 500; font-variant-numeric: tabular-nums; }
.entry__advantages dd { margin: 8px 0 0 28px; color: #536780; font-size: 12px; }
.entry__signature { margin: 8px 0 0; text-align: center; font-size: 11px; letter-spacing: 1.5px; color: #63738a; }
@media (max-width: 600px) {
  #app main.entry { padding: 24px 20px; }
  .entry__brand { font-size: 21px; }
  .entry__category { display: none; }
  .entry__poster { padding: 64px 0 56px; }
  .entry__eyebrow { font-size: 11px; letter-spacing: 2px; margin-bottom: 20px; }
  .entry__poster h1 { font-size: clamp(27px, 7.5vw, 44px); }
  .entry__summary { max-width: 290px; margin-top: 24px; }
  .entry__desktop-break { display: none; }
  .entry__actions { gap: 12px; width: 100%; margin-top: 28px; }
  .entry__button { min-width: 0; gap: 12px; padding: 12px 22px; min-height: 52px; font-size: 14px; }
  .entry__advantages { grid-template-columns: 1fr; gap: 18px; padding: 24px 0; }
  .entry__advantages dd { margin-top: 4px; }
}
</style>
