import { CssBaseline, ThemeProvider } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SnackbarProvider } from "notistack";
import { RouterProvider } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { LanguageProvider } from "./context/LanguageContext";
import { router } from "./main";
import { darkTheme } from "./theme";

function App() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: Infinity,
      },
    },
  });

  return (
    // <React.StrictMode>
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <QueryClientProvider client={queryClient}>
        <SnackbarProvider maxSnack={3}>
          <LanguageProvider>
            <AuthProvider>
              <RouterProvider router={router} />
            </AuthProvider>
          </LanguageProvider>
        </SnackbarProvider>
      </QueryClientProvider>
    </ThemeProvider>
    // </React.StrictMode>
  );
}

export default App;
