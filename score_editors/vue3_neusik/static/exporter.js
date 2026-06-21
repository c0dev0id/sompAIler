// Template-based YAML serializer — instrument blocks only (v1).
// Each object selects a template by finding the first entry in its
// selectExportTemplate() list where all required slots have values.
// Placeholders #0, #1, ... are filled with slot values.

function fillTemplate(template, slots) {
    return template.replace(/#(\d+)/g, (_, i) => slots[parseInt(i, 10)] ?? '');
}

function indent(text, level) {
    const pad = '  '.repeat(level);
    return text.split('\n').map((line, i) => {
        if (i === 0) return line;
        if (line.startsWith('- ')) return pad.slice(2) + line;
        return pad + line;
    }).join('\n');
}

// ── Shape ──────────────────────────────────────────────────────────────────

function exportCoord(coord) {
    let s = `x=${coord.x} y=${coord.y}`;
    if (coord.z !== undefined && coord.z !== 1) s += ` z=${coord.z}`;
    if (coord.isSharp) s += ` is_sharp=True`;
    return s;
}

function exportShape(shape, slotName, level) {
    if (!shape) return '';
    const coordLines = shape.coords.map(c => `  - coords: ${exportCoord(c)}`).join('\n');
    let header = `${slotName}: length=${shape.length}`;
    if (shape.start !== undefined) header += ` start=${shape.start}`;
    if (shape.z !== undefined && shape.z !== 1) header += ` z=${shape.z}`;
    const block = coordLines ? `${header}\n${coordLines}` : header;
    return indent(block, level);
}

// ── BasicProperties ────────────────────────────────────────────────────────

function exportBasicProperties(bp, level) {
    if (!bp) return '';
    const lines = [];
    if (bp.oscillator) lines.push(`  O: ref=${bp.oscillator}`);
    if (bp.A) lines.push(`  ${exportShape(bp.A, 'A', 1)}`);
    if (bp.S) lines.push(`  ${exportShape(bp.S, 'S', 1)}`);
    if (bp.R) lines.push(`  ${exportShape(bp.R, 'R', 1)}`);
    for (const fm of (bp.fmModulations ?? [])) {
        const parts = Object.entries(fm).map(([k, v]) => `${k}=${v}`).join(' ');
        lines.push(`  FM:\n    modulation: ${parts}`);
    }
    if (!lines.length) return '';
    return indent('basic_properties:\n' + lines.join('\n'), level);
}

// ── LabelSpec ─────────────────────────────────────────────────────────────

function exportLabelSpec(ls, level) {
    const label = ls.label ? ` '${ls.label}'` : '';
    const bp = exportBasicProperties(ls.basicProperties, 1);
    const body = bp ? `label_spec:${label}\n  ${bp}` : `label_spec:${label}`;
    return indent(body, level);
}

// ── Variation ─────────────────────────────────────────────────────────────

function exportVariation(v, level) {
    const dep = v.dependsOn ? ` depends_on=${v.dependsOn}` : '';
    const lines = [`variation:${dep}`];
    if (v.basicProperties) lines.push(`  ${exportBasicProperties(v.basicProperties, 1)}`);
    for (const ls of (v.labelSpecs ?? [])) lines.push(`  ${exportLabelSpec(ls, 1)}`);
    for (const sv of (v.subvariations ?? [])) lines.push(`  ${exportVariation(sv, 1)}`);
    if (v.spread?.length) lines.push(`  SPREAD: ${v.spread.join(' ')}`);
    return indent(lines.join('\n'), level);
}

// ── Instrument ────────────────────────────────────────────────────────────

export function exportInstrument(instr) {
    const lines = [];
    const name = instr.name;
    lines.push(`instrument: '${name}'`);

    for (const v of (instr.variations ?? [])) {
        lines.push(`  character:\n    ${exportVariation(v, 2)}`);
    }

    if (instr.basicProperties) {
        lines.push(`  character:\n    ${exportBasicProperties(instr.basicProperties, 2)}`);
    }

    if (instr.railsbackCurve) {
        lines.push(`  ${exportShape(instr.railsbackCurve, 'RAILSBACK_CURVE', 1)}`);
    }
    if (instr.volumes) {
        lines.push(`  ${exportShape(instr.volumes, 'VOLUMES', 1)}`);
    }
    if (instr.timbre) {
        lines.push(`  ${exportShape(instr.timbre, 'TIMBRE', 1)}`);
    }
    for (const fm of (instr.fmModulations ?? [])) {
        const parts = Object.entries(fm).map(([k, v]) => `${k}=${v}`).join(' ');
        lines.push(`  FM:\n    modulation: ${parts}`);
    }

    return lines.join('\n');
}

// ── Score patch ────────────────────────────────────────────────────────────

// Replace instrument blocks in rawScoreText with serialized model instruments.
// Non-dirty linked instruments (NOT_CHANGED_SINCE set, not edited) are left as-is
// from rawScoreText. Embedded and dirty instruments are emitted from the model.
export function patchScore(rawScoreText, instruments) {
    // Split raw text into instrument blocks and other sections.
    // Strategy: locate each `^instrument:` line and replace that block
    // (up to next same-indent section or EOF) with the serialized model.

    const lines = rawScoreText.split('\n');
    const result = [];
    const instrMap = {};
    for (const instr of instruments) {
        const basename = instr.name.includes('/') ? instr.name.split('/').pop() : instr.name;
        instrMap[basename] = instr;
        instrMap[instr.name] = instr;
    }

    let i = 0;
    while (i < lines.length) {
        const line = lines[i];
        const m = line.match(/^instrument:\s+'?([^']+)'?/);
        if (m) {
            const rawName = m[1];
            const instr = instrMap[rawName];
            if (instr && instr.isDirty) {
                // consume the raw block
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
