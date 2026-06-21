import { h } from 'vue';
import { ObjectShort } from './ObjectShort.js';

// Shows sub-objects of the currently focused node — variations, bars, voices, etc.
export const PaneSubObjects = {
    props: ['store'],
    setup(props) {
        function focused() {
            const fp = props.store.focusPath;
            return fp.length ? fp[fp.length - 1] : props.store.scoreModel;
        }

        function subItems(node) {
            if (!node) return [];
            if (node.type === 'score') {
                return [
                    ...node.instruments.map(i => ({ kind: 'instrument', node: i, label: i.name })),
                    ...node.bars.map(b => ({ kind: 'bar', node: b, label: b.id })),
                ];
            }
            if (node.type === 'instrument') {
                return node.variations.map((v, idx) => ({
                    kind: 'variation',
                    node: v,
                    label: `variation ${idx + 1}${v.dependsOn ? ` (${v.dependsOn})` : ''}`,
                }));
            }
            if (node.type === 'variation') {
                return [
                    ...node.labelSpecs.map(ls => ({
                        kind: 'label_spec', node: ls, label: ls.label ?? '(no label)',
                    })),
                    ...node.subvariations.map((sv, idx) => ({
                        kind: 'variation', node: sv, label: `subvariation ${idx + 1}`,
                    })),
                ];
            }
            if (node.type === 'bar') {
                return Object.entries(node.voices).map(([name, v]) => ({
                    kind: 'voice', node: v, label: name,
                }));
            }
            return [];
        }

        return () => {
            const node = focused();
            const items = subItems(node);
            if (!items.length) return h('div', { class: 'se-pane' }, h('em', null, 'No sub-objects'));

            return h('div', { class: 'se-pane' }, [
                h('ul', { class: 'se-object-list' }, items.map((item, idx) =>
                    h(ObjectShort, {
                        key: idx,
                        node: item.node,
                        label: item.label,
                        typeTag: item.kind,
                        focused: props.store.focusPath.includes(item.node),
                        hasChildren: item.kind !== 'bar' && item.kind !== 'voice',
                        onFocus: () => props.store.pushFocus(item.node),
                        onDrillDown: () => props.store.pushFocus(item.node),
                    })
                )),
            ]);
        };
    },
};
