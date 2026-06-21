import { h } from 'vue';

// Renders a shape's coord table with cascade-shift and an SVG preview.
// `shape` is mutated in place; `onChange` called after each mutation.

export const ShapeEditor = {
    props: ['shape', 'onChange'],
    setup(props) {
        function updateCoord(i, field, value) {
            const coord = props.shape.coords[i];
            const num = parseFloat(value);
            if (isNaN(num)) return;
            const old = coord[field];
            const delta = num - old;
            coord[field] = num;

            // cascade-shift: if x increased past next coord, shift all following
            if (field === 'x' && delta > 0) {
                for (let j = i + 1; j < props.shape.coords.length; j++) {
                    if (props.shape.coords[j].x <= num) {
                        props.shape.coords[j].x += delta;
                    } else break;
                }
            }
            props.onChange?.();
        }

        function addCoord() {
            const coords = props.shape.coords;
            const lastX = coords.length ? coords[coords.length - 1].x + 1 : 1;
            coords.push({ x: lastX, y: 0, z: 1, isSharp: false });
            props.onChange?.();
        }

        function removeCoord(i) {
            props.shape.coords.splice(i, 1);
            props.onChange?.();
        }

        function renderSvg() {
            const coords = props.shape.coords;
            if (!coords.length) return h('svg', { class: 'se-shape-svg' });

            const xs = coords.map(c => c.x);
            const ys = coords.map(c => c.y);
            const minX = Math.min(...xs), maxX = Math.max(...xs);
            const minY = Math.min(...ys), maxY = Math.max(...ys);
            const W = 200, H = 60;
            const rangeX = maxX - minX || 1;
            const rangeY = maxY - minY || 1;

            const toSvg = c => {
                const sx = ((c.x - minX) / rangeX) * W;
                const sy = H - ((c.y - minY) / rangeY) * H;
                return [sx, sy];
            };

            const points = coords.map(c => toSvg(c).join(',') ).join(' ');

            return h('svg', {
                class: 'se-shape-svg',
                viewBox: `0 0 ${W} ${H}`,
                preserveAspectRatio: 'none',
            }, [
                h('polyline', {
                    points,
                    fill: 'none',
                    stroke: '#2a6aaa',
                    'stroke-width': '1.5',
                }),
                ...coords.map(c => {
                    const [sx, sy] = toSvg(c);
                    return h('circle', { cx: sx, cy: sy, r: 2.5, fill: '#6aacff' });
                }),
            ]);
        }

        return () => {
            const shape = props.shape;
            if (!shape) return null;

            return h('div', { class: 'se-shape-editor' }, [
                h('table', { class: 'se-shape-table' }, [
                    h('thead', null, h('tr', null, [
                        h('th', null, 'x'), h('th', null, 'y'), h('th', null, 'z'),
                        h('th', null, '♯'), h('th', null, ''),
                    ])),
                    h('tbody', null, shape.coords.map((coord, i) =>
                        h('tr', { key: i }, [
                            h('td', null, h('input', {
                                type: 'number', value: coord.x, step: 1,
                                onInput: e => updateCoord(i, 'x', e.target.value),
                            })),
                            h('td', null, h('input', {
                                type: 'number', value: coord.y, step: 1,
                                onInput: e => updateCoord(i, 'y', e.target.value),
                            })),
                            h('td', null, h('input', {
                                type: 'number', value: coord.z ?? 1, step: 0.1,
                                onInput: e => updateCoord(i, 'z', e.target.value),
                            })),
                            h('td', null, h('input', {
                                type: 'checkbox', checked: !!coord.isSharp,
                                onChange: e => { coord.isSharp = e.target.checked; props.onChange?.(); },
                            })),
                            h('td', null, h('button', { onClick: () => removeCoord(i) }, '✕')),
                        ])
                    )),
                ]),
                h('button', { class: 'se-btn', style: 'margin-top:0.3rem', onClick: addCoord }, '+ coord'),
                renderSvg(),
            ]);
        };
    },
};
