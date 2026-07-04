<script setup>
defineProps({
  show: { type: Boolean, default: false },
  title: { type: String, required: true },
  objectName: { type: String, required: true },
  impact: { type: String, required: true },
  irreversible: { type: Boolean, default: true },
  riskTip: { type: String, default: '' },
  confirmText: { type: String, default: '确认' },
  cancelText: { type: String, default: '取消' }
});

defineEmits(['cancel', 'confirm']);
</script>

<template>
  <div v-if="show" class="danger-dialog-overlay" role="presentation" @click="$emit('cancel')">
    <section
      class="danger-dialog"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="`${title}-title`"
      @click.stop
    >
      <div class="modal-icon" aria-hidden="true">!</div>
      <h3 :id="`${title}-title`" class="modal-title">{{ title }}</h3>

      <dl class="danger-summary">
        <div class="summary-row">
          <dt>操作对象</dt>
          <dd class="highlight-text">{{ objectName }}</dd>
        </div>
        <div class="summary-row">
          <dt>影响范围</dt>
          <dd>{{ impact }}</dd>
        </div>
        <div class="summary-row">
          <dt>能否撤销</dt>
          <dd :class="{ 'warning-text': irreversible }">{{ irreversible ? '不可撤销' : '可撤销' }}</dd>
        </div>
      </dl>

      <p v-if="riskTip" class="risk-tip">{{ riskTip }}</p>

      <div class="modal-actions">
        <button type="button" class="btn-cancel" @click="$emit('cancel')">{{ cancelText }}</button>
        <button type="button" class="btn-confirm" @click="$emit('confirm')">{{ confirmText }}</button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.danger-dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: var(--bg-overlay);
  backdrop-filter: blur(5px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 9999;
  animation: fadeIn var(--duration-base) ease-out;
}

.danger-dialog {
  background: var(--bg-panel);
  border: 1px solid var(--border-strong);
  border-top: 2px solid var(--danger);
  padding: var(--space-3xl);
  border-radius: var(--radius-md);
  width: min(440px, calc(100vw - 32px));
  text-align: left;
  box-shadow: var(--shadow-popover);
  animation: slideUp var(--duration-slow) cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.modal-icon {
  width: 34px;
  height: 34px;
  margin: 0 auto var(--space-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--danger-border);
  border-radius: var(--radius-sm);
  background: var(--bg-danger-soft);
  color: var(--danger);
  font-size: 20px;
  font-weight: 700;
}

.modal-title {
  color: var(--text-primary);
  font-size: 18px;
  margin: 0 0 var(--space-xl);
  font-weight: normal;
  letter-spacing: 1px;
  text-align: center;
}

.danger-summary {
  margin: 0;
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
}

.summary-row {
  display: grid;
  grid-template-columns: 108px 1fr;
  gap: var(--space-md);
  padding: var(--space-md) 0;
  border-top: 1px solid var(--border-subtle);
}

.summary-row:first-child {
  border-top: none;
}

.summary-row dt {
  color: var(--text-disabled);
  font-size: 12px;
}

.summary-row dd {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.highlight-text {
  color: var(--accent) !important;
}

.warning-text {
  color: var(--danger) !important;
}

.risk-tip {
  margin: var(--space-lg) 0 var(--space-2xl);
  color: var(--danger);
  font-size: 12px;
  line-height: 1.7;
}

.modal-actions {
  display: flex;
  gap: var(--space-lg);
  justify-content: center;
}

.modal-actions button {
  padding: var(--space-sm) var(--space-2xl);
  border: 1px solid transparent;
  border-radius: var(--radius-xs);
  font-family: var(--font-mono);
  font-size: 13px;
  cursor: pointer;
  transition: background var(--duration-base) var(--ease-standard), color var(--duration-base) var(--ease-standard), border-color var(--duration-base) var(--ease-standard), box-shadow var(--duration-base) var(--ease-standard);
}

.btn-cancel {
  background: var(--bg-hover);
  color: var(--text-secondary);
  border-color: var(--border-strong);
}

.btn-cancel:hover {
  background: var(--bg-hover-strong);
  color: var(--text-primary);
}

.btn-confirm {
  background: var(--bg-danger-soft);
  color: var(--danger);
  border-color: var(--danger-border);
}

.btn-confirm:hover {
  background: var(--danger);
  color: var(--text-inverse);
  box-shadow: var(--shadow-danger-soft);
}

@media (max-width: 520px) {
  .summary-row {
    grid-template-columns: 1fr;
    gap: var(--space-xs);
  }

  .modal-actions {
    flex-direction: column;
  }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { transform: translateY(20px) scale(0.95); opacity: 0; }
  to { transform: translateY(0) scale(1); opacity: 1; }
}
</style>
