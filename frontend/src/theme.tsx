import "@fontsource/inter";
import { Components, createTheme, PaletteOptions } from "@mui/material";
import { TypographyOptions } from "@mui/material/styles/createTypography";

export const semanticColors = {
  income: "#48cc90",
  expense: "#ff8285",
  warning: "#faad14",
  info: "#3b82f6",
};

export const darkTheme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#00863A",
    },
    error: {
      main: "#ff8285",
    },
    warning: {
      main: "#faad14",
    },
    background: {
      default: "#080808", //background
      paper: "#2b2b2b", //borders and dividers
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
          backgroundColor: "#0d0d0d",
          backgroundImage: "none",
          borderRadius: 14,
          border: "1px solid #2b2b2b",
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
          border: `1px solid #2b2b2b`,
          "& .MuiDataGrid-withBorderColor": {
            borderColor: "#2b2b2b",
          },
        },
      },
    },
  } as Components,
});
