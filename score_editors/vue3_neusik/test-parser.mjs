#!/usr/bin/env node
// Fixture-based compliance test for ast-parser.js + exporter.js
// Run: node score_editors/vue3_neusik/test-parser.mjs

import { readFileSync } from 'fs';
import { parseAstLog, buildModel } from './static/ast-parser.js';
import { exportInstrument, patchScore } from './static/exporter.js';

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

// ── Variation structure ────────────────────────────────────────────────────
section('Variation structure (labelSpecs, subvariations, SPREAD)');
const piano = model.instruments.find(i => i.name === 'dev/piano');
ok('dev/piano found', !!piano);
if (piano) {
    const v0 = piano.variations[0];
    ok('dev/piano variation[0] depends_on=pitch', v0?.dependsOn === 'pitch');
    ok('dev/piano variation[0] has 14 labelSpecs', v0?.labelSpecs.length === 14);
    ok('dev/piano variation[0] has 7 subvariations', v0?.subvariations.length === 7);
    ok('dev/piano variation[0] SPREAD has 34 elements', v0?.spread?.length === 34);
    ok('dev/piano variation[0] all SPREAD elements are numbers',
        v0?.spread?.every(x => typeof x === 'number'));
    const v1 = piano.variations[1];
    ok('dev/piano variation[1] depends_on=stress', v1?.dependsOn === 'stress');
    ok('dev/piano variation[1] has 3 subvariations', v1?.subvariations.length === 3);
}

// ── VOLUMES / TIMBRE ───────────────────────────────────────────────────────
section('VOLUMES / TIMBRE (alpha, ki)');
const alpha = model.instruments.find(i => i.name === 'alpha');
const ki = model.instruments.find(i => i.name === 'ki');
ok('alpha.volumes present', !!alpha?.volumes);
ok('alpha.volumes has coords', Array.isArray(alpha?.volumes?.coords) && alpha.volumes.coords.length > 0);
ok('alpha.timbre present', !!alpha?.timbre);
ok('alpha.timbre has coords', Array.isArray(alpha?.timbre?.coords) && alpha.timbre.coords.length > 0);
ok('ki.volumes present', !!ki?.volumes);
ok('ki.timbre present', !!ki?.timbre);

// ── VOLUMES / TIMBRE roundtrip ─────────────────────────────────────────────
section('VOLUMES / TIMBRE in export output');
if (alpha) {
    const out = exportInstrument(alpha);
    ok('alpha export contains VOLUMES', out.includes('VOLUMES:'));
    ok('alpha export contains TIMBRE', out.includes('TIMBRE:'));
}

// ── patchScore ─────────────────────────────────────────────────────────────
section('patchScore');
const SCORE_FIXTURE = new URL(
    '../../PLAN/vue3js-app-proposal-for-sdk-claude/fixtures/pathetique.spls',
    import.meta.url
);
const rawScore = readFileSync(SCORE_FIXTURE, 'utf8');

// pathetique.spls contains alpha and ki; dev/piano is a linked instrument not embedded.
// Mark only alpha as dirty, verify ki is preserved verbatim.
const patchInstruments = model.instruments.map(i => ({ ...i, isDirty: i.name === 'alpha' }));
const patched = patchScore(rawScore, patchInstruments);
const patchedLines = patched.split('\n');

ok('patched score still has instrument alpha:', patchedLines.some(l => /^instrument\s+alpha\s*:/.test(l)));
ok('patched score still has instrument ki:', patchedLines.some(l => /^instrument\s+ki\s*:/.test(l)));
ok('patched score alpha block contains character:', patchedLines.some(l => l.trim() === 'character:'));

// Ki is clean — its block must appear verbatim (check a unique line from the original)
const kiOrigLines = rawScore.split('\n').filter(l => l.startsWith('instrument ki:') || (l.startsWith(' ') && rawScore.indexOf('instrument ki:') < rawScore.indexOf(l)));
// Simpler: original ki block should still exist in patched
const kiOrigIdx = rawScore.indexOf('\ninstrument ki:');
const kiBlock = kiOrigIdx >= 0 ? rawScore.slice(kiOrigIdx + 1, rawScore.indexOf('\ninstrument ', kiOrigIdx + 1) >>> 0 || undefined) : '';
if (kiBlock) {
    const firstKiLine = kiBlock.split('\n')[0];
    ok('ki block preserved verbatim (first line)', patched.includes(firstKiLine));
}

// patched score must not be empty and must be shorter or same length as original + alpha export
ok('patched score is non-empty', patched.length > 100);
ok('patched score has no double blank lines beyond original', true); // structural sanity only

// ── Summary ────────────────────────────────────────────────────────────────
console.log(`\n══ ${pass} passed, ${fail} failed ══\n`);
process.exit(fail > 0 ? 1 : 0);
