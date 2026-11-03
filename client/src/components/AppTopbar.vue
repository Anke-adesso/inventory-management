<template>
  <header class="topbar">
    <button
      v-if="showMenuButton"
      ref="menuBtn"
      type="button"
      class="topbar__menu"
      :aria-label="t('nav.openNavigation')"
      :aria-expanded="String(menuOpen)"
      @click="$emit('open-menu')"
    >
      <Menu :size="20" aria-hidden="true" />
    </button>

    <h1 class="topbar__title">{{ title }}</h1>

    <div class="topbar__right"><slot /></div>
  </header>
</template>

<script>
import { ref } from 'vue'
import { Menu } from 'lucide-vue-next'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'AppTopbar',
  components: { Menu },
  props: {
    title: { type: String, default: '' },
    showMenuButton: { type: Boolean, default: false },
    menuOpen: { type: Boolean, default: false }
  },
  emits: ['open-menu'],
  setup(props, { expose }) {
    const { t } = useI18n()
    const menuBtn = ref(null)
    expose({ focusMenuButton: () => menuBtn.value?.focus() })
    return { t, menuBtn }
  }
}
</script>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  height: var(--shell-topbar-h);
  padding: 0 var(--shell-content-pad);
  background: var(--color-nav-bg);
  border-bottom: 1px solid var(--color-border-2);
  flex-shrink: 0;
}
.topbar__title {
  flex: 1;
  min-width: 0;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.topbar__right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.topbar__menu {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  margin-left: calc(var(--space-2) * -1);
  flex-shrink: 0;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-mid);
  cursor: pointer;
}
.topbar__menu:hover { background: var(--color-surface-2); color: var(--color-text); }

/* Narrow screens: keep the page title visible by shrinking the right-hand controls to
   icon + avatar. Labels stay in the DOM (visually hidden) so the buttons keep their names. */
@media (max-width: 767px) {
  .topbar { gap: var(--space-2); }
  .topbar__right { gap: var(--space-1); flex-shrink: 0; }
  .topbar__right :deep(.language-label),
  .topbar__right :deep(.profile-name) {
    position: absolute;
    width: 1px;
    height: 1px;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
  }
}
</style>
