<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { AuthError, authState, loadAuthSession, safeAuthRedirect, sendEmailCode, signInWithEmail } from '../data/auth'

const route = useRoute(), router = useRouter()
const register = computed(() => route.name === 'register')
const purpose = computed(() => register.value ? 'register' as const : 'login' as const)
const destination = computed(() => safeAuthRedirect(route.query.redirect))
const email = ref(''), code = ref(''), error = ref(''), feedback = ref('')
const loading = ref(true), sending = ref(false), submitting = ref(false), remaining = ref(0)
const emailInput = ref<HTMLInputElement | null>(null)
let deadline = 0
let timer: ReturnType<typeof setInterval> | undefined

function cooldown(seconds: number) { deadline = Date.now() + seconds * 1000; remaining.value = seconds }
function failure(cause: unknown) {
  error.value = cause instanceof Error ? cause.message : '网络连接失败，请稍后重试。'
  if (cause instanceof AuthError && cause.retryAfter) cooldown(cause.retryAfter)
}
async function initialize() {
  loading.value = true; error.value = ''
  try {
    await loadAuthSession(true)
    if (authState.user) await router.replace(destination.value)
    else if (!authState.enabled) error.value = '账号功能未启用，请联系管理员。'
  } catch (cause) { failure(cause) }
  finally { loading.value = false }
}
async function sendCode() {
  if (!emailInput.value?.reportValidity() || sending.value || remaining.value > 0) return
  sending.value = true; error.value = ''; feedback.value = ''
  try {
    const result = await sendEmailCode(email.value.trim(), purpose.value)
    cooldown(result.retry_after)
    feedback.value = `验证码邮件已发送，请在 ${Math.floor(result.expires_in / 60)} 分钟内填写。`
  } catch (cause) { failure(cause) }
  finally { sending.value = false }
}
async function submit() {
  if (submitting.value || sending.value) return
  submitting.value = true; error.value = ''
  try {
    await signInWithEmail(email.value.trim(), code.value, purpose.value)
    await router.replace(destination.value)
  } catch (cause) { failure(cause) }
  finally { submitting.value = false }
}
watch(purpose, () => { code.value = ''; error.value = ''; feedback.value = '' })
watch(email, () => { code.value = ''; feedback.value = ''; error.value = ''; deadline = 0; remaining.value = 0 })
onMounted(() => {
  void initialize()
  timer = setInterval(() => { remaining.value = Math.max(0, Math.ceil((deadline - Date.now()) / 1000)) }, 1000)
})
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<template>
  <main class="auth-page" :data-page="register ? 'register' : 'login'" aria-labelledby="auth-heading">
    <header class="auth-page__masthead">
      <RouterLink to="/" class="auth-page__brand"><AppIcon name="layers" />ShockPath</RouterLink>
      <RouterLink to="/" class="auth-page__back">返回开始页<AppIcon name="arrow" /></RouterLink>
    </header>
    <div class="auth-page__layout">
      <section class="auth-page__story" aria-label="实验平台介绍">
        <p>CFD 数值实验与可视分析</p>
        <h2>探索流动之境，<br />从这里开始。</h2>
        <p class="auth-page__promise">让数值耗散可调、可辨、可追溯。</p>
        <RouterLink to="/research">了解论文与求解器优势<AppIcon name="arrow" /></RouterLink>
      </section>

      <section class="auth-page__form-panel">
        <nav class="auth-page__tabs" aria-label="账号入口">
          <RouterLink :to="{ name: 'login', query: route.query }" :aria-current="!register ? 'page' : undefined">登录</RouterLink>
          <RouterLink :to="{ name: 'register', query: route.query }" :aria-current="register ? 'page' : undefined">注册</RouterLink>
        </nav>
        <h1 id="auth-heading">{{ register ? '创建你的 ShockPath 账号' : '登录 ShockPath' }}</h1>
        <p class="auth-page__intro">{{ register ? '用邮箱注册，验证成功后即可开始实验。' : '使用邮箱验证码登录，继续你的数值实验。' }}</p>
        <p v-if="loading" class="auth-page__status" role="status">正在连接登录服务…</p>
        <form @submit.prevent="submit" :aria-busy="sending || submitting">
          <label for="auth-email">邮箱账号</label>
          <input id="auth-email" ref="emailInput" v-model="email" type="email" name="email" autocomplete="email" placeholder="请输入你的邮箱地址" required maxlength="254" :disabled="loading || sending || submitting" />
          <label for="auth-code">邮箱验证码</label>
          <div class="auth-page__code-row">
            <input id="auth-code" v-model="code" type="text" name="code" inputmode="numeric" autocomplete="one-time-code" placeholder="6 位验证码" pattern="[0-9]{6}" maxlength="6" required :disabled="loading || submitting" aria-describedby="auth-code-help" />
            <button type="button" class="auth-page__send" :disabled="loading || sending || submitting || remaining > 0 || !email.trim() || !authState.enabled" @click="sendCode">{{ sending ? '发送中…' : remaining > 0 ? `${remaining} 秒后重发` : '获取验证码' }}</button>
          </div>
          <p id="auth-code-help" class="auth-page__hint">验证码会发送到你的邮箱，10 分钟内有效。</p>
          <p v-if="feedback" class="auth-page__feedback" role="status">{{ feedback }}</p>
          <p v-if="error" class="auth-page__error" role="alert">{{ error }}<button v-if="!authState.loaded" type="button" @click="initialize">重新连接</button></p>
          <button type="submit" class="auth-page__submit" :disabled="loading || sending || submitting || !authState.enabled">{{ submitting ? '正在验证…' : register ? '注册并开始实验' : '登录并开始实验' }}<AppIcon name="arrow" /></button>
        </form>
        <p class="auth-page__switch">{{ register ? '已有账号？' : '还没有账号？' }}<RouterLink :to="{ name: register ? 'login' : 'register', query: route.query }">{{ register ? '去登录' : '立即注册' }}</RouterLink></p>
      </section>
    </div>
  </main>
</template>

<style scoped>
#app main.auth-page { max-width: none; min-height: 100svh; padding: 32px clamp(20px, 5vw, 80px); background: #edf3fb url('/images/entry-atmosphere.webp') center / cover no-repeat; }
.auth-page__masthead { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.auth-page__brand { display: inline-flex; align-items: center; gap: 10px; color: #315ecb; font-size: 24px; font-weight: 650; text-decoration: none; letter-spacing: -.7px; }
.auth-page__brand .sp-icon { width: 28px; height: 28px; }
.auth-page__back { display: inline-flex; align-items: center; gap: 8px; min-height: 44px; color: #536780; font-size: 13px; text-decoration: none; }
.auth-page__back .sp-icon { transform: rotate(180deg); width: 16px; }
.auth-page__layout { width: min(100%, 1060px); margin: 64px auto; display: grid; grid-template-columns: 1fr 460px; gap: clamp(32px, 6vw, 96px); align-items: center; }
.auth-page__story > p:first-child { font-size: 12px; letter-spacing: 2px; color: #536780; }
.auth-page__story h2 { font-size: clamp(30px, 3.6vw, 48px); line-height: 1.5; color: #243955; margin: 24px 0; }
.auth-page__promise { color: #315ecb; font-size: 17px; }
.auth-page__story > a { display: inline-flex; align-items: center; gap: 10px; min-height: 44px; font-size: 13px; margin-top: 32px; }
.auth-page__form-panel { padding: 36px; background: #ffffffed; border: 1px solid #e3e9f3; border-radius: 24px; box-shadow: 0 16px 48px #345bc812; }
.auth-page__tabs { display: flex; gap: 28px; margin-bottom: 28px; border-bottom: 1px solid var(--sp-border); }
.auth-page__tabs a { display: flex; align-items: center; min-height: 44px; padding: 0 4px 12px; color: #697386; text-decoration: none; border-bottom: 2px solid transparent; }
.auth-page__tabs a[aria-current='page'] { color: #315ecb; border-color: #416de4; font-weight: 600; }
.auth-page__form-panel h1 { font-size: 23px; margin: 0 0 12px; }
.auth-page__intro { margin: 0 0 28px; color: #697386; font-size: 13px; }
.auth-page label { display: block; margin: 20px 0 8px; font-size: 14px; color: #2c4668; }
.auth-page input { min-height: 50px; width: 100%; min-width: 0; border: 1px solid #ccd5e3; border-radius: 12px; padding: 12px 14px; font-size: 14px; background: white; color: var(--sp-text); }
.auth-page input::placeholder { color: #7c8798; }
.auth-page__code-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 10px; }
.auth-page__send { min-height: 50px; min-width: 120px; padding: 10px 12px; border: 1px solid #b7c8e9; border-radius: 12px; background: #f3f6ff; color: #315ecb; font-size: 13px; }
.auth-page__send:hover:enabled { background: #e9efff; border-color: #416de4; }
.auth-page__hint { color: #697386; font-size: 12px; margin: 12px 0 0; }
.auth-page__feedback, .auth-page__error, .auth-page__status { margin: 16px 0 0; font-size: 13px; line-height: 1.8; }
.auth-page__feedback { color: #34745a; }
.auth-page__error { color: #923e47; background: #fff8f8; padding: 12px; border-radius: 10px; }
.auth-page__error button { background: none; border: 0; text-decoration: underline; color: #315ecb; min-height: 44px; }
.auth-page__submit { margin-top: 28px; display: inline-flex; justify-content: center; align-items: center; gap: 12px; width: 100%; min-height: 52px; border: 0; border-radius: 999px; background: var(--sp-primary); color: white; font-size: 15px; }
.auth-page__submit:hover:enabled { background: var(--sp-primary-hover); }
.auth-page button:disabled, .auth-page input:disabled { opacity: .6; }
.auth-page__switch { color: #697386; font-size: 13px; margin: 24px 0 0; text-align: center; }.auth-page__switch a { margin-left: 8px; }
@media (max-width: 850px) { .auth-page__layout { max-width: 460px; grid-template-columns: 1fr; margin: 36px auto; }.auth-page__story { display: none; } }
@media (max-width: 600px) { #app main.auth-page { padding: 20px 16px; }.auth-page__brand { font-size: 21px; }.auth-page__form-panel { padding: 28px 22px; border-radius: 20px; }.auth-page__form-panel h1 { font-size: 21px; }.auth-page__send { min-width: 110px; }.auth-page__layout { margin-top: 28px; } }
</style>
