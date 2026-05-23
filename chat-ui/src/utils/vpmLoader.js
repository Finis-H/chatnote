// src/utils/vpmLoader.js
import * as Vue from 'vue';
import { markRaw } from 'vue';
import { loadModule } from 'vue3-sfc-loader/dist/vue3-sfc-loader.esm.js';

let registeredContext = null;

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
      const options = {
        moduleCache: { vue: Vue, 'vault:useNeuroLink': registeredContext },
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