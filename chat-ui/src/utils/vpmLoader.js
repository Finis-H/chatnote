// src/utils/vpmLoader.js
import * as Vue from 'vue';
import { loadModule } from 'vue3-sfc-loader/dist/vue3-sfc-loader.esm.js';
import * as NeuroLink from '../composables/useNeuroLink';

// 这里的 options 是给编译器定义的“生存环境”
const options = {
  moduleCache: { vue: Vue, 'vault:useNeuroLink': NeuroLink},
  async getFile(url) {
    const res = await fetch(url);
    if (!res.ok) throw Object.assign(new Error(res.statusText + ' ' + url), { res });
    return {
      getContentData: asBinary => asBinary ? res.arrayBuffer() : res.text(),
    }
  },
  addStyle(textContent) {
    const style = Object.assign(document.createElement('style'), { textContent });
    const ref = document.head.getElementsByTagName('style')[0] || null;
    document.head.insertBefore(style, ref);
  },
};

/** VPM 动态加载器：从后端的静态通道拉取并编译 Vue 文件 */
export function loadVpmComponent(pluginId, componentName) {
  const timestamp = Date.now(); // 加时间戳避免缓存

  return Vue.defineAsyncComponent(() =>
    loadModule(`http://127.0.0.1:8000/plugins/${pluginId}/ui/${componentName}.vue?t=${timestamp}`, options)
  );
}