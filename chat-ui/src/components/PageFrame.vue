<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' }
});
</script>

<template>
  <section class="page-frame">
    <header class="page-frame__header" :class="{ 'page-frame__header--with-subtitle': subtitle }">
      <div class="page-frame__heading">
        <h2 class="page-frame__title">{{ title }}</h2>
        <p v-if="subtitle" class="page-frame__subtitle">{{ subtitle }}</p>
      </div>
      <div v-if="$slots.actions" class="page-frame__actions">
        <slot name="actions" />
      </div>
    </header>

    <slot />
  </section>
</template>

<style scoped>
.page-frame {
  padding: var(--space-3xl);
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
  height: 100%;
  overflow-y: auto;
}

.page-frame::-webkit-scrollbar {
  width: 6px;
}

.page-frame::-webkit-scrollbar-thumb {
  background: var(--border-strong);
  border-radius: var(--radius-xs);
}

.page-frame__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-lg);
}

.page-frame__header--with-subtitle {
  border-bottom: 1px solid var(--border-strong);
  padding-bottom: var(--space-lg);
}

.page-frame__heading {
  min-width: 0;
}

.page-frame__title {
  color: var(--text-primary);
  font-size: 18px;
  font-weight: normal;
  margin: 0;
}

.page-frame__subtitle {
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.6;
  margin: var(--space-xs) 0 0;
}

.page-frame__actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-shrink: 0;
}

@media (max-width: 640px) {
  .page-frame__header {
    flex-direction: column;
  }
}
</style>
