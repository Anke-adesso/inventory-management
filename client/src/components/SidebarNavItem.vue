<template>
  <RouterLink
    :to="item.to"
    class="nav-item"
    :class="{ 'is-collapsed': collapsed }"
    :active-class="item.to === '/' ? '' : 'is-active'"
    exact-active-class="is-active"
    @mouseenter="showTip"
    @mouseleave="hideTip"
    @focus="showTip"
    @blur="hideTip"
  >
    <component :is="item.icon" class="nav-item__icon" :size="18" aria-hidden="true" />
    <span class="nav-item__label" :class="{ 'sr-only': collapsed }">{{ label }}</span>
  </RouterLink>

  <Teleport to="body">
    <div
      v-if="tip"
      class="nav-tooltip"
      role="presentation"
      :style="{ top: tip.top + 'px', left: tip.left + 'px' }"
    >
      {{ label }}
    </div>
  </Teleport>
</template>

<script>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'

export default {
  name: 'SidebarNavItem',
  props: {
    item: { type: Object, required: true },
    label: { type: String, required: true },
    collapsed: { type: Boolean, default: false }
  },
  setup(props) {
    const route = useRoute()
    const tip = ref(null)

    // Tooltip is teleported and fixed-positioned: the sidebar's overflow would clip an
    // absolutely positioned one. Supplementary only; the label stays in the DOM (sr-only).
    const showTip = (e) => {
      if (!props.collapsed) return
      const r = e.currentTarget.getBoundingClientRect()
      tip.value = { top: r.top + r.height / 2, left: r.right + 8 }
    }
    const hideTip = () => { tip.value = null }

    watch(() => route.fullPath, hideTip)
    watch(() => props.collapsed, (c) => { if (!c) hideTip() })

    return { tip, showTip, hideTip }
  }
}
</script>

<style scoped>
.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
  height: 36px;
  padding: 0 var(--space-3);
  border-radius: var(--radius-sm);
  color: var(--color-text-mid);
  font-size: var(--text-sm);
  font-weight: 500;
  text-decoration: none;
  transition: background var(--dur-fast), color var(--dur-fast);
}
.nav-item:hover { background: var(--color-surface-2); color: var(--color-text); }
.nav-item.is-active { background: var(--color-accent-bg); color: var(--color-accent); font-weight: 600; }
.nav-item.is-collapsed { justify-content: center; padding: 0; }

.nav-item__icon { flex-shrink: 0; }
.nav-item__label { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* Teleported to body, so keep it self-contained. Above shell and drawer. */
.nav-tooltip {
  position: fixed;
  transform: translateY(-50%);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  background: var(--color-text);
  color: var(--color-surface);
  font-family: var(--font-sans);
  font-size: var(--text-xs);
  font-weight: 500;
  white-space: nowrap;
  pointer-events: none;
  z-index: 900;
  box-shadow: var(--shadow-md);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
