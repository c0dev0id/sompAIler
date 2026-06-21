import { h, ref, onMounted, onUnmounted } from 'vue';
import { fetchStatus } from '../api.js';

export const StatusPoller = {
    props: ['store'],
    setup(props) {
        const timer = ref(null);
        const eta = ref(null);

        function nextInterval(status) {
            if (!status) return 2000;
            const pct = status.progress ?? 0;
            // At 0–20%: poll at centile-of-ETA intervals
            if (eta.value && pct > 0 && pct <= 20) {
                return Math.max(500, (eta.value * 10) | 0);
            }
            return 2000;
        }

        async function poll() {
            try {
                const status = await fetchStatus(props.store.credentials);
                if (status.eta) eta.value = status.eta;
                props.store.synthesisStatus = status;
                if (status.frozen) {
                    // done — stop polling
                    return;
                }
            } catch (_) {
                // transient error — keep polling
            }
            timer.value = setTimeout(poll, nextInterval(props.store.synthesisStatus));
        }

        onMounted(() => { poll(); });
        onUnmounted(() => { if (timer.value) clearTimeout(timer.value); });

        return () => {
            const s = props.store.synthesisStatus;
            if (!s) return h('div', { class: 'se-status' }, 'Polling…');

            const pct = s.progress ?? 0;
            const label = s.frozen
                ? (s.error ? `Error: ${s.error}` : 'Done')
                : `${s.state ?? 'Running'} ${pct}%`;

            return h('div', { class: 'se-status' }, [
                h('span', null, label),
                h('div', { class: 'se-status-progress' }, [
                    h('div', { class: 'se-status-bar', style: { width: `${pct}%` } }),
                ]),
            ]);
        };
    },
};
