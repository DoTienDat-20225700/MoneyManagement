import "@fontsource/inter";
import { Components, createTheme, PaletteOptions } from "@mui/material";
import { TypographyOptions } from "@mui/material/styles/createTypography";

export const darkTheme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#00863A",
    },
    background: {
      default: "#080808", //background
      paper: "#2b2b2b", //borders and dividers
    },
    text: {
      primary: "#fff",
      secondary: "#8a8a8a",
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
        },
        containedPrimary: {
          backgroundColor: "#00863A",
          "&:hover": {
            backgroundColor: "#007030",
          },
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
            borderColor: "#2b2b2b",
          },
          "&:hover .MuiOutlinedInput-notchedOutline": {
            borderColor: "#444444",
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
          color: "#8a8a8a",
          "&.Mui-checked": {
            color: "#00863A",
          },
        },
      },
    },
    MuiCheckbox: {
      styleOverrides: {
        root: {
          color: "#8a8a8a",
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
