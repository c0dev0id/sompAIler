#!/usr/bin/env node
// Fixture-based compliance test for ast-parser.js + exporter.js
// Run: node score_editors/vue3_neusik/test-parser.mjs

import { readFileSync } from 'fs';
import { parseAstLog, buildModel } from './static/ast-parser.js';
import { exportInstrument } from './static/exporter.js';

const FIXTURE = new URL(
    '../../PLAN/vue3js-app-proposal-for-sdk-claude/fixtures/ast.log',
    import.meta.url
);
const text = readFileSync(FIXTURE, 'utf8');

let pass = 0, fail = 0;
function ok(label, value) {
    if (value) { console.log(`  ✓ ${label}`); pass++; }
    else        { console.error(`  ✗ ${label}`); fail++; }
}
function section(name) { console.log(`\n── ${name}`); }

// ── Parse ──────────────────────────────────────────────────────────────────
section('Parse pass');
const raw = parseAstLog(text);
ok('root node exists', raw && raw.slot === 'root');
ok('root has children', raw.children.length > 0);

// ── Build model ────────────────────────────────────────────────────────────
section('Build model');
const model = buildModel(raw);
ok('score type', model.type === 'score');
ok('has instruments', model.instruments.length > 0);
ok('has bars', model.bars.length > 0);
ok('432 bars', model.bars.length === 432);
console.log(`     bars: ${model.bars.length}, instruments: ${model.instruments.length}`);

// ── Bar IDs ────────────────────────────────────────────────────────────────
section('Bar IDs');
const barIdRe = /^(\w?)(\d+)(?:=\d+)?P(\d+)L(\d+)P?\d*M(\d+)$/;
const badBars = model.bars.filter(b => !barIdRe.test(b.id));
ok('all bar IDs parse', badBars.length === 0);
if (badBars.length) console.error(`     bad IDs: ${badBars.slice(0,5).map(b=>b.id).join(', ')}`);

// ── Instruments ────────────────────────────────────────────────────────────
section('Instruments');
for (const instr of model.instruments) {
    const label = `instrument "${instr.name}"`;
    ok(`${label} has name`, typeof instr.name === 'string' && instr.name.length > 0);
    ok(`${label} has variations or basicProperties`,
        instr.variations.length > 0 || instr.basicProperties !== null);

    for (const v of instr.variations) {
        ok(`${label} variation type`, v.type === 'variation');
        if (v.basicProperties) {
            const bp = v.basicProperties;
            for (const key of ['A', 'S', 'R']) {
                if (bp[key]) {
                    ok(`${label} ${key} shape has coords array`, Array.isArray(bp[key].coords));
                    for (const c of bp[key].coords) {
                        ok(`${label} ${key} coord has x+y`, c.x !== undefined && c.y !== undefined);
                    }
                }
            }
        }
    }
}

// ── Shape roundtrip ────────────────────────────────────────────────────────
section('Shape roundtrip (parse → export string)');

// Verify serializeShape output matches RFC pattern:
// [length:][start;]x,y[*z][!] separated by ;
const SHAPE_RE = /^(\d+(\.\d+)?:)?(\d+(\.\d+)?;)?(-?\d+(\.\d+)?,-?\d+(\.\d+)?(\*-?\d+(\.\d+)?)?!?(;-?\d+(\.\d+)?,-?\d+(\.\d+)?(\*-?\d+(\.\d+)?)?!?)*)$/;

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

let shapesChecked = 0;
for (const instr of model.instruments) {
    for (const v of instr.variations) {
        if (!v.basicProperties) continue;
        for (const key of ['A', 'S', 'R']) {
            const s = v.basicProperties[key];
            if (!s) continue;
            const str = serializeShape(s);
            ok(`${instr.name} ${key} shape serializes`, str !== null && str.length > 0);
            ok(`${instr.name} ${key} shape matches RFC pattern`, SHAPE_RE.test(str));
            shapesChecked++;
        }
    }
}
console.log(`     shapes checked: ${shapesChecked}`);

// ── Exporter ───────────────────────────────────────────────────────────────
section('exportInstrument output');

// RFC §4.4: instrument block must start with "instrument NAME:"
// followed by "  character:" block
for (const instr of model.instruments) {
    instr.isDirty = true; // force export path
    let out;
    try {
        out = exportInstrument(instr);
    } catch (e) {
        ok(`${instr.name} exportInstrument throws`, false);
        console.error(`     ${e.message}`);
        continue;
    }
    const lines = out.split('\n');
    ok(`${instr.name} starts with "instrument NAME:"`,
        /^instrument \S+.*:/.test(lines[0]));
    ok(`${instr.name} has character: block`,
        lines.some(l => l.trim() === 'character:'));
}

// ── RAILSBACK_CURVE roundtrip ──────────────────────────────────────────────
section('RAILSBACK_CURVE roundtrip');
const instrWithRC = model.instruments.filter(
    i => i.variations.some(v => v.railsbackCurve !== null)
);
console.log(`     instruments with RAILSBACK_CURVE: ${instrWithRC.length}`);
for (const instr of instrWithRC) {
    for (const v of instr.variations) {
        if (!v.railsbackCurve) continue;
        const out = exportInstrument(instr);
        ok(`${instr.name} RAILSBACK_CURVE in output`, out.includes('RAILSBACK_CURVE:'));
    }
}
if (instrWithRC.length === 0) {
    console.log('     (none in fixture — cannot verify roundtrip)');
}

// ── Summary ────────────────────────────────────────────────────────────────
console.log(`\n══ ${pass} passed, ${fail} failed ══\n`);
process.exit(fail > 0 ? 1 : 0);
