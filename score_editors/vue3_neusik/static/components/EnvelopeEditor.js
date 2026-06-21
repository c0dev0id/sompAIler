import { h, computed } from 'vue';
import { ShapeEditor } from './ShapeEditor.js';

// Default shapes used when toggling a section on for the first time.
function defaultShape(section) {
    switch (section) {
        case 'A': return { length: 10, start: 0, z: 1, coords: [{ x: 1, y: 10, z: 1, isSharp: false }] };
        case 'S': return { length: 10, start: 0, z: 1, coords: [{ x: 1, y: 100, z: 1, isSharp: false }] };
        case 'R': return { length: 5,  start: 0, z: 1, coords: [{ x: 1, y: 0,   z: 1, isSharp: false }] };
        default:  return { length: 1,  start: 0, z: 1, coords: [] };
    }
}

// Co-dependence:
// - Attack ending y=0 → disable S and R
// - S absent → R disabled
function attackEndsAtZero(shape) {
    if (!shape?.coords?.length) return false;
    return shape.coords[shape.coords.length - 1].y === 0;
}

export const EnvelopeEditor = {
    props: ['basicProperties', 'onChange'],
    setup(props) {
        function toggle(section) {
            const bp = props.basicProperties;
            if (bp[section]) {
                bp[section] = null;
            } else {
                bp[section] = defaultShape(section);
            }
            props.onChange?.();
        }

        return () => {
            const bp = props.basicProperties;
            if (!bp) return null;

            const aZero = attackEndsAtZero(bp.A);
            const sDisabled = aZero;
            const rDisabled = aZero || !bp.S;

            function section(key, label, disabled) {
                const active = !!bp[key];
                return h('div', { class: 'se-envelope-section' }, [
                    h('div', { class: 'se-envelope-toggle' }, [
                        h('input', {
                            type: 'checkbox',
                            id: `env-${key}`,
                            checked: active,
                            disabled,
                            onChange: () => !disabled && toggle(key),
                        }),
                        h('label', { for: `env-${key}` }, label),
                    ]),
                    active
                        ? h('div', { class: disabled ? 'se-envelope-disabled' : null }, [
                            h(ShapeEditor, {
                                shape: bp[key],
                                onChange: props.onChange,
                            }),
                          ])
                        : null,
                ]);
            }

            return h('div', null, [
                section('A', 'Attack',  false),
                section('S', 'Sustain', sDisabled),
                section('R', 'Release', rDisabled),
            ]);
        };
    },
};
