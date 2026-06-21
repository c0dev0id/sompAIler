import { h } from 'vue';

// Extended property view rendered as a definition list.
// `fields`: array of { key, value, editable?, type? }
// `onChange`: called with { key, value } when field changes.
export const ObjectExtended = {
    props: ['fields', 'onChange'],
    setup(props) {
        function onInput(key, type, rawValue) {
            let value = rawValue;
            if (type === 'number') value = parseFloat(rawValue);
            if (type === 'boolean') value = rawValue === 'true';
            props.onChange?.({ key, value });
        }

        return () => h('dl', null, (props.fields ?? []).flatMap(f => [
            h('dt', null, f.key),
            h('dd', null, f.editable
                ? (f.type === 'boolean'
                    ? h('select', {
                        value: String(f.value),
                        onChange: e => onInput(f.key, 'boolean', e.target.value),
                    }, [
                        h('option', { value: 'true' }, 'True'),
                        h('option', { value: 'false' }, 'False'),
                    ])
                    : h('input', {
                        type: f.type === 'number' ? 'number' : 'text',
                        value: f.value ?? '',
                        onInput: e => onInput(f.key, f.type, e.target.value),
                    })
                )
                : h('span', null, String(f.value ?? '—'))
            ),
        ]));
    },
};
