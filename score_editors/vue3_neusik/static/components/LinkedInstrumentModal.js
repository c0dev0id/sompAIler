import { h } from 'vue';

// Shown when the user edits a linked instrument (name contains '/').
// onEmbed: drop path prefix, instrument becomes embedded.
// onDiscard: revert the pending edit, keep instrument linked/unchanged.
export const LinkedInstrumentModal = {
    props: ['instrumentName', 'onEmbed', 'onDiscard'],
    setup(props) {
        const basename = props.instrumentName.split('/').pop();
        return () => h('div', null, [
            h('div', { class: 'se-overlay' }),
            h('div', { class: 'se-import-dialog' }, [
                h('h3', null, 'Linked instrument edited'),
                h('p', { style: 'font-size:0.85rem;margin:0 0 1rem' }, [
                    `Instrument `,
                    h('code', null, props.instrumentName),
                    ` is linked. Embed it as `,
                    h('code', null, basename),
                    `? If not, this edit is discarded.`,
                ]),
                h('div', { class: 'se-dialog-buttons' }, [
                    h('button', { class: 'se-btn', onClick: props.onDiscard }, 'Discard edit'),
                    h('button', { class: 'se-btn se-btn-primary', onClick: props.onEmbed }, 'Embed'),
                ]),
            ]),
        ]);
    },
};
