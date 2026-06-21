import { createApp, h } from 'vue';
import { store } from './store.js';
import { AppShell } from './components/AppShell.js';

const root = document.getElementById('score-editor-app');
const importOnLoad = root?.dataset.importOnLoad === 'true';

createApp({
    setup() {
        return () => h(AppShell, { store, importOnLoad });
    },
}).mount('#score-editor-app');
