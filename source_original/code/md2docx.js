// Markdown -> DOCX with the GRMS Partners visual identity (white, antracite 1A1A1A, bronze 8C5A35 sparingly).
// Usage: node md2docx.js input.md output.docx [baseDirForImages]
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, BorderStyle, Footer, Header, PageNumber,
  Table, TableRow, TableCell, WidthType, ShadingType, ImageRun, LevelFormat, PageBreak, TableLayoutType,
  VerticalAlign,
} = require('docx');

const C = { antracite: '1A1A1A', bronzo: '8C5A35', grigio: 'BFBFBF', grigioChiaro: 'F5F3EF', testoSec: '595959' };
const PAGE_W = 11906, PAGE_H = 16838, MARGIN = 1134, CONTENT_W = PAGE_W - 2 * MARGIN;

const [, , inPath, outPath, baseDirArg] = process.argv;
const baseDir = baseDirArg || path.dirname(inPath);
const md = fs.readFileSync(inPath, 'utf8').replace(/\r/g, '');
const lines = md.split('\n');

// ---------------------------------------------------------------- inline
function inline(text, opts = {}) {
  const size = opts.size || 21, color = opts.color || C.antracite, font = opts.font || 'Calibri';
  const runs = [];
  // tokens: **bold**, *italic*, `code`
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) runs.push(new TextRun({ text: text.slice(last, m.index), size, color, font, bold: opts.bold, italics: opts.italics }));
    const tok = m[0];
    if (tok.startsWith('**')) runs.push(new TextRun({ text: tok.slice(2, -2), bold: true, size, color, font, italics: opts.italics }));
    else if (tok.startsWith('`')) runs.push(new TextRun({ text: tok.slice(1, -1), font: 'Consolas', size: size - 2, color }));
    else runs.push(new TextRun({ text: tok.slice(1, -1), italics: true, size, color, font, bold: opts.bold }));
    last = m.index + tok.length;
  }
  if (last < text.length) runs.push(new TextRun({ text: text.slice(last), size, color, font, bold: opts.bold, italics: opts.italics }));
  return runs;
}

// ---------------------------------------------------------------- tables
function parseRow(l) {
  let s = l.trim();
  if (s.startsWith('|')) s = s.slice(1);
  if (s.endsWith('|')) s = s.slice(0, -1);
  return s.split('|').map(x => x.trim());
}
function buildTable(rows) {
  const header = rows[0], body = rows.slice(2);
  const n = header.length;
  const fontSize = n >= 12 ? 13 : n >= 8 ? 14 : n >= 6 ? 15 : 17;   // half-points
  // column widths proportional to content length (capped), sum = CONTENT_W
  const lens = header.map((h, j) => {
    const cells = body.map(r => (r[j] || '').replace(/\*\*/g, ''));
    const mxBody = Math.max(0, ...cells.map(v => Math.min(v.length, 60)));
    const longestWord = Math.max(...[h, ...cells].map(v => Math.max(0, ...v.replace(/\*\*/g, '').split(/\s+/).map(w => w.length))));
    const hdrLen = Math.min(h.length, 28);
    return Math.max(5, longestWord + 1, Math.min(Math.max(mxBody, hdrLen * 0.6), 48));
  });
  // absolute minimum per column so that the longest word never breaks
  const charW = fontSize * 10 * 0.56;
  const minW = header.map((h, j) => {
    const cells = [h, ...body.map(r => (r[j] || ''))].map(v => v.replace(/\*\*/g, ''));
    const lw = Math.max(...cells.map(v => Math.max(0, ...v.split(/\s+/).map(w => w.length))));
    return Math.ceil(Math.min(lw, 22) * charW + 180);
  });
  let widths = new Array(n).fill(0), fixed = new Array(n).fill(false);
  for (let it = 0; it < n; it++) {
    const free = CONTENT_W - widths.reduce((a, b, k) => a + (fixed[k] ? b : 0), 0);
    const totL = lens.reduce((a, b, k) => a + (fixed[k] ? 0 : b), 0);
    let changed = false;
    for (let k = 0; k < n; k++) if (!fixed[k]) {
      const w = Math.floor(free * lens[k] / totL);
      if (w < minW[k]) { widths[k] = minW[k]; fixed[k] = true; changed = true; } else widths[k] = w;
    }
    if (!changed) break;
  }
  widths[widths.length - 1] += CONTENT_W - widths.reduce((a, b) => a + b, 0);
  const border = { style: BorderStyle.SINGLE, size: 4, color: C.grigio };
  const hdrBorder = { style: BorderStyle.SINGLE, size: 10, color: C.antracite };
  const mkCell = (txt, j, isHdr) => new TableCell({
    width: { size: widths[j], type: WidthType.DXA },
    margins: { top: 40, bottom: 40, left: 70, right: 70 },
    verticalAlign: VerticalAlign.TOP,
    borders: { top: isHdr ? hdrBorder : border, bottom: isHdr ? hdrBorder : border, left: border, right: border },
    shading: isHdr ? { type: ShadingType.CLEAR, color: 'auto', fill: 'FFFFFF' } : undefined,
    children: [new Paragraph({ spacing: { before: 0, after: 0, line: 240 },
      alignment: (!isHdr && /^[-+]?[\d.,]+%?$|^n\.d\.$|^-$/.test(txt.replace(/\s/g, ''))) ? AlignmentType.RIGHT : AlignmentType.LEFT,
      children: inline(txt, { size: fontSize, bold: isHdr }) })],
  });
  const trs = [new TableRow({ tableHeader: true, children: header.map((h, j) => mkCell(h, j, true)) })];
  for (const r of body) trs.push(new TableRow({ cantSplit: true, children: header.map((_, j) => mkCell(r[j] || '', j, false)) }));
  return new Table({ width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: widths, layout: TableLayoutType.FIXED, rows: trs });
}

// ---------------------------------------------------------------- images
function pngSize(buf) { return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) }; }
function buildImage(alt, src) {
  const p = path.resolve(baseDir, src);
  if (!fs.existsSync(p)) return [new Paragraph({ children: inline(`[Figura non trovata: ${src}]`, { italics: true }) })];
  const buf = fs.readFileSync(p);
  const { w, h } = pngSize(buf);
  const maxW = 620; // px at 96 dpi ~ 16.4 cm
  const W = Math.min(maxW, w), H = Math.round(h * W / w);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 40 },
      children: [new ImageRun({ type: 'png', data: buf, transformation: { width: W, height: H }, altText: { title: alt, description: alt, name: alt } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
      children: [new TextRun({ text: alt, italics: true, size: 17, color: C.testoSec, font: 'Calibri' })] }),
  ];
}

// ---------------------------------------------------------------- cover
function cover(title, subtitle, note) {
  const out = [
    new Paragraph({ spacing: { before: 1800, after: 80 }, children: [new TextRun({ text: 'GRMS PARTNERS', bold: true, size: 30, color: C.antracite, font: 'Georgia', characterSpacing: 60 })] }),
    new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: 'Alta Sartoria Patrimoniale', italics: true, size: 24, color: C.bronzo, font: 'Georgia' })] }),
    new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: 'Consulenza Patrimoniale Indipendente', size: 19, color: C.antracite, font: 'Calibri' })] }),
    new Paragraph({ spacing: { after: 1400 }, children: [new TextRun({ text: 'Collana: Architettura Quantitativa  ·  Investment Advisory / Private Wealth / Tax Optimization', size: 19, color: C.antracite, font: 'Calibri' })] }),
    new Paragraph({ spacing: { after: 300 }, children: [new TextRun({ text: title, bold: true, size: 44, color: C.antracite, font: 'Georgia' })] }),
    new Paragraph({ spacing: { after: 900 }, children: [new TextRun({ text: subtitle, size: 25, color: C.antracite, font: 'Calibri' })] }),
  ];
  if (note) out.push(new Paragraph({ spacing: { after: 100 }, children: [new TextRun({ text: note, italics: true, size: 19, color: C.testoSec, font: 'Calibri' })] }));
  out.push(new Paragraph({ children: [new PageBreak()] }));
  return out;
}

// ---------------------------------------------------------------- main parse
const children = [];
let i = 0, numInstance = 0;
// skip the textual letterhead (first lines until the first '# ' title); capture title/subtitle/note
while (i < lines.length && !lines[i].startsWith('# ')) i++;
const title = lines[i].replace(/^#\s+/, ''); i++;
while (i < lines.length && !lines[i].startsWith('## ')) i++;
const subtitle = lines[i].replace(/^##\s+/, ''); i++;
let note = '';
while (i < lines.length && !lines[i].startsWith('## ')) {
  const l = lines[i].trim();
  if (l.startsWith('*') && l.endsWith('*') && !note) note = l.replace(/^\*|\*$/g, '');
  i++;
}
children.push(...cover(title, subtitle, note));

let para = [];
function flushPara() {
  if (!para.length) return;
  const text = para.join(' ');
  children.push(new Paragraph({ spacing: { after: 140, line: 288 }, alignment: AlignmentType.JUSTIFIED, children: inline(text) }));
  para = [];
}
let firstH2 = true;
while (i < lines.length) {
  const raw = lines[i];
  const l = raw.trimEnd();
  if (l.trim() === '') { flushPara(); i++; continue; }
  if (/^---+$/.test(l.trim())) { flushPara(); i++; continue; }
  if (l.startsWith('```')) {
    flushPara(); i++;
    while (i < lines.length && !lines[i].startsWith('```')) {
      children.push(new Paragraph({ spacing: { after: 0 }, shading: { type: ShadingType.CLEAR, color: 'auto', fill: C.grigioChiaro },
        children: [new TextRun({ text: lines[i], font: 'Consolas', size: 18, color: C.antracite })] }));
      i++;
    }
    i++; children.push(new Paragraph({ spacing: { after: 120 }, children: [] })); continue;
  }
  let m;
  if ((m = l.match(/^(#{2,4})\s+(.*)$/))) {
    flushPara();
    const lvl = m[1].length, txt = m[2];
    if (lvl === 2) {
      // each top-level section starts on a new page (except the first ones on the same page as abstract)
      if (!firstH2 && /^\d+\.|^Appendice|^Indice|^Executive/.test(txt)) children.push(new Paragraph({ children: [new PageBreak()] }));
      firstH2 = false;
      children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: txt })] }));
    } else if (lvl === 3) children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: txt })] }));
    else children.push(new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun({ text: txt })] }));
    i++; continue;
  }
  if ((m = l.match(/^!\[(.*)\]\((.*)\)$/))) { flushPara(); children.push(...buildImage(m[1], m[2])); i++; continue; }
  if (l.trim().startsWith('|')) {
    flushPara();
    const rows = [];
    while (i < lines.length && lines[i].trim().startsWith('|')) { rows.push(parseRow(lines[i])); i++; }
    if (rows.length >= 2) {
      children.push(buildTable(rows));
      children.push(new Paragraph({ spacing: { after: 100 }, children: [] }));
    }
    continue;
  }
  if ((m = l.match(/^(\s*)[-*]\s+(.*)$/)) && !/^\*[^*]/.test(l.trim()) || /^\s*-\s+/.test(l)) {
    flushPara();
    while (i < lines.length && /^(\s*)-\s+/.test(lines[i])) {
      const mm = lines[i].match(/^(\s*)-\s+(.*)$/);
      const level = Math.min(2, Math.floor(mm[1].length / 2));
      children.push(new Paragraph({ numbering: { reference: 'bullets', level }, spacing: { after: 60, line: 276 }, children: inline(mm[2]) }));
      i++;
    }
    children.push(new Paragraph({ spacing: { after: 60 }, children: [] }));
    continue;
  }
  if (/^\d+\.\s+/.test(l)) {
    flushPara(); numInstance++;
    while (i < lines.length && (/^\d+\.\s+/.test(lines[i]) || /^\s{2,}-\s+/.test(lines[i]))) {
      if (/^\d+\.\s+/.test(lines[i])) {
        const mm = lines[i].match(/^\d+\.\s+(.*)$/);
        children.push(new Paragraph({ numbering: { reference: 'numbers', level: 0, instance: numInstance }, spacing: { after: 60, line: 276 }, children: inline(mm[1]) }));
      } else {
        const mm = lines[i].match(/^\s+-\s+(.*)$/);
        children.push(new Paragraph({ numbering: { reference: 'bullets', level: 1 }, spacing: { after: 40, line: 276 }, children: inline(mm[1]) }));
      }
      i++;
    }
    children.push(new Paragraph({ spacing: { after: 60 }, children: [] }));
    continue;
  }
  if (l.startsWith('>')) {
    flushPara();
    const t = l.replace(/^>\s?/, '');
    children.push(new Paragraph({ spacing: { before: 120, after: 160 }, indent: { left: 400 },
      border: { left: { style: BorderStyle.SINGLE, size: 8, color: C.bronzo, space: 8 } }, children: inline(t, { size: 19, color: C.testoSec }) }));
    i++; continue;
  }
  if (/^\*[^*].*\*$/.test(l.trim())) {          // italic note line (table/figure caption)
    flushPara();
    children.push(new Paragraph({ spacing: { after: 160 }, children: inline(l.trim().slice(1, -1), { size: 17, italics: true, color: C.testoSec }) }));
    i++; continue;
  }
  para.push(l.trim());
  i++;
}
flushPara();

const doc = new Document({
  creator: 'GRMS Partners',
  title: title,
  description: subtitle,
  styles: {
    default: { document: { run: { font: 'Calibri', size: 21, color: C.antracite } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 30, bold: true, color: C.antracite, font: 'Georgia' },
        paragraph: { spacing: { before: 240, after: 160 }, keepNext: true, outlineLevel: 0,
          border: { bottom: { color: C.bronzo, space: 4, style: BorderStyle.SINGLE, size: 8 } } } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 25, bold: true, color: C.antracite, font: 'Georgia' },
        paragraph: { spacing: { before: 260, after: 120 }, keepNext: true, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 22, bold: true, color: C.antracite, font: 'Georgia' },
        paragraph: { spacing: { before: 200, after: 100 }, keepNext: true, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: 'bullets', levels: [
        { level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 400, hanging: 260 } } } },
        { level: 1, format: LevelFormat.BULLET, text: '–', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 800, hanging: 260 } } } },
        { level: 2, format: LevelFormat.BULLET, text: '·', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1200, hanging: 260 } } } },
      ] },
      { reference: 'numbers', levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 400, hanging: 300 } } } },
      ] },
    ],
  },
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: PAGE_H }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } }, titlePage: true },
    headers: {
      default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [
        new TextRun({ text: 'GRMS Partners  ·  January Buy  ·  Documento riservato per il Consiglio', size: 15, color: C.testoSec, font: 'Calibri' })] })] }),
      first: new Header({ children: [new Paragraph({ children: [] })] }),
    },
    footers: {
      default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
        new TextRun({ children: [PageNumber.CURRENT], color: C.bronzo, size: 17, font: 'Calibri' })] })] }),
      first: new Footer({ children: [new Paragraph({ alignment: AlignmentType.LEFT, children: [
        new TextRun({ text: 'GRMS Partners — Studio, Via Grazzano, Udine', size: 16, color: C.antracite, font: 'Calibri' })] })] }),
    },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => { fs.writeFileSync(outPath, buf); console.log('written', outPath, buf.length); });
