import { createApp } from "vue";
import App from "./App.vue";
import { initSystemEnv } from "./composables/useNeuroLink";

async function bootstrap() {
    // 1. 强制阻塞：必须等 Tauri 和 Rust 把动态端口和 Token 拿回来！
    await initSystemEnv();
    // 2. 环境寻址完毕后，再挂载 UI 界面！
    createApp(App).mount("#app");
}

bootstrap();
