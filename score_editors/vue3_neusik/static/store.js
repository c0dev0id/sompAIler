import { reactive } from 'vue';

export const store = reactive({
    scoreModel: null,
    rawScoreText: null,
    focusPath: [],
    credentials: null,
    synthesisStatus: null,
    isDirty: false,
    errorMessage: '',

    setFocus(path) {
        this.focusPath = path;
    },

    pushFocus(node) {
        const idx = this.focusPath.indexOf(node);
        if (idx !== -1) {
            this.focusPath = this.focusPath.slice(0, idx + 1);
        } else {
            this.focusPath = [...this.focusPath, node];
        }
    },

    markDirty() {
        this.isDirty = true;
    },
});
