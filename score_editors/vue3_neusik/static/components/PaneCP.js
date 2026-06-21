import { h, ref } from 'vue';
import { fetchScoreText, putScoreText } from '../api.js';
import { patchScore } from '../exporter.js';
import { StatusPoller } from './StatusPoller.js';

export const PaneCP = {
    props: ['store', 'onImportClick'],
    setup(props) {
        const exporting = ref(false);
        const exportError = ref('');

        function breadcrumbLabel(node) {
            if (!node) return '?';
            if (node.type === 'score') return 'Score';
            if (node.type === 'instrument') return node.name;
            if (node.type === 'variation') return node.dependsOn ? `var(${node.dependsOn})` : 'variation';
            if (node.type === 'label_spec') return node.label ?? 'label';
            if (node.type === 'bar') return node.id;
            return node.type;
        }

        async function doExport() {
            exportError.value = '';
            exporting.value = true;
            try {
                const raw = await fetchScoreText(props.store.credentials);
                props.store.rawScoreText = raw;
                const patched = patchScore(raw, props.store.scoreModel.instruments);
                await putScoreText(patched, props.store.credentials);
                // Start polling
                props.store.synthesisStatus = { frozen: false, progress: 0 };
            } catch (e) {
                exportError.value = e.message;
            } finally {
                exporting.value = false;
            }
        }

        return () => {
            const store = props.store;
            const model = store.scoreModel;
            const fp = store.focusPath;

            return h('div', { class: 'se-pane' }, [
                // Header
                h('div', { class: 'se-cp-header' }, [
                    h('span', { class: 'se-cp-title' },
                        model ? (model.info?.title ?? 'Untitled score') : 'No score loaded'),
                    h('button', {
                        class: 'se-btn',
                        disabled: store.isDirty,
                        title: store.isDirty ? 'Save or discard edits before re-importing' : 'Import from server',
                        onClick: props.onImportClick,
                    }, 'Import'),
                    model ? h('button', {
                        class: 'se-btn se-btn-primary',
                        disabled: !store.isDirty || exporting.value,
                        onClick: doExport,
                    }, exporting.value ? 'Exporting…' : 'Export') : null,
                ]),

                // Breadcrumb
                fp.length ? h('div', { class: 'se-breadcrumb' }, [
                    h('span', { onClick: () => store.setFocus([]) }, 'Score'),
                    ...fp.map((node, i) => [
                        ' › ',
                        h('span', { onClick: () => store.setFocus(fp.slice(0, i + 1)) },
                            breadcrumbLabel(node)),
                    ]).flat(),
                ]) : null,

                // Score info
                model ? h('dl', { style: 'font-size:0.8rem;margin:0.5rem 0' }, [
                    h('dt', null, 'Instruments'),
                    h('dd', null, String(model.instruments.length)),
                    h('dt', null, 'Bars'),
                    h('dd', null, String(model.bars.length)),
                ]) : null,

                // Export error
                exportError.value ? h('div', { class: 'se-error' }, exportError.value) : null,

                // Status poller (shown after export started)
                store.synthesisStatus && !store.synthesisStatus.frozen
                    ? h(StatusPoller, { store })
                    : null,

                // Result link
                store.synthesisStatus?.frozen && !store.synthesisStatus?.error
                    ? h('a', {
                        href: '/sompyle/result.mp3',
                        style: 'display:block;margin-top:0.5rem',
                      }, 'Download result')
                    : null,
            ]);
        };
    },
};
