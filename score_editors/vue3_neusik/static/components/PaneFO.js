import { h } from 'vue';
import { ObjectExtended } from './ObjectExtended.js';
import { EnvelopeEditor } from './EnvelopeEditor.js';

function instrFields(instr) {
    return [
        { key: 'name', value: instr.name, editable: false },
        { key: 'linked', value: instr.isLinked, editable: false, type: 'boolean' },
        { key: 'NOT_CHANGED_SINCE', value: instr.notChangedSince ?? '—', editable: false },
    ];
}

function variationFields(v) {
    return [
        { key: 'depends_on', value: v.dependsOn ?? '—', editable: true },
    ];
}

export const PaneFO = {
    props: ['store'],
    setup(props) {
        function focused() {
            const fp = props.store.focusPath;
            return fp.length ? fp[fp.length - 1] : null;
        }

        function markDirty() {
            props.store.markDirty();
        }

        return () => {
            const node = focused();
            if (!node) return h('div', { class: 'se-fo-pane se-pane' }, 'Nothing selected');

            const children = [];

            if (node.type === 'instrument') {
                children.push(
                    h('h4', { style: 'margin:0 0 0.5rem' }, `Instrument: ${node.name}`),
                    h(ObjectExtended, { fields: instrFields(node), onChange: null }),
                );
            } else if (node.type === 'variation') {
                children.push(
                    h('h4', { style: 'margin:0 0 0.5rem' }, 'Variation'),
                    h(ObjectExtended, { fields: variationFields(node), onChange: ({ key, value }) => {
                        if (key === 'depends_on') node.dependsOn = value;
                        markDirty();
                    }}),
                    node.basicProperties
                        ? h(EnvelopeEditor, {
                            basicProperties: node.basicProperties,
                            onChange: markDirty,
                          })
                        : null,
                );
            } else if (node.type === 'label_spec') {
                children.push(
                    h('h4', { style: 'margin:0 0 0.5rem' }, `Label: ${node.label}`),
                    node.basicProperties
                        ? h(EnvelopeEditor, {
                            basicProperties: node.basicProperties,
                            onChange: markDirty,
                          })
                        : null,
                );
            } else if (node.type === 'bar') {
                children.push(
                    h('h4', { style: 'margin:0 0 0.5rem' }, `Bar: ${node.id}`),
                    h(ObjectExtended, { fields: [
                        { key: 'movement', value: node.movement },
                        { key: 'part',     value: node.part },
                        { key: 'line',     value: node.line },
                        { key: 'measure',  value: node.measure },
                    ], onChange: null }),
                );
            } else {
                children.push(h('pre', { style: 'font-size:0.75rem;white-space:pre-wrap' },
                    JSON.stringify(node, null, 2)));
            }

            return h('div', { class: 'se-fo-pane' }, children);
        };
    },
};
