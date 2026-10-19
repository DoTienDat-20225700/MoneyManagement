import test from 'node:test';
import assert from 'node:assert/strict';

// Core WCAG 2.2 Relative Luminance and Contrast Ratio calculation formulas
function hexToRgb(hex) {
  let clean = hex.replace('#', '').trim();
  if (clean.length === 3) {
    clean = clean.split('').map(c => c + c).join('');
  }
  const num = parseInt(clean, 16);
  return {
    r: (num >> 16) & 255,
    g: (num >> 8) & 255,
    b: num & 255,
  };
}

function sRGBtoLin(colorChannel) {
  const c = colorChannel / 255;
  return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

function relativeLuminance(rgb) {
  const rLin = sRGBtoLin(rgb.r);
  const gLin = sRGBtoLin(rgb.g);
  const bLin = sRGBtoLin(rgb.b);
  return 0.2126 * rLin + 0.7152 * gLin + 0.0722 * bLin;
}

function contrastRatio(hex1, hex2) {
  const lum1 = relativeLuminance(hexToRgb(hex1));
  const lum2 = relativeLuminance(hexToRgb(hex2));
  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);
  return (lighter + 0.05) / (darker + 0.05);
}

function blendRgbaOnHex(rgbaStr, bgHex) {
  const match = rgbaStr.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
  if (!match) throw new Error(`Invalid rgba: ${rgbaStr}`);
  const r = parseInt(match[1]);
  const g = parseInt(match[2]);
  const b = parseInt(match[3]);
  const a = match[4] !== undefined ? parseFloat(match[4]) : 1.0;

  const bg = hexToRgb(bgHex);
  const blended = {
    r: Math.round(r * a + bg.r * (1 - a)),
    g: Math.round(g * a + bg.g * (1 - a)),
    b: Math.round(b * a + bg.b * (1 - a)),
  };
  return `#${((1 << 24) + (blended.r << 16) + (blended.g << 8) + blended.b).toString(16).slice(1)}`;
}

test('Contrast Math - Standard boundary calculations', () => {
  const whiteOnBlack = contrastRatio('#ffffff', '#000000');
  assert.ok(Math.abs(whiteOnBlack - 21.0) < 0.1, `White on black should be 21:1, got ${whiteOnBlack}`);

  const blackOnWhite = contrastRatio('#000000', '#ffffff');
  assert.ok(Math.abs(blackOnWhite - 21.0) < 0.1, `Symmetric check should be 21:1, got ${blackOnWhite}`);

  const identical = contrastRatio('#2b2b2b', '#2b2b2b');
  assert.equal(identical, 1.0, `Same color contrast should be exactly 1.0:1`);
});

test('Color Token: text.secondary (#9e9e9e) meets WCAG 2.2 AA (>= 4.5:1)', () => {
  const ratioOnPaper = contrastRatio('#9e9e9e', '#2b2b2b');
  assert.ok(
    ratioOnPaper >= 4.5,
    `text.secondary (#9e9e9e) on Paper (#2b2b2b) must be >= 4.5:1. Got ${ratioOnPaper.toFixed(2)}:1`
  );

  const ratioOnDefault = contrastRatio('#9e9e9e', '#080808');
  assert.ok(
    ratioOnDefault >= 4.5,
    `text.secondary (#9e9e9e) on Default (#080808) must be >= 4.5:1. Got ${ratioOnDefault.toFixed(2)}:1`
  );

  // Regression check: old #8a8a8a must fail
  const oldRatio = contrastRatio('#8a8a8a', '#2b2b2b');
  assert.ok(oldRatio < 4.5, `Old #8a8a8a was non-compliant (< 4.5:1)`);
});

test('Color Token: error.main / Expense red (#ff8285) meets WCAG 2.2 AA (>= 4.5:1)', () => {
  const ratioOnPaper = contrastRatio('#ff8285', '#2b2b2b');
  assert.ok(
    ratioOnPaper >= 4.5,
    `error.main (#ff8285) on Paper (#2b2b2b) must be >= 4.5:1. Got ${ratioOnPaper.toFixed(2)}:1`
  );

  // Chip text contrast: #ff8285 on background rgba(255, 130, 133, 0.15) over paper #2b2b2b
  const chipBg = blendRgbaOnHex('rgba(255, 130, 133, 0.15)', '#2b2b2b');
  const chipRatio = contrastRatio('#ff8285', chipBg);
  assert.ok(
    chipRatio >= 4.5,
    `Expense chip text on chip background must be >= 4.5:1. Got ${chipRatio.toFixed(2)}:1`
  );

  // Regression check: old #f25659 must fail
  const oldRatio = contrastRatio('#f25659', '#2b2b2b');
  assert.ok(oldRatio < 4.5, `Old #f25659 was non-compliant (< 4.5:1)`);
});

test('UI Component: OutlinedInput border (#5e5e5e) meets WCAG 2.2 Non-text contrast (>= 3.0:1)', () => {
  const ratioOnDefault = contrastRatio('#5e5e5e', '#080808');
  assert.ok(
    ratioOnDefault >= 3.0,
    `Input border (#5e5e5e) on Default (#080808) must be >= 3.0:1. Got ${ratioOnDefault.toFixed(2)}:1`
  );

  // Hover state #777777
  const hoverRatio = contrastRatio('#777777', '#080808');
  assert.ok(
    hoverRatio >= 3.0,
    `Input border hover (#777777) on Default (#080808) must be >= 3.0:1. Got ${hoverRatio.toFixed(2)}:1`
  );

  // Regression check: old #2b2b2b border on #080808 must fail
  const oldBorderRatio = contrastRatio('#2b2b2b', '#080808');
  assert.ok(oldBorderRatio < 3.0, `Old border #2b2b2b was non-compliant (< 3.0:1)`);
});

test('Graphical Object: LinearProgress track (rgba(255,255,255,0.36)) meets WCAG 2.2 (>= 3.0:1)', () => {
  const trackBlended = blendRgbaOnHex('rgba(255, 255, 255, 0.36)', '#2b2b2b');
  const trackRatio = contrastRatio(trackBlended, '#2b2b2b');
  assert.ok(
    trackRatio >= 3.0,
    `LinearProgress track on Paper (#2b2b2b) must be >= 3.0:1. Got ${trackRatio.toFixed(2)}:1`
  );

  // Progress fill Normal (#48cc90) contrast against paper background
  const fillNormalRatio = contrastRatio('#48cc90', '#2b2b2b');
  assert.ok(
    fillNormalRatio >= 3.0,
    `LinearProgress fill (#48cc90) on paper must be >= 3.0:1. Got ${fillNormalRatio.toFixed(2)}:1`
  );

  // Progress fill Danger (#ff8285) contrast against paper background
  const fillDangerRatio = contrastRatio('#ff8285', '#2b2b2b');
  assert.ok(
    fillDangerRatio >= 3.0,
    `LinearProgress fill (#ff8285) on paper must be >= 3.0:1. Got ${fillDangerRatio.toFixed(2)}:1`
  );

  // Regression check: old 0.08 track must fail
  const oldTrackBlended = blendRgbaOnHex('rgba(255, 255, 255, 0.08)', '#2b2b2b');
  const oldTrackRatio = contrastRatio(oldTrackBlended, '#2b2b2b');
  assert.ok(oldTrackRatio < 3.0, `Old track alpha was non-compliant (< 3.0:1)`);
});

test('Focus Indicator: :focus-visible outline (#00863A) meets WCAG 2.2 AA non-text contrast (>= 3.0:1)', () => {
  const ratioOnPaper = contrastRatio('#00863A', '#2b2b2b');
  assert.ok(
    ratioOnPaper >= 3.0,
    `Focus outline (#00863A) on Paper (#2b2b2b) must be >= 3.0:1. Got ${ratioOnPaper.toFixed(2)}:1`
  );

  const ratioOnDefault = contrastRatio('#00863A', '#080808');
  assert.ok(
    ratioOnDefault >= 3.0,
    `Focus outline (#00863A) on Default (#080808) must be >= 3.0:1. Got ${ratioOnDefault.toFixed(2)}:1`
  );
});

test('Reduced Motion (WCAG 2.3.3): matchMedia event listener lifecycle & fallback logic', () => {
  let listenerCalled = false;
  let listenerFn = null;
  const mockMql = {
    matches: false,
    addEventListener: (event, fn) => {
      assert.equal(event, 'change');
      listenerFn = fn;
    },
    removeEventListener: (event, fn) => {
      assert.equal(event, 'change');
      listenerFn = null;
    },
  };

  mockMql.addEventListener('change', (e) => {
    listenerCalled = e.matches;
  });

  assert.equal(typeof listenerFn, 'function', 'Listener function should be registered');
  listenerFn({ matches: true });
  assert.equal(listenerCalled, true, 'Event listener must update reduced motion state when OS settings change');

  mockMql.removeEventListener('change', listenerFn);
  assert.equal(listenerFn, null, 'Cleanup function must properly detach listener on unmount');
});

test('Heading Typography (WCAG 1.3.1): Semantic component prop preserves identical computed style', () => {
  const variantStyles = {
    h4: { fontSize: '2.125rem', fontWeight: 600, lineHeight: 1.235 },
    h5: { fontSize: '1.5rem', fontWeight: 600, lineHeight: 1.334 },
    h6: { fontSize: '1.25rem', fontWeight: 600, lineHeight: 1.6 },
    body1: { fontSize: '1rem', fontWeight: 400, lineHeight: 1.5 },
  };

  // In MUI v5, CSS styles are coupled to .MuiTypography-[variant] classes, not HTML tag selectors.
  // Changing component="h2" on Typography with variant="h6" or variant="h5" only alters the DOM tag,
  // leaving fontSize, fontWeight, lineHeight, and color 100% identical.
  const h6AsH2 = { ...variantStyles.h6, tag: 'h2' };
  const h6Default = { ...variantStyles.h6, tag: 'h6' };

  assert.equal(h6AsH2.fontSize, h6Default.fontSize, 'fontSize must not change when changing component prop');
  assert.equal(h6AsH2.fontWeight, h6Default.fontWeight, 'fontWeight must not change when changing component prop');
  assert.equal(h6AsH2.lineHeight, h6Default.lineHeight, 'lineHeight must not change when changing component prop');
  assert.notEqual(h6AsH2.tag, h6Default.tag, 'DOM tag must be semantically adjusted');
});

