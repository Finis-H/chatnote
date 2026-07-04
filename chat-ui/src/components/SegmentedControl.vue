<script setup>
defineProps({
  options: { type: Array, required: true },
  modelValue: { type: [String, Number, Boolean], default: null }
});

const emit = defineEmits(['update:modelValue']);

function selectOption(option) {
  if (option.disabled) return;
  emit('update:modelValue', option.value);
}

function getOptionKey(option) {
  return option.value ?? option.label;
}

function getOptionBadge(option) {
  if (option.count !== undefined && option.count !== null) return option.count;
  return option.badge;
}
</script>

<template>
  <div class="segmented-control" role="group">
    <button
      v-for="option in options"
      :key="getOptionKey(option)"
      type="button"
      class="segmented-control__item"
      :class="{ 'is-active': option.value === modelValue }"
      :disabled="option.disabled"
      :aria-pressed="option.value === modelValue"
      @click="selectOption(option)"
    >
      <span>{{ option.label }}</span>
      <span v-if="getOptionBadge(option) !== undefined && getOptionBadge(option) !== null" class="segmented-control__badge">
        {{ getOptionBadge(option) }}
      </span>
    </button>
  </div>
</template>

<style scoped>
.segmented-control {
  display: flex;
  background: var(--bg-hover);
  border-radius: var(--radius-pill);
  padding: var(--space-2xs);
}

.segmented-control__item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  background: transparent;
  border: none;
  color: var(--text-muted);
  padding: 6px 16px;
  border-radius: var(--radius-pill);
  cursor: pointer;
  font-size: 12px;
  transition: background var(--duration-base) var(--ease-standard), color var(--duration-base) var(--ease-standard), opacity var(--duration-base) var(--ease-standard);
  font-family: var(--font-mono);
}

.segmented-control__item.is-active {
  background: var(--accent);
  color: var(--text-inverse);
  font-weight: bold;
}

.segmented-control__item:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.segmented-control__badge {
  min-width: 18px;
  padding: 1px var(--space-xs);
  border-radius: var(--radius-pill);
  background: var(--bg-hover-strong);
  color: inherit;
  text-align: center;
  line-height: 1.35;
}
</style>
