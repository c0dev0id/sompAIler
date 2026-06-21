import { h } from 'vue';

// One-line summary row with a drill-down chevron.
export const ObjectShort = {
    props: ['node', 'label', 'typeTag', 'focused', 'hasChildren'],
    emits: ['focus', 'drillDown'],
    setup(props, { emit }) {
        return () => h('li', {
            class: ['se-object-item', props.focused ? 'focused' : null],
            onClick: () => emit('focus'),
        }, [
            props.typeTag ? h('span', { class: 'se-object-type' }, props.typeTag) : null,
            h('span', { class: 'se-object-label' }, props.label),
            props.hasChildren
                ? h('button', {
                    class: 'se-chevron',
                    title: 'Drill down',
                    onClick: e => { e.stopPropagation(); emit('drillDown'); },
                  }, '›')
                : null,
        ]);
    },
};
