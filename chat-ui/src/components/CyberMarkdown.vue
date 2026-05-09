<script setup>
import { computed } from 'vue';
import { marked } from 'marked';
import hljs from 'highlight.js';
import DOMPurify from 'dompurify';
import 'highlight.js/styles/atom-one-dark.css';
import { open } from '@tauri-apps/plugin-shell';

const props = defineProps({ text: { type: String, default: '' } });

marked.setOptions({
  renderer: new marked.Renderer(),
  highlight: function (code, lang) {
    const language = hljs.getLanguage(lang) ? lang : 'plaintext';
    return hljs.highlight(code, { language }).value;
  },
  langPrefix: 'hljs language-', gfm: true, breaks: true,
});

const sanitizedHtml = computed(() => {
  if (!props.text) return '';
  const rawHtml = marked.parse(props.text);
  return DOMPurify.sanitize(rawHtml, { ALLOWED_URI_REGEXP: /^(?:(?:(?:f|h)t|mn)tp(?:s)?|mailto|tel|note):/i });
});

const handleMarkdownClick = async (event) => {
  const target = event.target.closest('a');
  if (target && target.href) {
    event.preventDefault(); 
    const url = target.href;
    if (url.startsWith('http://') || url.startsWith('https://')) {
      await open(url); 
    } else {
      console.log('触发内部锚点:', url);
    }
  }
};
</script>

<template>
  <div class="article markdown-body" v-html="sanitizedHtml" @click="handleMarkdownClick"></div>
</template>