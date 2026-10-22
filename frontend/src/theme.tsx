import "@fontsource/inter";
import { Components, createTheme, PaletteOptions } from "@mui/material";
import { TypographyOptions } from "@mui/material/styles/createTypography";

export const semanticColors = {
  income: "#48cc90",
  expense: "#ff8285",
  warning: "#faad14",
  info: "#9e9e9e",
};

export const paletteTokens = {
  primary: "#00863A",
  primaryHover: "#007030",
  primaryContrastText: "#ffffff",
  success: "#48cc90",
  income: "#48cc90",
  error: "#ff8285",
  expense: "#ff8285",
  warning: "#faad14",
  info: "#9e9e9e",
  bgDefault: "#080808",
  bgPaper: "#1E1E1E",
  bgCard: "#121212",
  elevated: "#121212",
  bgSidebar: "#0d0e12",
  divider: "#1E1E1E",
  controlBorder: "#5e5e5e",
  textPrimary: "#ffffff",
  textSecondary: "#9e9e9e",
  tint: {
    primary12: "rgba(0, 134, 58, 0.12)",
    success12: "rgba(72, 204, 144, 0.12)",
    error12: "rgba(255, 130, 133, 0.12)",
    warning12: "rgba(250, 173, 20, 0.12)",
    info12: "rgba(158, 158, 158, 0.12)",
  },
  chart: {
    colors: ["#60A5FA", "#A78BFA", "#22D3EE", "#F472B6", "#94A3B8"],
    neutral: "#6B7280",
    other: "#6B7280",
    expense: "#ff8285",
  },
};

export type SeverityLevel = "ok" | "warning" | "danger" | "neutral";
export type BudgetStatus = "normal" | "approaching" | "exceeded";

export function getStatusColorsBySeverity(level: SeverityLevel) {
  switch (level) {
    case "danger":
      return {
        color: paletteTokens.error,
        bg: paletteTokens.tint.error12,
        progressColor: paletteTokens.error,
      };
    case "warning":
      return {
        color: paletteTokens.warning,
        bg: paletteTokens.tint.warning12,
        progressColor: paletteTokens.warning,
      };
    case "ok":
      return {
        color: paletteTokens.success,
        bg: paletteTokens.tint.success12,
        progressColor: paletteTokens.success,
      };
    case "neutral":
    default:
      return {
        color: paletteTokens.textSecondary,
        bg: "rgba(255, 255, 255, 0.05)",
        progressColor: paletteTokens.textSecondary,
      };
  }
}

export function mapBudgetSeverity(status: BudgetStatus): SeverityLevel {
  if (status === "exceeded") return "danger";
  if (status === "approaching") return "warning";
  return "ok";
}

export function mapDebtSeverity(status: string): SeverityLevel {
  const s = status.toUpperCase();
  if (s === "OVERDUE") return "danger";
  if (s === "DUE_SOON" || s === "DUE_7_DAYS") return "warning";
  return "neutral";
}

export function mapForecastSeverity(risk: string): SeverityLevel {
  const r = risk.toUpperCase();
  if (r === "CRITICAL") return "danger";
  if (r === "WARNING") return "warning";
  return "ok";
}

export function statusColors(status: BudgetStatus) {
  return getStatusColorsBySeverity(mapBudgetSeverity(status));
}

export const darkTheme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#00863A",
    },
    success: {
      main: "#00863A",
      light: "#48cc90",
      contrastText: "#ffffff",
    },
    error: {
      main: "#ff8285",
    },
    warning: {
      main: "#faad14",
    },
    info: {
      main: "#9e9e9e",
      light: "#b0b0b0",
      dark: "#757575",
      contrastText: "#080808",
    },
    background: {
      default: "#080808", //background
      paper: "#1E1E1E", //borders and dividers
    },
    text: {
      primary: "#fff",
      secondary: "#9e9e9e",
    },
  } as PaletteOptions,
  typography: {
    fontFamily: ["Inter", "sans-serif"].join(","),
  } as TypographyOptions,
  components: {
    MuiButton: {
      defaultProps: {
        disableRipple: true,
      },
      styleOverrides: {
        root: {
          boxShadow: "none",
          textTransform: "none",
          borderRadius: 8,
          fontWeight: 600,
          "&.Mui-focusVisible": {
            outline: "2px solid #00863A",
            outlineOffset: 2,
          },
        },
        containedPrimary: {
          backgroundColor: "#00863A",
          "&:hover": {
            backgroundColor: "#007030",
          },
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          "&.Mui-focusVisible": {
            outline: "2px solid #00863A",
            outlineOffset: 2,
          },
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          backgroundColor: "rgba(255, 255, 255, 0.36)",
          borderRadius: 4,
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          backgroundColor: paletteTokens.bgCard,
          backgroundImage: "none",
          borderRadius: 14,
          border: `1px solid ${paletteTokens.divider}`,
          boxShadow: "0 24px 64px rgba(0, 0, 0, 0.85)",
        },
      },
    },
    MuiDialogTitle: {
      styleOverrides: {
        root: {
          fontSize: "1.25rem",
          fontWeight: 600,
          color: "#ffffff",
          padding: "20px 24px 8px 24px",
        },
      },
    },
    MuiDialogContent: {
      styleOverrides: {
        root: {
          padding: "8px 24px 20px 24px",
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          backgroundColor: "rgba(255, 255, 255, 0.02)",
          "& .MuiOutlinedInput-notchedOutline": {
            borderColor: "#5e5e5e",
          },
          "&:hover .MuiOutlinedInput-notchedOutline": {
            borderColor: "#777777",
          },
          "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
            borderColor: "#00863A",
          },
        },
      },
    },
    MuiRadio: {
      styleOverrides: {
        root: {
          color: "#9e9e9e",
          "&.Mui-checked": {
            color: "#00863A",
          },
        },
      },
    },
    MuiCheckbox: {
      styleOverrides: {
        root: {
          color: "#9e9e9e",
          "&.Mui-checked": {
            color: "#00863A",
          },
        },
      },
    },
    MuiDataGrid: {
      styleOverrides: {
        root: {
          border: `1px solid ${paletteTokens.divider}`,
          "& .MuiDataGrid-withBorderColor": {
            borderColor: paletteTokens.divider,
          },
        },
      },
    },
  } as Components,
});
