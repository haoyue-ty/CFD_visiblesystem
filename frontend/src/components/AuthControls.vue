<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { authState, logout } from '../data/auth'

const router = useRouter()
const busy = ref(false)
const error = ref('')
const user = computed(() => authState.user)
async function signOut() {
  busy.value = true; error.value = ''
  try { await logout(); await router.replace('/') }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '退出失败，请重试。' }
  finally { busy.value = false }
}
</script>
<template>
  <div class="account-controls">
    <template v-if="user">
      <span class="account-controls__email" :title="user.email" data-testid="account-email">{{ user.email }}</span>
      <button type="button" class="account-controls__link" :disabled="busy" @click="signOut">{{ busy ? '退出中…' : '退出登录' }}</button>
    </template>
    <template v-else>
      <RouterLink to="/login" class="account-controls__link" data-testid="entry-login">登录</RouterLink>
      <RouterLink to="/register" class="account-controls__register" data-testid="entry-register">注册</RouterLink>
    </template>
    <p v-if="error" class="account-controls__error" role="alert">{{ error }}</p>
  </div>
</template>
<style scoped>
.account-controls { position: relative; display: flex; align-items: center; gap: 16px; flex-shrink: 0; }
.account-controls__link, .account-controls__register { display: inline-flex; align-items: center; justify-content: center; min-height: 44px; padding: 8px 12px; font-size: 14px; text-decoration: none; border: 0; background: transparent; color: #315ecb; border-radius: 999px; }
.account-controls__link:hover { background: #ffffffa6; }
.account-controls__register { border: 1px solid #a7bbdb; padding-inline: 22px; background: #ffffff9c; }
.account-controls__register:hover { background: white; border-color: var(--sp-primary); }
.account-controls__email { max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #536780; font-size: 12px; }
.account-controls__error { position: absolute; right: 0; top: 100%; min-width: 240px; margin: 6px 0; padding: 12px; color: #923e47; background: #fff8f8; border: 1px solid #e7c6c9; border-radius: 10px; font-size: 12px; z-index: 5; }
@media (max-width: 600px) { .account-controls { gap: 8px; }.account-controls__email { max-width: 100px; }.account-controls__link, .account-controls__register { font-size: 13px; padding-inline: 12px; } }
</style>
