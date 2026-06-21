import { h, ref, onMounted } from 'vue';
import { PaneCP } from './PaneCP.js';
import { PaneFO } from './PaneFO.js';
import { PaneSubObjects } from './PaneSubObjects.js';
import { ImportDialog } from './ImportDialog.js';

const PANES = [
    { id: 'cp',   label: 'Position' },
    { id: 'fo',   label: 'Object' },
    { id: 'sub',  label: 'Sub-objects' },
];

export const AppShell = {
    props: ['store', 'importOnLoad'],
    setup(props) {
        const activePane = ref('cp');
        const showImport = ref(false);

        function openImport() {
            if (!props.store.isDirty) showImport.value = true;
        }

        onMounted(() => {
            if (props.importOnLoad && !props.store.isDirty) showImport.value = true;
        });

        return () => {
            const store = props.store;

            return h('div', { class: 'se-shell' }, [
                // Pane area
                h('div', { class: 'se-pane-area' }, [
                    h('div', { class: ['se-pane', activePane.value === 'cp' ? 'active' : null] },
                        h(PaneCP, { store, onImportClick: openImport })),
                    h('div', { class: ['se-pane', activePane.value === 'fo' ? 'active' : null] },
                        h(PaneFO, { store })),
                    h('div', { class: ['se-pane', activePane.value === 'sub' ? 'active' : null] },
                        h(PaneSubObjects, { store })),
                ]),

                // Handle bar (tab switcher at bottom)
                h('div', { class: 'se-handle-bar' }, PANES.map(p =>
                    h('button', {
                        key: p.id,
                        class: ['se-handle', activePane.value === p.id ? 'active' : null],
                        onClick: () => { activePane.value = p.id; },
                    }, p.label)
                )),

                // Error banner
                store.errorMessage
                    ? h('div', { class: 'se-error', style: 'margin:0' }, store.errorMessage)
                    : null,

                // Import dialog
                showImport.value
                    ? h(ImportDialog, { store, onClose: () => { showImport.value = false; } })
                    : null,
            ]);
        };
    },
};
