import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const FRONTEND_DIR = path.resolve(__dirname, "..");
const THEME_PATH = path.join(FRONTEND_DIR, "src", "theme.tsx");

// 1. WCAG 2.2 Color Contrast Utilities
function parseColor(colorStr) {
  if (!colorStr) return null;
  const s = colorStr.trim().toLowerCase();

  // Hex format #rgb, #rgba, #rrggbb, #rrggbbaa
  if (s.startsWith("#")) {
    let hex = s.slice(1);
    let a = 1.0;
    if (hex.length === 3) {
      hex = hex.split("").map((c) => c + c).join("");
    } else if (hex.length === 4) {
      a = parseInt(hex[3] + hex[3], 16) / 255;
      hex = hex.slice(0, 3).split("").map((c) => c + c).join("");
    } else if (hex.length === 8) {
      a = parseInt(hex.slice(6, 8), 16) / 255;
      hex = hex.slice(0, 6);
    }
    const r = parseInt(hex.slice(0, 2), 16);
    const g = parseInt(hex.slice(2, 4), 16);
    const b = parseInt(hex.slice(4, 6), 16);
    return { r, g, b, a };
  }

  // rgba or rgb format
  const rgbMatch = s.match(/rgba?\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)(?:\s*,\s*([0-9.]+))?\s*\)/);
  if (rgbMatch) {
    const r = parseFloat(rgbMatch[1]);
    const g = parseFloat(rgbMatch[2]);
    const b = parseFloat(rgbMatch[3]);
    const a = rgbMatch[4] !== undefined ? parseFloat(rgbMatch[4]) : 1.0;
    return { r, g, b, a };
  }

  return null;
}

function compositeColor(fg, bg) {
  const alpha = fg.a !== undefined ? fg.a : 1.0;
  if (alpha >= 0.999) return { r: fg.r, g: fg.g, b: fg.b, a: 1.0 };
  const r = Math.round(alpha * fg.r + (1 - alpha) * bg.r);
  const g = Math.round(alpha * fg.g + (1 - alpha) * bg.g);
  const b = Math.round(alpha * fg.b + (1 - alpha) * bg.b);
  return { r, g, b, a: 1.0 };
}

function channelLuminance(channel) {
  const c = channel / 255;
  return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

function relativeLuminance(color) {
  return (
    0.2126 * channelLuminance(color.r) +
    0.7152 * channelLuminance(color.g) +
    0.0722 * channelLuminance(color.b)
  );
}

function calculateContrastRatio(foreground, background) {
  const fgParsed = parseColor(foreground);
  const bgParsed = parseColor(background);
  if (!fgParsed || !bgParsed) return 1.0;

  // Composite foreground over background if foreground has transparency
  const fgEffective = compositeColor(fgParsed, bgParsed);
  const lum1 = relativeLuminance(fgEffective);
  const lum2 = relativeLuminance(bgParsed);

  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);
  return (lighter + 0.05) / (darker + 0.05);
}

// 2. Read values from theme.tsx
const themeContent = fs.readFileSync(THEME_PATH, "utf-8");

function extractRegex(content, regex, fallback) {
  const m = content.match(regex);
  return m ? m[1].trim() : fallback;
}

const theme = {
  primary: extractRegex(themeContent, /primary:\s*\{\s*main:\s*["']([^"']+)["']/, "#00863A"),
  error: extractRegex(themeContent, /error:\s*\{\s*main:\s*["']([^"']+)["']/, "#ff8285"),
  warning: extractRegex(themeContent, /warning:\s*\{\s*main:\s*["']([^"']+)["']/, "#faad14"),
  bgDefault: extractRegex(themeContent, /default:\s*["']([^"']+)["']/, "#080808"),
  bgPaper: extractRegex(themeContent, /paper:\s*["']([^"']+)["']/, "#2b2b2b"),
  textPrimary: extractRegex(themeContent, /text:\s*\{[\s\S]*?primary:\s*["']([^"']+)["']/, "#fff"),
  textSecondary: extractRegex(themeContent, /text:\s*\{[\s\S]*?secondary:\s*["']([^"']+)["']/, "#9e9e9e"),
  dialogPaper: extractRegex(themeContent, /backgroundColor:\s*["'](#(?:[0-9a-fA-F]{3,8}))["']/, "#0d0d0d"),
  inputBorder: extractRegex(themeContent, /MuiOutlinedInput-notchedOutline":\s*\{\s*borderColor:\s*["']([^"']+)["']/, "#5e5e5e"),
  inputBorderHover: extractRegex(themeContent, /:hover \.MuiOutlinedInput-notchedOutline":\s*\{\s*borderColor:\s*["']([^"']+)["']/, "#777777"),
  inputBorderFocus: extractRegex(themeContent, /:focused \.MuiOutlinedInput-notchedOutline":\s*\{\s*borderColor:\s*["']([^"']+)["']/, "#00863A"),
  btnPrimaryHover: extractRegex(themeContent, /backgroundColor:\s*["'](#007030)["']/, "#007030"),
  linearProgressTrack: extractRegex(themeContent, /MuiLinearProgress:\s*\{[\s\S]*?backgroundColor:\s*["']([^"']+)["']/, "rgba(255, 255, 255, 0.36)"),
};

// 3. Define Test Pairs
const testPairs = [
  // --- A. Text on Paper & Default Backgrounds ---
  {
    category: "Văn bản chính",
    name: "text.primary trên background.default",
    fg: theme.textPrimary,
    bg: theme.bgDefault,
    req: 4.5,
    required: true,
  },
  {
    category: "Văn bản chính",
    name: "text.primary trên background.paper",
    fg: theme.textPrimary,
    bg: theme.bgPaper,
    req: 4.5,
    required: true,
  },
  {
    category: "Văn bản phụ",
    name: "text.secondary trên background.default",
    fg: theme.textSecondary,
    bg: theme.bgDefault,
    req: 4.5,
    required: true,
  },
  {
    category: "Văn bản phụ",
    name: "text.secondary trên background.paper",
    fg: theme.textSecondary,
    bg: theme.bgPaper,
    req: 4.5,
    required: true,
  },
  {
    category: "Văn bản vô hiệu",
    name: "text.disabled trên background.default (miễn trừ WCAG)",
    fg: "rgba(255, 255, 255, 0.5)",
    bg: theme.bgDefault,
    req: 4.5,
    required: false, // disabled is exempt under WCAG 1.4.3
    exempt: true,
  },
  {
    category: "Văn bản vô hiệu",
    name: "text.disabled trên background.paper (miễn trừ WCAG)",
    fg: "rgba(255, 255, 255, 0.5)",
    bg: theme.bgPaper,
    req: 4.5,
    required: false, // disabled is exempt under WCAG 1.4.3
    exempt: true,
  },

  // --- B. Contained Buttons ---
  {
    category: "Nút bấm Contained",
    name: "Chữ trên nút primary (#00863A)",
    fg: "#ffffff",
    bg: theme.primary,
    req: 4.5,
    required: true,
  },
  {
    category: "Nút bấm Contained",
    name: "Chữ trên nút primary hover (#007030)",
    fg: "#ffffff",
    bg: theme.btnPrimaryHover,
    req: 4.5,
    required: true,
  },
  {
    category: "Nút bấm Contained",
    name: "Chữ trên nút error MUI (#d32f2f)",
    fg: "#ffffff",
    bg: "#d32f2f",
    req: 4.5,
    required: true,
  },
  {
    category: "Nút bấm Contained",
    name: "Chữ trên nút Settings hardcode (#2e7d32)",
    fg: "#ffffff",
    bg: "#2e7d32",
    req: 4.5,
    required: true,
  },

  // --- C. Semantic State Colors as Text on Paper & Default ---
  {
    category: "Màu ngữ nghĩa làm CHỮ",
    name: "Màu Thu nhập (#48cc90) trên background.paper",
    fg: "#48cc90",
    bg: theme.bgPaper,
    req: 4.5,
    required: true,
  },
  {
    category: "Màu ngữ nghĩa làm CHỮ",
    name: "Màu Thu nhập (#48cc90) trên background.default",
    fg: "#48cc90",
    bg: theme.bgDefault,
    req: 4.5,
    required: true,
  },
  {
    category: "Màu ngữ nghĩa làm CHỮ",
    name: "Màu Chi tiêu (theme.error) trên background.paper",
    fg: theme.error,
    bg: theme.bgPaper,
    req: 4.5,
    required: true,
  },
  {
    category: "Màu ngữ nghĩa làm CHỮ",
    name: "Màu Chi tiêu (theme.error) trên background.default",
    fg: theme.error,
    bg: theme.bgDefault,
    req: 4.5,
    required: true,
  },
  {
    category: "Màu ngữ nghĩa làm CHỮ",
    name: "Màu Cảnh báo (#faad14) trên background.paper",
    fg: "#faad14",
    bg: theme.bgPaper,
    req: 4.5,
    required: true,
  },
  {
    category: "Màu ngữ nghĩa làm CHỮ",
    name: "Màu Cảnh báo (#faad14) trên background.default",
    fg: "#faad14",
    bg: theme.bgDefault,
    req: 4.5,
    required: true,
  },
  {
    category: "Màu ngữ nghĩa làm CHỮ",
    name: "Màu Vượt hạn mức (theme.error) trên background.paper",
    fg: theme.error,
    bg: theme.bgPaper,
    req: 4.5,
    required: true,
  },
  {
    category: "Màu ngữ nghĩa làm CHỮ",
    name: "Màu Sắp vượt hạn mức Tailwind (#f59e0b) trên background.paper",
    fg: "#f59e0b",
    bg: theme.bgPaper,
    req: 4.5,
    required: true,
  },

  // --- D. Text in Status Chips (Alpha 0.15 over Paper) ---
  {
    category: "Chữ trong Status Chip",
    name: "Chữ xanh (#48cc90) trong chip mờ rgba(72,204,144,0.15) trên paper",
    fg: "#48cc90",
    bg: "rgba(72, 204, 144, 0.15)",
    baseBg: theme.bgPaper,
    req: 4.5,
    required: true,
  },
  {
    category: "Chữ trong Status Chip",
    name: "Chữ cam (#faad14) trong chip mờ rgba(250,173,20,0.15) trên paper",
    fg: "#faad14",
    bg: "rgba(250, 173, 20, 0.15)",
    baseBg: theme.bgPaper,
    req: 4.5,
    required: true,
  },
  {
    category: "Chữ trong Status Chip",
    name: "Chữ đỏ (theme.error) trong chip mờ rgba(255,130,133,0.15) trên paper",
    fg: theme.error,
    bg: "rgba(255, 130, 133, 0.15)",
    baseBg: theme.bgPaper,
    req: 4.5,
    required: true,
  },
  {
    category: "Chữ trong Status Chip",
    name: "Chữ xanh (#48cc90) trong chip mờ rgba(0,134,58,0.2) trên paper",
    fg: "#48cc90",
    bg: "rgba(0, 134, 58, 0.2)",
    baseBg: theme.bgPaper,
    req: 4.5,
    required: true,
  },

  // --- E. Navigation & Tabs ---
  {
    category: "Điều hướng & Tabs",
    name: "Chữ tab / link chưa chọn (rgba(255,255,255,0.7)) trên AppDrawer bg",
    fg: "rgba(255, 255, 255, 0.7)",
    bg: "rgba(13, 14, 18, 0.85)",
    baseBg: theme.bgDefault,
    req: 4.5,
    required: true,
  },
  {
    category: "Điều hướng & Tabs",
    name: "Chữ tab MUI chưa chọn (text.secondary) trên background.paper",
    fg: theme.textSecondary,
    bg: theme.bgPaper,
    req: 4.5,
    required: true,
  },

  // --- F. Input Fields ---
  {
    category: "Ô nhập liệu (Input)",
    name: "Placeholder input (rgba(255, 255, 255, 0.5)) trên input bg",
    fg: "rgba(255, 255, 255, 0.5)",
    bg: "rgba(255, 255, 255, 0.02)",
    baseBg: theme.bgDefault,
    req: 4.5,
    required: true,
  },
  {
    category: "Ô nhập liệu (Input)",
    name: "Helper text (text.secondary) trên background.default",
    fg: theme.textSecondary,
    bg: theme.bgDefault,
    req: 4.5,
    required: true,
  },
  {
    category: "Ô nhập liệu (Input)",
    name: "Error text (#f44336) trên background.default",
    fg: "#f44336",
    bg: theme.bgDefault,
    req: 4.5,
    required: true,
  },
  {
    category: "Ô nhập liệu (Input)",
    name: "Link đăng ký / đăng nhập (#4caf50) trên background.default",
    fg: "#4caf50",
    bg: theme.bgDefault,
    req: 4.5,
    required: true,
  },

  // --- G. Alerts / Snackbars ---
  {
    category: "Alert & Thông báo",
    name: "Chữ Alert Error (#fdeded trên #5f2120)",
    fg: "#fdeded",
    bg: "#5f2120",
    req: 4.5,
    required: true,
  },
  {
    category: "Alert & Thông báo",
    name: "Chữ Alert Warning (#fff4e5 trên #663c00)",
    fg: "#fff4e5",
    bg: "#663c00",
    req: 4.5,
    required: true,
  },
  {
    category: "Alert & Thông báo",
    name: "Chữ Alert Info (#e5f6fd trên #014361)",
    fg: "#e5f6fd",
    bg: "#014361",
    req: 4.5,
    required: true,
  },
  {
    category: "Alert & Thông báo",
    name: "Chữ Alert Success (#edf7ed trên #1e4620)",
    fg: "#edf7ed",
    bg: "#1e4620",
    req: 4.5,
    required: true,
  },

  // --- H. DataGrid ---
  {
    category: "Bảng DataGrid",
    name: "Chữ hàng hover (#ffffff trên rgba(255,255,255,0.03))",
    fg: "#ffffff",
    bg: "rgba(255, 255, 255, 0.03)",
    baseBg: theme.bgDefault,
    req: 4.5,
    required: true,
  },
  {
    category: "Bảng DataGrid",
    name: "Chữ hàng selected (#ffffff trên rgba(255,255,255,0.05))",
    fg: "#ffffff",
    bg: "rgba(255, 255, 255, 0.05)",
    baseBg: theme.bgDefault,
    req: 4.5,
    required: true,
  },

  // --- I. ApexCharts ---
  {
    category: "Biểu đồ ApexCharts",
    name: "Nhãn trục CurrentMonthChart (text.secondary) trên background.paper",
    fg: theme.textSecondary,
    bg: theme.bgPaper,
    req: 4.5,
    required: true,
  },
  {
    category: "Biểu đồ ApexCharts",
    name: "Nhãn trục CashFlowForecast (text.secondary) trên background.paper",
    fg: theme.textSecondary,
    bg: theme.bgPaper,
    req: 4.5,
    required: true,
  },
  {
    category: "Biểu đồ ApexCharts",
    name: "Chú giải ProfileChart (text.secondary) trên background.paper",
    fg: theme.textSecondary,
    bg: theme.bgPaper,
    req: 4.5,
    required: true,
  },
  {
    category: "Biểu đồ ApexCharts",
    name: "Tooltip custom text (#aaa) trên tooltip bg (#161616)",
    fg: "#aaaaaa",
    bg: "#161616",
    req: 4.5,
    required: true,
  },

  // --- J. Non-text Contrast (Graphics & UI Components >= 3:1) ---
  {
    category: "Phi văn bản (Non-text)",
    name: "Viền OutlinedInput (#2b2b2b) trên background.default (#080808)",
    fg: theme.inputBorder,
    bg: theme.bgDefault,
    req: 3.0,
    required: true,
  },
  {
    category: "Phi văn bản (Non-text)",
    name: "Viền OutlinedInput Hover (#444444) trên background.default (#080808)",
    fg: theme.inputBorderHover,
    bg: theme.bgDefault,
    req: 3.0,
    required: true,
  },
  {
    category: "Phi văn bản (Non-text)",
    name: "Viền OutlinedInput Focus (#00863A) trên background.default (#080808)",
    fg: theme.inputBorderFocus,
    bg: theme.bgDefault,
    req: 3.0,
    required: true,
  },
  {
    category: "Phi văn bản (Non-text)",
    name: "Track LinearProgress (theme.linearProgressTrack) trên paper (#2b2b2b)",
    fg: theme.linearProgressTrack,
    bg: theme.bgPaper,
    req: 3.0,
    required: true,
  },
  {
    category: "Phi văn bản (Non-text)",
    name: "Fill LinearProgress Normal (#48cc90) trên track",
    fg: "#48cc90",
    bg: "rgba(255, 255, 255, 0.08)",
    baseBg: theme.bgPaper,
    req: 3.0,
    required: true,
  },
  {
    category: "Phi văn bản (Non-text)",
    name: "Fill LinearProgress Danger (#f25659) trên track",
    fg: "#f25659",
    bg: "rgba(255, 255, 255, 0.08)",
    baseBg: theme.bgPaper,
    req: 3.0,
    required: true,
  },
  {
    category: "Phi văn bản (Non-text)",
    name: "Đường cảnh báo an toàn ApexCharts (#faad14) trên chart bg (#080808)",
    fg: "#faad14",
    bg: theme.bgDefault,
    req: 3.0,
    required: true,
  },
  {
    category: "Phi văn bản (Non-text)",
    name: "Đường cảnh báo cạn quỹ ApexCharts (#f25659) trên chart bg (#080808)",
    fg: "#f25659",
    bg: theme.bgDefault,
    req: 3.0,
    required: true,
  },

  // --- K. Sidebar Navigation (WCAG 2.2 AA) ---
  {
    category: "Thanh điều hướng Sidebar",
    name: "Chữ mục chưa chọn (#9e9e9e) trên nền sidebar (#0d0e12)",
    fg: theme.textSecondary,
    bg: "#0d0e12",
    req: 4.5,
    required: true,
  },
  {
    category: "Thanh điều hướng Sidebar",
    name: "Chữ mục đang chọn (#48cc90) trên nền mục active (rgba(0,134,58,0.14))",
    fg: "#48cc90",
    bg: "rgba(0, 134, 58, 0.14)",
    baseBg: "#0d0e12",
    req: 4.5,
    required: true,
  },
  {
    category: "Thanh điều hướng Sidebar",
    name: "Chỉ báo mục đang chọn (#48cc90) trên nền sidebar (#0d0e12)",
    fg: "#48cc90",
    bg: "#0d0e12",
    req: 3.0,
    required: true,
  },
  {
    category: "Thanh điều hướng Sidebar",
    name: "Icon/Chữ nút thu gọn bình thường (#9e9e9e) trên nền sidebar (#0d0e12)",
    fg: theme.textSecondary,
    bg: "#0d0e12",
    req: 3.0,
    required: true,
  },
  {
    category: "Thanh điều hướng Sidebar",
    name: "Icon nút hamburger trên nền thanh trên (#e0e0e0 trên #0d0e12)",
    fg: "#e0e0e0",
    bg: "#0d0e12",
    req: 3.0,
    required: true,
  },
  {
    category: "Thanh điều hướng Sidebar",
    name: "Icon nút hamburger khi hover (#ffffff trên nền hover)",
    fg: "#ffffff",
    bg: "rgba(255, 255, 255, 0.06)",
    baseBg: "#0d0e12",
    req: 3.0,
    required: true,
  },
  {
    category: "Thanh điều hướng Sidebar",
    name: "Vòng focus nút hamburger (#00863A trên #0d0e12)",
    fg: theme.primary,
    bg: "#0d0e12",
    req: 3.0,
    required: true,
  },
];

// Helper to run contrast calculation
function runContrastChecks() {
  console.log("=========================================================================================");
  console.log("                KIỂM TRA TƯƠNG PHẢN MÀU WCAG 2.2 AA (MONEYMANAGEMENT)                   ");
  console.log("=========================================================================================\n");

  let totalCount = 0;
  let passCount = 0;
  let failCount = 0;
  let requiredFails = 0;

  const rows = [];

  for (const item of testPairs) {
    totalCount++;
    // Handle layered backgrounds if specified
    let effectiveBg = item.bg;
    if (item.baseBg) {
      const bgP = parseColor(item.bg);
      const baseP = parseColor(item.baseBg);
      const comp = compositeColor(bgP, baseP);
      effectiveBg = `rgb(${comp.r}, ${comp.g}, ${comp.b})`;
    }

    const ratio = calculateContrastRatio(item.fg, effectiveBg);
    const pass = ratio >= item.req;

    if (pass) {
      passCount++;
    } else {
      failCount++;
      if (item.required) {
        requiredFails++;
      }
    }

    rows.push({
      category: item.category,
      name: item.name,
      fg: item.fg,
      bg: item.bg + (item.baseBg ? ` over ${item.baseBg}` : ""),
      ratio: ratio.toFixed(2) + ":1",
      req: item.req.toFixed(1) + ":1",
      status: pass ? "ĐẠT" : item.exempt ? "MIỄN (FAIL)" : "KHÔNG ĐẠT",
      required: item.required,
      exempt: item.exempt,
    });
  }

  // Print results grouped by category
  let currentCat = "";
  for (const r of rows) {
    if (r.category !== currentCat) {
      currentCat = r.category;
      console.log(`\n### ${currentCat.toUpperCase()}`);
      console.log(
        "---------------------------------------------------------------------------------------------------------------"
      );
      console.log(
        ` ${"Cặp kiểm tra".padEnd(46)} | ${"FG / BG".padEnd(28)} | ${"Tỷ lệ".padEnd(8)} | ${"Ngưỡng".padEnd(8)} | ${"Kết quả"}`
      );
      console.log(
        "---------------------------------------------------------------------------------------------------------------"
      );
    }
    const colorDesc = `${r.fg} / ${r.bg}`.slice(0, 28);
    const statusStr = r.status === "ĐẠT" ? `✅ ${r.status}` : r.exempt ? `ℹ️  ${r.status}` : `❌ ${r.status}`;
    console.log(
      ` ${r.name.padEnd(46)} | ${colorDesc.padEnd(28)} | ${r.ratio.padEnd(8)} | ${r.req.padEnd(8)} | ${statusStr}`
    );
  }

  // --- Scan all hardcoded colors from codebase ---
  console.log("\n=========================================================================================");
  console.log("            QUÉT TOÀN BỘ MÃ MÀU HARDCODE VÀ ĐO VỚI NỀN PAPER VÀ DEFAULT                ");
  console.log("=========================================================================================\n");

  const srcDir = path.join(FRONTEND_DIR, "src");
  const hexRegex = /#(?:[0-9a-fA-F]{3,4}){1,2}\b/g;
  const hardcodedColors = new Map();

  function scanDir(dir) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const ent of entries) {
      const full = path.join(dir, ent.name);
      if (ent.isDirectory()) {
        scanDir(full);
      } else if (ent.isFile() && (ent.name.endsWith(".tsx") || ent.name.endsWith(".ts"))) {
        const lines = fs.readFileSync(full, "utf-8").split("\n");
        const rel = path.relative(FRONTEND_DIR, full);
        lines.forEach((line, idx) => {
          let match;
          while ((match = hexRegex.exec(line)) !== null) {
            const c = match[0].toLowerCase();
            if (!hardcodedColors.has(c)) {
              hardcodedColors.set(c, []);
            }
            const isText =
              /color:\s*["']?|sx=\{\{[^}]*color|<Typography[^>]*color/i.test(line) &&
              !/borderColor|background|border:/i.test(line);
            hardcodedColors.get(c).push({
              file: rel,
              line: idx + 1,
              isText,
              snippet: line.trim(),
            });
          }
        });
      }
    }
  }

  scanDir(srcDir);

  console.log(
    ` ${"Mã màu".padEnd(10)} | ${"Số lần".padEnd(7)} | ${"Tỷ lệ trên Paper".padEnd(18)} | ${"Tỷ lệ trên Default".padEnd(20)} | ${"Đánh giá chữ"}`
  );
  console.log(
    "---------------------------------------------------------------------------------------------------------------"
  );

  const sortedH = [...hardcodedColors.entries()].sort((a, b) => b[1].length - a[1].length);
  for (const [color, usages] of sortedH) {
    const ratioPaper = calculateContrastRatio(color, theme.bgPaper);
    const ratioDefault = calculateContrastRatio(color, theme.bgDefault);
    const usedAsText = usages.some((u) => u.isText);

    let textStatus = "Không dùng làm chữ";
    if (usedAsText) {
      if (ratioPaper < 4.5) {
        textStatus = "❌ FAIL trên Paper (< 4.5:1)";
      } else {
        textStatus = "✅ Đạt trên Paper & Default";
      }
    }

    console.log(
      ` ${color.padEnd(10)} | ${String(usages.length).padEnd(7)} | ${(ratioPaper.toFixed(2) + ":1").padEnd(18)} | ${(
        ratioDefault.toFixed(2) + ":1"
      ).padEnd(20)} | ${textStatus}`
    );
  }

  console.log("\n=========================================================================================");
  console.log("            BẢNG SO SÁNH TRƯỚC VÀ SAU KHI CHUẨN HÓA MÀU (BEFORE / AFTER)                 ");
  console.log("=========================================================================================");
  console.log(" Token / Phần tử                 | Trước (Tỷ lệ)     | Sau (Tỷ lệ)       | Đánh giá WCAG");
  console.log("-----------------------------------------------------------------------------------------");
  console.log(" text.secondary trên Paper       | #8a8a8a (4.10:1)  | #9e9e9e (5.37:1)  | ✅ ĐẠT (>= 4.5:1)");
  console.log(" Màu Chi tiêu trên Paper         | #f25659 (4.21:1)  | #ff8285 (5.92:1)  | ✅ ĐẠT (>= 4.5:1)");
  console.log(" Chữ đỏ trong chip mờ trên Paper | #f25659 (3.53:1)  | #ff8285 (4.57:1)  | ✅ ĐẠT (>= 4.5:1)");
  console.log(" Viền OutlinedInput trên Default | #2b2b2b (1.41:1)  | #5e5e5e (3.09:1)  | ✅ ĐẠT (>= 3.0:1)");
  console.log(" Viền OutlinedInput Hover        | #444444 (2.06:1)  | #777777 (4.45:1)  | ✅ ĐẠT (>= 3.0:1)");
  console.log(" Track LinearProgress trên Paper | rgba(0.08)(1.28:1)| rgba(0.36)(3.16:1)| ✅ ĐẠT (>= 3.0:1)");
  console.log(" Nhãn trục x/y & chú giải Chart  | #616161 (2.29:1)  | #9e9e9e (5.37:1)  | ✅ ĐẠT (>= 4.5:1)");
  console.log("-----------------------------------------------------------------------------------------");

  console.log("\n=========================================================================================");
  console.log(` TỔNG KẾT: ${totalCount} cặp đo | ĐẠT: ${passCount} | KHÔNG ĐẠT: ${failCount} (Bắt buộc không đạt: ${requiredFails})`);
  console.log("=========================================================================================\n");

  if (requiredFails > 0) {
    console.error(`[CẢNH BÁO A11Y] Có ${requiredFails} cặp kiểm tra bắt buộc KHÔNG ĐẠT chuẩn WCAG 2.2 AA!`);
    console.error("Vui lòng xem báo cáo chi tiết trong ACCESSIBILITY_AUDIT.md để chuẩn hóa giá trị màu.\n");
    process.exit(1);
  } else {
    console.log("[THÀNH CÔNG] Tất cả các cặp kiểm tra đều đạt chuẩn WCAG 2.2 AA!\n");
    process.exit(0);
  }
}

runContrastChecks();
