// src/utils/vpmLoader.js
import * as Vue from 'vue';
import { markRaw } from 'vue';
import { loadModule } from 'vue3-sfc-loader/dist/vue3-sfc-loader.esm.js';

let registeredContext = null;
const FIRST_PARTY_PLUGIN_IDS = new Set(['music_agent']);
const PLUGIN_INFO_WAIT_MS = 800;
const PLUGIN_INFO_POLL_MS = 50;

/**
 * VPM 引擎全局上下文注册中心
 * 由主程序在初始化时单向注入，彻底切断循环依赖！
 */
export function registerVpmContext(context) {
  registeredContext = context;
}
/** * VPM 动态加载器：恢复经典的 2 个参数签名！完美兼容 PluginCenter！
 */
export function loadVpmComponent(pluginId, componentName) {
  return markRaw(Vue.defineAsyncComponent(async () => {
    try {
      if (!registeredContext) throw new Error("VPM 核心上下文未注册！");
      const apiBase = registeredContext.SystemConfig.API_BASE;
      const pluginInfo = await resolvePluginInfo(pluginId);
      const isFirstParty = FIRST_PARTY_PLUGIN_IDS.has(pluginId) || pluginInfo.security?.trust === 'first_party';
      const pluginContext = isFirstParty ? registeredContext : createThirdPartyContext(pluginId, pluginInfo);
      const options = {
        moduleCache: { vue: Vue, 'vault:useNeuroLink': pluginContext },
        async getFile(url) {
          const res = await fetch(url);
          if (!res.ok) throw Object.assign(new Error(res.statusText + ' ' + url), { res });
          return { getContentData: asBinary => asBinary ? res.arrayBuffer() : res.text() }
        },
        addStyle(textContent) {
          const style = Object.assign(document.createElement('style'), { textContent });
          const ref = document.head.getElementsByTagName('style')[0] || null;
          document.head.insertBefore(style, ref);
        },
      };
      const timestamp = Date.now();
      const targetUrl = `${apiBase}/plugins/${pluginId}/ui/${componentName}.vue?t=${timestamp}`;
      return await loadModule(targetUrl, options);
    } catch (err) {
      console.error(`🚨 [VPM 引擎] 加载组件 ${componentName} 失败:`, err);
      throw err;
    }
  }));
}

async function resolvePluginInfo(pluginId) {
  const current = findPluginInfo(pluginId);
  if (current) return current;

  registeredContext.sendWsCommand?.({ type: "fetch_plugins" });
  const deadline = Date.now() + PLUGIN_INFO_WAIT_MS;
  while (Date.now() < deadline) {
    await sleep(PLUGIN_INFO_POLL_MS);
    const refreshed = findPluginInfo(pluginId);
    if (refreshed) return refreshed;
  }
  return {};
}

function findPluginInfo(pluginId) {
  return (registeredContext.pluginsList?.value || []).find(item => item.plugin_id === pluginId);
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function createThirdPartyContext(pluginId, pluginInfo) {
  const apiBase = registeredContext.SystemConfig.API_BASE;
  const scopedToken = pluginInfo.plugin_ui_token || '';
  const safeSystemConfig = Object.freeze({
    API_BASE: apiBase,
    WS_BASE: registeredContext.SystemConfig.WS_BASE,
    SERVER_PORT: registeredContext.SystemConfig.SERVER_PORT
  });

  async function pluginFetch(path, options = {}) {
    const normalizedPath = String(path || '');
    const expectedPrefix = `/api/plugins/${pluginId}/`;
    if (!normalizedPath.startsWith(expectedPrefix)) {
      throw new Error(`Third-party plugin ${pluginId} can only call ${expectedPrefix}...`);
    }
    const headers = new Headers(options.headers || {});
    headers.set('X-Vault-Plugin-Token', scopedToken);
    return fetch(`${apiBase}${normalizedPath}`, { ...options, headers });
  }

  return Object.freeze({
    plugin_id: pluginId,
    SystemConfig: safeSystemConfig,
    showToast: registeredContext.showToast,
    pluginFetch
  });
}
