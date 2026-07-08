import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';

export function useScrollAffordance(containerRef, options = {}) {
  const threshold = options.threshold ?? 32;
  const canScrollUp = ref(false);
  const canScrollDown = ref(false);
  const isNearBottom = ref(true);
  let frameId = 0;
  let resizeObserver = null;
  let boundContainer = null;

  function readState() {
    const container = containerRef.value;
    if (!container) {
      canScrollUp.value = false;
      canScrollDown.value = false;
      isNearBottom.value = true;
      return;
    }

    const bottomGap = container.scrollHeight - container.clientHeight - container.scrollTop;
    canScrollUp.value = container.scrollTop > threshold;
    canScrollDown.value = bottomGap > threshold;
    isNearBottom.value = bottomGap <= threshold;
  }

  function scheduleStateRead() {
    if (frameId) return;
    frameId = requestAnimationFrame(() => {
      frameId = 0;
      readState();
    });
  }

  function unbindContainer() {
    if (boundContainer) {
      boundContainer.removeEventListener('scroll', scheduleStateRead);
    }
    if (resizeObserver) {
      resizeObserver.disconnect();
      resizeObserver = null;
    }
    boundContainer = null;
  }

  function bindContainer(container) {
    if (boundContainer === container) return;
    unbindContainer();
    boundContainer = container;
    if (!boundContainer) {
      readState();
      return;
    }

    boundContainer.addEventListener('scroll', scheduleStateRead, { passive: true });
    if (window.ResizeObserver) {
      resizeObserver = new ResizeObserver(scheduleStateRead);
      resizeObserver.observe(boundContainer);
    }
    scheduleStateRead();
  }

  function scrollToBottom(behavior = 'smooth') {
    const container = containerRef.value;
    if (!container) return;
    container.scrollTo({ top: container.scrollHeight, behavior });
    scheduleStateRead();
  }

  function scrollToTop(behavior = 'smooth') {
    const container = containerRef.value;
    if (!container) return;
    container.scrollTo({ top: 0, behavior });
    scheduleStateRead();
  }

  function refreshScrollState() {
    scheduleStateRead();
  }

  async function refreshScrollStateAfterRender() {
    await nextTick();
    scheduleStateRead();
  }

  onMounted(() => bindContainer(containerRef.value));
  watch(containerRef, bindContainer);
  onBeforeUnmount(() => {
    if (frameId) cancelAnimationFrame(frameId);
    unbindContainer();
  });

  return {
    canScrollUp,
    canScrollDown,
    isNearBottom,
    scrollToBottom,
    scrollToTop,
    refreshScrollState,
    refreshScrollStateAfterRender
  };
}
