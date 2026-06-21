import { h } from 'vue';

// Inline identifier + a few key props — used for list rows.
export const ObjectBasic = {
    props: ['label', 'meta'],  // meta: array of {key, value} pairs
    setup(props) {
        return () => h('div', { class: 'se-object-label' }, [
            h('strong', null, props.label),
            ...(props.meta ?? []).map(({ key, value }) =>
                h('span', { style: 'color:#888;margin-left:0.5rem;font-size:0.8em' },
                    `${key}=${value}`)
            ),
        ]);
    },
};
