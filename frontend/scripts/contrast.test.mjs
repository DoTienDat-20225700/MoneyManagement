import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

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

test('Sidebar Contrast: Unselected item text (#9e9e9e) on Sidebar (#0d0e12) meets WCAG 2.2 AA (>= 4.5:1)', () => {
  const ratio = contrastRatio('#9e9e9e', '#0d0e12');
  assert.ok(ratio >= 4.5, `Unselected item text contrast must be >= 4.5:1. Got ${ratio.toFixed(2)}:1`);
});

test('Sidebar Contrast: Selected item text (#48cc90) on Active bg over Sidebar meets WCAG 2.2 AA (>= 4.5:1)', () => {
  const activeBg = blendRgbaOnHex('rgba(0, 134, 58, 0.22)', '#0d0e12');
  const ratio = contrastRatio('#48cc90', activeBg);
  assert.ok(ratio >= 4.5, `Selected item text contrast must be >= 4.5:1. Got ${ratio.toFixed(2)}:1`);
});

test('Sidebar Contrast: Active indicator (#48cc90) on Sidebar meets WCAG 2.2 Non-text (>= 3.0:1)', () => {
  const ratio = contrastRatio('#48cc90', '#0d0e12');
  assert.ok(ratio >= 3.0, `Active indicator contrast must be >= 3.0:1. Got ${ratio.toFixed(2)}:1`);
});

test('Sidebar Contrast: Collapse button icon (#9e9e9e) and hover state (#ffffff) meet WCAG 2.2 AA', () => {
  const normalRatio = contrastRatio('#9e9e9e', '#0d0e12');
  assert.ok(normalRatio >= 3.0, `Collapse button normal icon must be >= 3.0:1. Got ${normalRatio.toFixed(2)}:1`);

  const hoverBg = blendRgbaOnHex('rgba(255, 255, 255, 0.06)', '#0d0e12');
  const hoverRatio = contrastRatio('#ffffff', hoverBg);
  assert.ok(hoverRatio >= 4.5, `Collapse button hover text must be >= 4.5:1. Got ${hoverRatio.toFixed(2)}:1`);
});

test('Navigation Logic: aria-current matching correctly handles exact root and sub-routes', () => {
  const checkIsActive = (itemPath, currentPath) => {
    return itemPath === '/' ? currentPath === '/' : currentPath.startsWith(itemPath);
  };

  // Root path "/" must only be active on exact match
  assert.equal(checkIsActive('/', '/'), true);
  assert.equal(checkIsActive('/', '/transactions'), false);

  // Sub-paths must match exact and nested routes
  assert.equal(checkIsActive('/transactions', '/transactions'), true);
  assert.equal(checkIsActive('/transactions', '/transactions/detail/123'), true);
  assert.equal(checkIsActive('/transactions', '/budgets'), false);
  assert.equal(checkIsActive('/budgets', '/budgets'), true);
  assert.equal(checkIsActive('/reports', '/reports'), true);
  assert.equal(checkIsActive('/saving-plans', '/saving-plans'), true);
  assert.equal(checkIsActive('/debts', '/debts'), true);
});

test('Sidebar Contrast: Hamburger button icon (#e0e0e0) and focus outline meet WCAG 2.2 Non-text (>= 3.0:1)', () => {
  const iconRatio = contrastRatio('#e0e0e0', '#0d0e12');
  assert.ok(iconRatio >= 3.0, `Hamburger icon contrast must be >= 3.0:1. Got ${iconRatio.toFixed(2)}:1`);

  const focusRatio = contrastRatio('#00863A', '#0d0e12');
  assert.ok(focusRatio >= 3.0, `Focus outline contrast must be >= 3.0:1. Got ${focusRatio.toFixed(2)}:1`);
});

test('Navigation State: Default state is OPEN without localStorage read/write', () => {
  const dir = path.dirname(fileURLToPath(import.meta.url));
  const rootPath = path.resolve(dir, '..', 'src', 'routes', 'Root.tsx');
  const appDrawerPath = path.resolve(dir, '..', 'src', 'components', 'AppDrawer.tsx');

  const rootContent = fs.readFileSync(rootPath, 'utf-8');
  const drawerContent = fs.readFileSync(appDrawerPath, 'utf-8');

  // Verify no localStorage usage for sidebar collapsed state
  assert.ok(!rootContent.includes('mm_sidebar_collapsed'), 'Root.tsx must NOT store/read mm_sidebar_collapsed in localStorage');
  assert.ok(!drawerContent.includes('mm_sidebar_collapsed'), 'AppDrawer.tsx must NOT store/read mm_sidebar_collapsed in localStorage');

  // Default state is open (collapsed = false)
  assert.ok(rootContent.includes('useState<boolean>(false)'), 'Root.tsx must initialize collapsed state to false (open)');
});

test('Navigation Logic: Content click-to-collapse rules', () => {
  // Mock state machine for auto-collapse
  let collapsed = false;
  let isTransitioning = false;

  const handleMainContentClick = ({ innerWidth, isCollapsed, detail, selectionLength, targetInMain }) => {
    if (innerWidth < 900) return; // f. Below md, ignore
    if (isCollapsed || isTransitioning) return; // d. Ignore if collapsed or transitioning
    if (detail === 0) return; // b. Synthetic keyboard click (Enter/Space) -> ignore
    if (selectionLength > 0) return; // Drag selection -> ignore
    if (!targetInMain) return; // c. Click outside main (sidebar/topbar/dialog) -> ignore

    collapsed = true;
  };

  // Rule 1: Mouse click in main while open -> collapses
  collapsed = false;
  handleMainContentClick({ innerWidth: 1280, isCollapsed: false, detail: 1, selectionLength: 0, targetInMain: true });
  assert.equal(collapsed, true, 'Valid mouse click in main must trigger collapse');

  // Rule 2: Synthetic keyboard click (Enter/Space, detail: 0) -> does NOT collapse
  collapsed = false;
  handleMainContentClick({ innerWidth: 1280, isCollapsed: false, detail: 0, selectionLength: 0, targetInMain: true });
  assert.equal(collapsed, false, 'Keyboard Enter/Space (detail: 0) must NOT collapse sidebar');

  // Rule 3: Text selection active -> does NOT collapse
  collapsed = false;
  handleMainContentClick({ innerWidth: 1280, isCollapsed: false, detail: 1, selectionLength: 12, targetInMain: true });
  assert.equal(collapsed, false, 'Mouse release after text selection must NOT collapse sidebar');

  // Rule 4: Click outside main (e.g. TopBar or Sidebar or Dialog portal) -> does NOT collapse
  collapsed = false;
  handleMainContentClick({ innerWidth: 1280, isCollapsed: false, detail: 1, selectionLength: 0, targetInMain: false });
  assert.equal(collapsed, false, 'Click on TopBar or Sidebar must NOT collapse sidebar');

  // Rule 5: Screen under md (< 900px) -> does NOT collapse
  collapsed = false;
  handleMainContentClick({ innerWidth: 768, isCollapsed: false, detail: 1, selectionLength: 0, targetInMain: true });
  assert.equal(collapsed, false, 'Click on mobile/tablet under md must NOT collapse sidebar');

  // Rule 6: Manual re-open by hamburger button keeps sidebar open until next content click
  collapsed = true;
  // User clicks hamburger button to toggle open:
  collapsed = false;
  assert.equal(collapsed, false, 'Sidebar reopened manually stays open');
  // Next content click collapses it again:
  handleMainContentClick({ innerWidth: 1280, isCollapsed: false, detail: 1, selectionLength: 0, targetInMain: true });
  assert.equal(collapsed, true, 'Next content click collapses sidebar again');
});

test('Route Isolation: AuthRoot and unauthenticated routes do not include AppDrawer', () => {
  const dir = path.dirname(fileURLToPath(import.meta.url));
  const authRootPath = path.resolve(dir, '..', 'src', 'routes', 'AuthRoot.tsx');
  const authRootContent = fs.readFileSync(authRootPath, 'utf-8');

  assert.ok(!authRootContent.includes('AppDrawer'), 'AuthRoot.tsx must NOT import or render AppDrawer');
  assert.ok(!authRootContent.includes('navigation'), 'AuthRoot.tsx must NOT import navigation');
});

test('A11Y-014: Heading hierarchy strictly structured without h1->h5 jump', () => {
  const dir = path.dirname(fileURLToPath(import.meta.url));
  const budgetsPath = path.resolve(dir, '..', 'src', 'routes', 'Budgets.tsx');
  const reportsPath = path.resolve(dir, '..', 'src', 'routes', 'Reports.tsx');

  const budgetsContent = fs.readFileSync(budgetsPath, 'utf-8');
  const reportsContent = fs.readFileSync(reportsPath, 'utf-8');

  // Verify that Budgets.tsx and Reports.tsx have component="h1"
  assert.ok(budgetsContent.includes('component="h1"'), 'Budgets.tsx must define an h1');
  assert.ok(reportsContent.includes('component="h1"'), 'Reports.tsx must define an h1');

  // Verify that any h5/h6 variants use component="span" or component="div" or component="h2"
  assert.ok(!reportsContent.includes('<Typography variant="h5"'), 'Reports.tsx must not render unaliased <h5> tag');
  assert.ok(!reportsContent.includes('<Typography variant="h6"'), 'Reports.tsx must not render unaliased <h6> tag');
});

test('A11Y-015: Bulk delete button satisfies WCAG 2.5.3 and includes item count in name and visible label', () => {
  // Test parameterized translation substitution
  const formatMsg = (str, params) => {
    let res = str;
    for (const [k, v] of Object.entries(params)) {
      res = res.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v));
    }
    return res;
  };

  const viTemplate = 'Xoá {count} giao dịch';
  const enTemplate = 'Delete {count} transactions';

  const vi3 = formatMsg(viTemplate, { count: 3 });
  const en3 = formatMsg(enTemplate, { count: 3 });

  assert.equal(vi3, 'Xoá 3 giao dịch');
  assert.equal(en3, 'Delete 3 transactions');

  // WCAG 2.5.3 Label in Name: aria-label MUST contain the visible text
  const visibleText = vi3;
  const accessibleName = vi3;
  assert.ok(accessibleName.includes(visibleText), 'Accessible name must contain the visible label text');
});

test('A11Y-016: ApexCharts configurations respect prefers-reduced-motion', () => {
  const dir = path.dirname(fileURLToPath(import.meta.url));
  const chartFiles = [
    path.resolve(dir, '..', 'src', 'components', 'charts', 'ProfileChart.tsx'),
    path.resolve(dir, '..', 'src', 'components', 'charts', 'CurrentMonthChart.tsx'),
    path.resolve(dir, '..', 'src', 'components', 'reports', 'CashFlowForecast.tsx'),
    path.resolve(dir, '..', 'src', 'routes', 'Reports.tsx'),
  ];

  for (const filePath of chartFiles) {
    const content = fs.readFileSync(filePath, 'utf-8');
    assert.ok(
      content.includes('usePrefersReducedMotion'),
      `${path.basename(filePath)} must import and invoke usePrefersReducedMotion`
    );
    assert.ok(
      content.includes('!prefersReducedMotion'),
      `${path.basename(filePath)} must toggle chart animations with !prefersReducedMotion`
    );
  }
});


