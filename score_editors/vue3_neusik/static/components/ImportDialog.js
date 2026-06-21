import { h, ref } from 'vue';
import { fetchAstLog } from '../api.js';
import { parseAstLog, buildModel } from '../ast-parser.js';

export const ImportDialog = {
    props: ['store'],
    emits: ['close'],
    setup(props, { emit }) {
        const username = ref('');
        const password = ref('');
        const error = ref('');
        const loading = ref(false);

        async function doImport() {
            error.value = '';
            loading.value = true;
            try {
                const creds = { username: username.value, password: password.value };
                const text = await fetchAstLog(creds);
                const rawTree = parseAstLog(text);
                props.store.scoreModel = buildModel(rawTree);
                props.store.credentials = creds;
                emit('close');
            } catch (e) {
                error.value = e.message;
            } finally {
                loading.value = false;
            }
        }

        function onKey(e) {
            if (e.key === 'Escape') emit('close');
            if (e.key === 'Enter') doImport();
        }

        return () => h('div', null, [
            h('div', { class: 'se-overlay', onClick: () => emit('close') }),
            h('div', { class: 'se-import-dialog', onKeydown: onKey, tabindex: -1 }, [
                h('h3', null, 'Import from server'),
                h('label', null, 'Username'),
                h('input', {
                    type: 'text',
                    value: username.value,
                    onInput: e => { username.value = e.target.value; },
                    autocomplete: 'username',
                }),
                h('label', null, 'Password'),
                h('input', {
                    type: 'password',
                    value: password.value,
                    onInput: e => { password.value = e.target.value; },
                    autocomplete: 'current-password',
                }),
                error.value ? h('div', { class: 'se-error' }, error.value) : null,
                h('div', { class: 'se-dialog-buttons' }, [
                    h('button', { class: 'se-btn', onClick: () => emit('close') }, 'Cancel'),
                    h('button', {
                        class: 'se-btn se-btn-primary',
                        onClick: doImport,
                        disabled: loading.value,
                    }, loading.value ? 'Loading…' : 'Import'),
                ]),
            ]),
        ]);
    },
};
