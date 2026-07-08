<script setup>
import { computed } from 'vue';
import { ArrowDown, ArrowUp } from '@element-plus/icons-vue';

const props = defineProps({
  direction: { type: String, default: 'bottom' },
  active: { type: Boolean, default: false },
  label: { type: String, default: '' }
});

defineEmits(['click']);

const icon = computed(() => props.direction === 'top' ? ArrowUp : ArrowDown);
const defaultLabel = computed(() => props.direction === 'top' ? 'Scroll to top' : 'Scroll to bottom');
const buttonLabel = computed(() => props.label || defaultLabel.value);
</script>

<template>
  <button
    type="button"
    class="scroll-edge-button"
    :class="{ 'scroll-edge-button--active': active }"
    :title="buttonLabel"
    :aria-label="buttonLabel"
    @click="$emit('click')"
  >
    <component :is="icon" aria-hidden="true" />
    <span v-if="active" class="scroll-edge-button__dot" aria-hidden="true"></span>
  </button>
</template>

<style scoped>
.scroll-edge-button {
  position: absolute;
  right: var(--space-2xl);
  bottom: var(--space-xl);
  z-index: 6;
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  background: var(--bg-panel-raised);
  color: var(--text-muted);
  box-shadow: var(--shadow-panel);
  cursor: pointer;
  transition: background var(--duration-base) var(--ease-standard),
    border-color var(--duration-base) var(--ease-standard),
    color var(--duration-base) var(--ease-standard),
    box-shadow var(--duration-base) var(--ease-standard),
    transform var(--duration-fast) var(--ease-standard);
}

.scroll-edge-button:hover,
.scroll-edge-button:focus-visible {
  border-color: var(--accent-border);
  background: var(--accent-soft);
  color: var(--accent-strong);
  box-shadow: var(--shadow-glow-soft);
}

.scroll-edge-button:active {
  transform: translateY(1px);
}

.scroll-edge-button svg {
  width: 17px;
  height: 17px;
}

.scroll-edge-button__dot {
  position: absolute;
  top: 5px;
  right: 5px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 3px rgba(69, 224, 200, 0.12);
}

@media (max-width: 720px) {
  .scroll-edge-button {
    right: var(--space-lg);
    bottom: var(--space-lg);
  }
}
</style>
