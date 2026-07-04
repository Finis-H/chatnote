<script setup>
defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  meta: { type: String, default: '' },
  danger: { type: Boolean, default: false },
  selected: { type: Boolean, default: false },
  active: { type: Boolean, default: false },
  interactive: { type: Boolean, default: false }
});
</script>

<template>
  <article
    class="vault-card"
    :class="{
      'vault-card--danger': danger,
      'vault-card--selected': selected,
      'vault-card--active': active,
      'vault-card--interactive': interactive
    }"
  >
    <header v-if="title || subtitle || meta || $slots.status" class="vault-card__header">
      <div class="vault-card__heading">
        <div v-if="meta" class="vault-card__meta">{{ meta }}</div>
        <h3 v-if="title" class="vault-card__title">{{ title }}</h3>
        <p v-if="subtitle" class="vault-card__subtitle">{{ subtitle }}</p>
      </div>
      <div v-if="$slots.status" class="vault-card__status">
        <slot name="status" />
      </div>
    </header>

    <div v-if="$slots.default" class="vault-card__body">
      <slot />
    </div>

    <footer v-if="$slots.actions" class="vault-card__actions">
      <slot name="actions" />
    </footer>
  </article>
</template>

<style scoped>
.vault-card {
  background: var(--bg-panel);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-xl);
  display: flex;
  flex-direction: column;
  min-width: 0;
  transition: transform var(--duration-base) var(--ease-standard), border-color var(--duration-base) var(--ease-standard), background var(--duration-base) var(--ease-standard), box-shadow var(--duration-base) var(--ease-standard);
}

.vault-card--interactive {
  cursor: pointer;
}

.vault-card--interactive:hover,
.vault-card--active,
.vault-card--selected {
  border-color: var(--accent-border);
  background: var(--bg-panel-raised);
  box-shadow: var(--shadow-panel);
}

.vault-card--interactive:hover {
  transform: translateY(-2px);
}

.vault-card--danger {
  border-color: var(--danger-border);
}

.vault-card--danger.vault-card--interactive:hover,
.vault-card--danger.vault-card--active,
.vault-card--danger.vault-card--selected {
  border-color: var(--danger-border);
  background: var(--bg-danger-soft);
}

.vault-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-lg);
}

.vault-card__heading {
  min-width: 0;
}

.vault-card__meta {
  color: var(--text-disabled);
  font-family: var(--font-mono);
  font-size: 10px;
  line-height: 1.5;
  margin-bottom: var(--space-xs);
}

.vault-card__title {
  color: var(--text-primary);
  font-size: 16px;
  line-height: 1.35;
  margin: 0;
  overflow-wrap: anywhere;
}

.vault-card--interactive:hover .vault-card__title {
  color: var(--accent-strong);
}

.vault-card__subtitle {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.55;
  margin: var(--space-sm) 0 0;
}

.vault-card__status {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.vault-card__body {
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.6;
  min-width: 0;
}

.vault-card__header + .vault-card__body,
.vault-card__body + .vault-card__actions,
.vault-card__header + .vault-card__actions {
  margin-top: var(--space-lg);
}

.vault-card__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-lg);
  border-top: 1px dashed var(--border-strong);
  padding-top: var(--space-lg);
}

@media (max-width: 640px) {
  .vault-card__header,
  .vault-card__actions {
    gap: var(--space-md);
  }
}
</style>
