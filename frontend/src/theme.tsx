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
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          backgroundColor: "#121316",
          backgroundImage: "none",
          borderRadius: 12,
          border: "1px solid rgba(255, 255, 255, 0.1)",
          boxShadow: "0 16px 48px rgba(0, 0, 0, 0.7)",
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
