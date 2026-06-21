const LINE_RE = /^(\d{2}) (\S+(?:\.\S+)*) ?(.*)/;
const DEBUG_RE = /^\d{2} # DEBUG/;


function coerce(s) {
    if (s === 'True' || s === 'Y' || s === 'on' || s === 'true') return true;
    if (s === 'False' || s === 'N' || s === 'off' || s === 'false') return false;
    if (s === '') return s;
    const n = Number(s);
    if (!isNaN(n) && s.trim() !== '') return n;
    return s;
}

export function parseAstLog(text) {
    const root = { slot: 'root', parentSlot: null, depth: -1, positionals: [], props: {}, children: [] };
    const stack = [root];

    for (const line of text.split('\n')) {
        if (!line.trim()) continue;
        if (DEBUG_RE.test(line)) continue;

        const m = LINE_RE.exec(line);
        if (!m) continue;

        const depth = parseInt(m[1], 10);
        const slotFull = m[2];
        const rest = m[3] || '';

        const dotIdx = slotFull.indexOf('.');
        let parentSlot = null, slot = slotFull;
        if (dotIdx !== -1) {
            parentSlot = slotFull.slice(0, dotIdx);
            slot = slotFull.slice(dotIdx + 1);
        }

        const { positionals, props } = parseRest(rest);

        const node = { slot, parentSlot, depth, positionals, props, children: [] };

        // Pop stack to find correct parent (parent must have depth < current)
        while (stack.length > 1 && stack[stack.length - 1].depth >= depth) {
            stack.pop();
        }

        stack[stack.length - 1].children.push(node);
        stack.push(node);
    }

    return root;
}

function parseRest(rest) {
    const positionals = [];
    const props = {};
    let i = 0;
    const n = rest.length;
    let inProps = false;

    while (i < n) {
        // skip spaces
        while (i < n && rest[i] === ' ') i++;
        if (i >= n) break;

        if (rest[i] === "'") {
            // single-quoted value (positional string)
            const j = rest.indexOf("'", i + 1);
            const val = rest.slice(i + 1, j === -1 ? n : j);
            i = j === -1 ? n : j + 1;
            if (!inProps) positionals.push(val);
        } else {
            // scan to next space
            let j = i;
            while (j < n && rest[j] !== ' ') j++;
            const tok = rest.slice(i, j);
            i = j;

            const eqIdx = tok.indexOf('=');
            if (eqIdx !== -1) {
                inProps = true;
                const key = tok.slice(0, eqIdx);
                let rawVal = tok.slice(eqIdx + 1);

                if (rawVal.startsWith("'")) {
                    // value continues until next single quote
                    const valStart = i - (tok.length - eqIdx - 1);
                    // find closing quote: search from after the opening quote
                    const openPos = rest.indexOf("'", rest.lastIndexOf(key + '=', i) + key.length + 1);
                    const closePos = rest.indexOf("'", openPos + 1);
                    rawVal = closePos === -1 ? rest.slice(openPos + 1) : rest.slice(openPos + 1, closePos);
                    i = closePos === -1 ? n : closePos + 1;
                }

                props[key] = coerce(rawVal);
            } else if (!inProps) {
                positionals.push(coerce(tok));
            }
            // bare token after props start is ignored (shouldn't happen per spec)
        }
    }

    return { positionals, props };
}

// ── Second pass: build typed model ──────────────────────────────────────────

export function buildModel(rawTree) {
    const score = {
        type: 'score',
        info: null,
        tuning: null,
        articles: [],
        stageVoices: [],
        instruments: [],
        bars: [],
    };

    for (const node of rawTree.children) {
        switch (node.slot) {
            case 'info':
                score.info = { ...node.props };
                break;
            case 'tuning':
                score.tuning = buildTuning(node);
                break;
            case 'article':
                score.articles.push(buildArticle(node));
                break;
            case 'stage_voice':
                score.stageVoices.push({
                    name: node.positionals[0],
                    direction: node.props.direction,
                    distance: node.props.distance,
                });
                break;
            case 'instrument':
                score.instruments.push(buildInstrument(node));
                break;
            case 'bar':
                score.bars.push(buildBar(node));
                break;
            default:
                score[node.slot] = buildGeneric(node);
        }
    }

    return score;
}

function buildTuning(node) {
    const t = { base: node.props.base, scales: {}, chords: {} };
    for (const child of node.children) {
        if (child.slot === 'scales') {
            t.scales[child.positionals[0]] = child.positionals.slice(1);
        } else if (child.slot === 'chords') {
            t.chords[child.positionals[0]] = child.positionals.slice(1);
        }
    }
    return t;
}

function buildArticle(node) {
    return {
        type: 'article',
        name: node.positionals[0],
        props: { ...node.props },
        properties: node.children
            .filter(c => c.slot === 'property')
            .map(c => ({ name: c.positionals[0], ...c.props })),
    };
}

function buildInstrument(node) {
    const instr = {
        type: 'instrument',
        name: node.positionals[0],
        notChangedSince: node.props.NOT_CHANGED_SINCE ?? null,
        isLinked: (node.positionals[0] ?? '').includes('/'),
        isDirty: false,
        variations: [],
        basicProperties: null,
        volumes: null,
        timbre: null,
        fmModulations: [],
        rawChildren: [],
    };

    for (const child of node.children) {
        switch (child.parentSlot + '.' + child.slot) {
            case 'character.variation':
                instr.variations.push(buildVariation(child));
                break;
            case 'character.basic_properties':
                instr.basicProperties = buildBasicProperties(child);
                break;
            case 'VOLUMES.shape':
                instr.volumes = buildShape(child);
                break;
            case 'TIMBRE.shape':
                instr.timbre = buildShape(child);
                break;
            case 'FM.modulation':
                instr.fmModulations.push({ ...child.props });
                break;
            default:
                instr.rawChildren.push(buildGeneric(child));
        }
    }

    return instr;
}

function buildVariation(node) {
    const v = {
        type: 'variation',
        dependsOn: node.props.depends_on ?? null,
        basicProperties: null,
        labelSpecs: [],
        subvariations: [],
        spread: null,
        railsbackCurve: null,
        rawChildren: [],
    };

    for (const child of node.children) {
        const key = (child.parentSlot ?? child.slot) + '.' + child.slot;
        switch (key) {
            case 'variation.basic_properties':
                v.basicProperties = buildBasicProperties(child);
                break;
            case 'variation.label_spec':
                v.labelSpecs.push(buildLabelSpec(child));
                break;
            case 'variation.subvariation':
                v.subvariations.push(buildVariation(child));
                break;
            case 'variation.SPREAD':
                v.spread = child.positionals;
                break;
            case 'RAILSBACK_CURVE.shape':
                v.railsbackCurve = buildShape(child);
                break;
            default:
                v.rawChildren.push(buildGeneric(child));
        }
    }

    return v;
}

function buildBasicProperties(node) {
    const bp = {
        type: 'basic_properties',
        A: null, S: null, R: null,
        oscillator: null,
        fmModulations: [],
        rawChildren: [],
    };

    for (const child of node.children) {
        const fqSlot = (child.parentSlot ?? '') + (child.parentSlot ? '.' : '') + child.slot;
        if (child.parentSlot === 'A' && child.slot === 'shape') {
            bp.A = buildShape(child);
        } else if (child.parentSlot === 'S' && child.slot === 'shape') {
            bp.S = buildShape(child);
        } else if (child.parentSlot === 'R' && child.slot === 'shape') {
            bp.R = buildShape(child);
        } else if (child.parentSlot === 'variation' && child.slot === 'O') {
            bp.oscillator = child.props.ref ?? child.positionals[0];
        } else if (child.parentSlot === 'FM' && child.slot === 'modulation') {
            const fm = { ...child.props };
            const envChild = child.children.find(c => c.slot === 'shape');
            if (envChild) fm.shape = buildShape(envChild);
            bp.fmModulations.push(fm);
        } else {
            bp.rawChildren.push(buildGeneric(child));
        }
    }

    return bp;
}

function buildLabelSpec(node) {
    const ls = {
        type: 'label_spec',
        label: node.positionals[0],
        basicProperties: null,
        rawChildren: [],
    };

    const directBpChildren = [];
    for (const child of node.children) {
        if (child.parentSlot === 'variation' && child.slot === 'basic_properties') {
            ls.basicProperties = buildBasicProperties(child);
        } else if (
            (child.slot === 'shape' && (child.parentSlot === 'A' || child.parentSlot === 'S' || child.parentSlot === 'R')) ||
            (child.parentSlot === 'variation' && child.slot === 'O') ||
            (child.parentSlot === 'FM' && child.slot === 'modulation')
        ) {
            directBpChildren.push(child);
        } else {
            ls.rawChildren.push(buildGeneric(child));
        }
    }
    if (!ls.basicProperties && directBpChildren.length > 0) {
        ls.basicProperties = buildBasicProperties({ children: directBpChildren });
    }

    return ls;
}

function buildShape(node) {
    return {
        type: 'shape',
        length: node.props.length,
        start: node.props.start,
        coords: node.children
            .filter(c => c.slot === 'coords')
            .map(c => ({
                x: c.props.x,
                y: c.props.y,
                z: c.props.z ?? 1,
                isSharp: c.props.is_sharp ?? false,
            })),
    };
}

function buildBar(node) {
    const bar = {
        type: 'bar',
        id: node.positionals[0] ?? '',
        stressor: null,
        tempoShape: null,
        tempoLevels: null,
        lowerStressBound: null,
        upperStressBound: null,
        tunings: [],
        voices: {},
        rawChildren: [],
    };

    for (const child of node.children) {
        const fqSlot = (child.parentSlot ?? '') + (child.parentSlot ? '.' : '') + child.slot;
        switch (fqSlot) {
            case 'stress_pattern.stressor':
                bar.stressor = buildStressor(child);
                break;
            case 'tempo.shape':
                bar.tempoShape = buildShape(child);
                break;
            case 'tempo.levels':
                bar.tempoLevels = child.positionals[0];
                break;
            case 'lower_stress_bound.shape':
                bar.lowerStressBound = buildShape(child);
                break;
            case 'upper_stress_bound.shape':
                bar.upperStressBound = buildShape(child);
                break;
            case 'bar.tuning':
                bar.tunings.push({ ...child.props });
                break;
            case 'bar.voice':
                bar.voices[child.positionals[0]] = buildVoice(child);
                break;
            default:
                bar.rawChildren.push(buildGeneric(child));
        }
    }

    return bar;
}

function buildStressor(node) {
    const levels = [];
    let currentGroup = [];
    for (const child of node.children) {
        if (child.slot === 'level') {
            currentGroup.push(parseInt(child.positionals[0]));
        } else if (child.slot === 'subdivision') {
            levels.push(currentGroup);
            currentGroup = [];
        }
    }
    if (currentGroup.length) levels.push(currentGroup);
    return { type: 'stressor', groups: levels };
}

function buildVoice(node) {
    const voice = {
        type: 'voice',
        name: node.positionals[0],
        offsets: [],
        articles: [],
        motifs: [],
    };

    for (const child of node.children) {
        const fqSlot = (child.parentSlot ?? '') + (child.parentSlot ? '.' : '') + child.slot;
        switch (fqSlot) {
            case 'voice.offset':
                voice.offsets.push(buildOffset(child));
                break;
            case 'voice.article':
                voice.articles.push(child.positionals[0]);
                break;
            case 'voice.motif':
                voice.motifs.push(child.props.label);
                break;
            default:
                // ignore
        }
    }

    return voice;
}

function buildOffset(node) {
    const offset = {
        type: 'offset',
        tick: node.props.tick,
        stemNotes: [],
        clusters: [],
        chains: [],
    };

    for (const child of node.children) {
        const fqSlot = (child.parentSlot ?? '') + (child.parentSlot ? '.' : '') + child.slot;
        switch (fqSlot) {
            case 'offset.stem_note':
                offset.stemNotes.push({ pitch: child.props.pitch, effLength: child.props.eff_length });
                break;
            case 'offset.cluster':
                offset.clusters.push(buildCluster(child));
                break;
            case 'offset.chain':
                offset.chains.push({ index: child.positionals[0], children: child.children.map(buildGeneric) });
                break;
            default:
                // ignore
        }
    }

    return offset;
}

function buildCluster(node) {
    const cluster = {
        type: 'cluster',
        index: node.positionals[0],
        repeat: node.props.repeat ?? null,
        notes: [],
        pauses: [],
        groups: [],
        subchains: [],
    };

    for (const child of node.children) {
        switch (child.slot) {
            case 'note':
                cluster.notes.push({ ...child.props });
                break;
            case 'pause':
                cluster.pauses.push({ length: child.props.length });
                break;
            case 'group':
                cluster.groups.push({ length: child.props.length, netlength: child.props.netlength });
                break;
            case 'subchain':
                cluster.subchains.push({ length: child.props.length, children: child.children.map(buildGeneric) });
                break;
            default:
                // ignore
        }
    }

    return cluster;
}

function buildGeneric(node) {
    return {
        type: node.slot,
        parentSlot: node.parentSlot,
        depth: node.depth,
        positionals: node.positionals,
        props: node.props,
        children: node.children.map(buildGeneric),
    };
}
