// RFC-compliant YAML serializer for Sompyler instrument blocks.
// Operates on the model produced by ast-parser.js buildModel().

// ── Shape ──────────────────────────────────────────────────────────────────
// RFC §1.3.4.5: SHAPE = [PREFIX (":" / ";")] Node 1*(";" Node)
//               Node  = x "," y ["*" z] ["!"]
// PREFIX+colon is the duration/resolution; optional START+semicolon follows.

function serializeShape(shape) {
    if (!shape) return null;
    const nodes = shape.coords.map(c => {
        let s = `${c.x},${c.y}`;
        if (c.z !== undefined && c.z !== 1) s += `*${c.z}`;
        if (c.isSharp) s += '!';
        return s;
    }).join(';');
    let prefix = '';
    if (shape.length != null) prefix = `${shape.length}:`;
    if (shape.start != null) prefix += `${shape.start};`;
    return prefix + nodes;
}

// ── FM / AM modulation ─────────────────────────────────────────────────────
// RFC §3.2.1.1.6-7: FM = FREQUENCY ["f"/"F"] ["@" OSC] ["[" SHAPE "]"] ";" MOD ":" BASE

function serializeFm(fm) {
    let s = String(fm.frequency ?? '');
    if (fm.factor) s += fm.factor;
    if (fm.osc) s += `@${fm.osc}`;
    if (fm.shape) s += `[${serializeShape(fm.shape)}]`;
    s += `;${fm.mod ?? ''}:${fm.base ?? ''}`;
    return s;
}

// ── Basic properties ───────────────────────────────────────────────────────
// RFC §3.2.1.1: O, A, S, R, FM go directly in the variation MAPPING.
// Returns array of YAML lines at 0 indent.

function basicPropLines(bp) {
    if (!bp) return [];
    const lines = [];
    if (bp.oscillator) lines.push(`O: ${bp.oscillator}`);
    const a = serializeShape(bp.A);
    if (a) lines.push(`A: "${a}"`);
    const s = serializeShape(bp.S);
    if (s) lines.push(`S: "${s}"`);
    const r = serializeShape(bp.R);
    if (r) lines.push(`R: "${r}"`);
    for (const fm of (bp.fmModulations ?? [])) lines.push(`FM: "${serializeFm(fm)}"`);
    return lines;
}

// ── Labelled property groups ───────────────────────────────────────────────
// RFC §3.2.1.2: label name (3+ lowercase chars) is the MAPPING KEY directly.
// Returns array of YAML lines at 0 indent.

function labelSpecLines(ls) {
    const inner = basicPropLines(ls.basicProperties);
    if (!inner.length) return [`${ls.label}:`];
    return [`${ls.label}:`, ...inner.map(l => `  ${l}`)];
}

// ── Variation ─────────────────────────────────────────────────────────────
// Returns YAML lines for one variation MAPPING (no leading "- ").

function variationLines(v) {
    const lines = [];
    if (v.dependsOn) lines.push(`ATTR: ${v.dependsOn}`);
    lines.push(...basicPropLines(v.basicProperties));
    for (const ls of (v.labelSpecs ?? [])) lines.push(...labelSpecLines(ls));
    if (v.spread?.length) lines.push(`SPREAD: [${v.spread.join(', ')}]`);
    for (const sv of (v.subvariations ?? [])) lines.push(...variationLines(sv));
    return lines;
}

// ── Instrument character block ─────────────────────────────────────────────
// Collects VOLUMES / TIMBRE / RAILSBACK_CURVE / FM from instrument level
// (RFC §3.2.1.3: these are variation-level properties, so they belong inside
// character, attached to the first/only variation).

function instrCharacterLines(instr) {
    const extraLines = [];
    const vol = serializeShape(instr.volumes);
    if (vol) extraLines.push(`VOLUMES: "${vol}"`);
    const timbre = serializeShape(instr.timbre);
    if (timbre) extraLines.push(`TIMBRE: "${timbre}"`);
    if (instr.railsbackCurve) {
        const rc = serializeShape(instr.railsbackCurve);
        if (rc) extraLines.push(`RAILSBACK_CURVE: "${rc}"`);
    }
    for (const fm of (instr.fmModulations ?? [])) extraLines.push(`FM: "${serializeFm(fm)}"`);

    const variations = instr.variations ?? [];
    const syntheticRoot = instr.basicProperties
        ? { basicProperties: instr.basicProperties, labelSpecs: [], subvariations: [], spread: null, dependsOn: null }
        : null;

    const allVariations = [
        ...(syntheticRoot ? [syntheticRoot] : []),
        ...variations,
    ];

    if (allVariations.length <= 1) {
        // Single variation — emit as MAPPING directly under character:
        const vLines = allVariations.length
            ? [...variationLines(allVariations[0]), ...extraLines]
            : extraLines;
        return vLines.map(l => `    ${l}`);
    }

    // Multiple variations — RFC MAYBE_LIST<VARIATION> as YAML sequence.
    const result = [];
    for (let i = 0; i < allVariations.length; i++) {
        const vLines = variationLines(allVariations[i]);
        const allLines = i === 0 ? [...vLines, ...extraLines] : vLines;
        if (!allLines.length) continue;
        result.push(`    - ${allLines[0]}`);
        for (const l of allLines.slice(1)) result.push(`      ${l}`);
    }
    return result;
}

// ── Instrument ────────────────────────────────────────────────────────────
// RFC §4.4: embedded instrument key is "instrument NAME:" not "instrument: 'NAME'"

export function exportInstrument(instr) {
    const lines = [`instrument ${instr.name}:`];
    if (instr.notChangedSince) lines.push(`  NOT_CHANGED_SINCE: ${instr.notChangedSince}`);
    lines.push(`  character:`);
    lines.push(...instrCharacterLines(instr));
    return lines.join('\n');
}

// ── Score patch ────────────────────────────────────────────────────────────
// Replace dirty instrument blocks in rawScoreText with RFC-serialized output.
// Non-dirty instruments are left verbatim.

export function patchScore(rawScoreText, instruments) {
    const lines = rawScoreText.split('\n');
    const result = [];
    const instrMap = {};
    for (const instr of instruments) {
        instrMap[instr.name] = instr;
        if (instr.name.includes('/')) instrMap[instr.name.split('/').pop()] = instr;
    }

    let i = 0;
    while (i < lines.length) {
        const line = lines[i];
        // RFC §4.4: "instrument NAME:" — strip optional quotes around name
        const m = line.match(/^instrument\s+(.+?)\s*:/);
        if (m) {
            const rawName = m[1].replace(/^'|'$/g, '');
            const instr = instrMap[rawName];
            if (instr && instr.isDirty) {
                i++;
                while (i < lines.length && (lines[i].startsWith(' ') || lines[i] === '')) i++;
                result.push(exportInstrument(instr));
                result.push('');
            } else {
                result.push(line);
                i++;
            }
        } else {
            result.push(line);
            i++;
        }
    }

    return result.join('\n');
}
