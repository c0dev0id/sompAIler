import { h, ref } from 'vue';
import { ObjectExtended } from './ObjectExtended.js';
import { EnvelopeEditor } from './EnvelopeEditor.js';
import { LinkedInstrumentModal } from './LinkedInstrumentModal.js';

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
        // Pending edit held while the linked-instrument modal is shown.
        const pendingEdit = ref(null);  // { instr, apply: fn }

        function focused() {
            const fp = props.store.focusPath;
            return fp.length ? fp[fp.length - 1] : null;
        }

        // Returns a change handler that intercepts the first edit to a linked
        // instrument and shows the embed-or-discard modal before applying it.
        function makeChangeHandler(instr, apply) {
            return () => {
                if (instr.isLinked && !instr.isDirty) {
                    // Stash the apply callback and show the modal.
                    pendingEdit.value = { instr, apply };
                } else {
                    apply();
                    instr.isDirty = true;
                    props.store.markDirty();
                }
            };
        }

        function embedInstrument(instr) {
            instr.name = instr.name.split('/').pop();
            instr.isLinked = false;
            instr.isDirty = true;
            pendingEdit.value.apply();
            pendingEdit.value = null;
            props.store.markDirty();
        }

        function discardEdit() {
            pendingEdit.value = null;
        }

        return () => {
            const node = focused();
            const children = [];

            if (!node || node.type === 'score') {
                return h('div', { class: 'se-fo-pane' }, 'Nothing selected');
            }

            if (node.type === 'instrument') {
                children.push(
                    h('h4', { style: 'margin:0 0 0.5rem' }, `Instrument: ${node.name}`),
                    h(ObjectExtended, { fields: instrFields(node), onChange: null }),
                );
            } else if (node.type === 'variation') {
                // Find the ancestor instrument for linked-instrument gating.
                const instr = props.store.scoreModel?.instruments.find(
                    i => i.variations?.includes(node) ||
                         i.variations?.some(v => v.subvariations?.includes(node))
                ) ?? null;

                const onChange = instr
                    ? makeChangeHandler(instr, () => { props.store.markDirty(); })
                    : () => props.store.markDirty();

                children.push(
                    h('h4', { style: 'margin:0 0 0.5rem' }, 'Variation'),
                    h(ObjectExtended, { fields: variationFields(node), onChange: ({ key, value }) => {
                        if (key === 'depends_on') node.dependsOn = value;
                        onChange();
                    }}),
                    node.basicProperties
                        ? h(EnvelopeEditor, { basicProperties: node.basicProperties, onChange })
                        : null,
                );
            } else if (node.type === 'label_spec') {
                const instr = props.store.scoreModel?.instruments.find(
                    i => i.variations?.some(v =>
                        v.labelSpecs?.includes(node) ||
                        v.subvariations?.some(sv => sv.labelSpecs?.includes(node))
                    )
                ) ?? null;

                const onChange = instr
                    ? makeChangeHandler(instr, () => { props.store.markDirty(); })
                    : () => props.store.markDirty();

                children.push(
                    h('h4', { style: 'margin:0 0 0.5rem' }, `Label: ${node.label}`),
                    node.basicProperties
                        ? h(EnvelopeEditor, { basicProperties: node.basicProperties, onChange })
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

            return h('div', { class: 'se-fo-pane' }, [
                ...children,
                pendingEdit.value
                    ? h(LinkedInstrumentModal, {
                        instrumentName: pendingEdit.value.instr.name,
                        onEmbed: () => embedInstrument(pendingEdit.value.instr),
                        onDiscard: discardEdit,
                      })
                    : null,
            ]);
        };
    },
};
