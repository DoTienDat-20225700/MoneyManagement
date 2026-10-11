import { Box, Toolbar } from "@mui/material";
import AppDrawer from "../components/AppDrawer";
import RequireAuth from "../components/auth/RequireAuth";

function Root() {
  return (
    <Box
      sx={{
        minHeight: "100vh",
        position: "relative",
        overflowX: "hidden",
        backgroundColor: "#0d0e12",
      }}
    >
      {/* Blurred background image layer after login */}
      <Box
        sx={{
          position: "fixed",
          inset: "-20px",
          backgroundImage: "url('/dashboard-bg.jpg')",
          backgroundSize: "cover",
          backgroundPosition: "center top",
          backgroundRepeat: "no-repeat",
          filter: "blur(12px)",
          transform: "scale(1.05)",
          opacity: 0.9,
          zIndex: 0,
          pointerEvents: "none",
        }}
      />

      {/* Dark gradient overlay for contrast and readability */}
      <Box
        sx={{
          position: "fixed",
          inset: 0,
          background:
            "linear-gradient(180deg, rgba(13, 14, 18, 0.75) 0%, rgba(13, 14, 18, 0.94) 100%)",
          zIndex: 0,
          pointerEvents: "none",
        }}
      />

      {/* Main content layer */}
      <Box sx={{ position: "relative", zIndex: 1, display: "flex", minHeight: "100vh" }}>
        <AppDrawer />
        <Box
          component="main"
          sx={{
            p: { xs: 2.5, sm: 4, md: 5 },
            width: "100%",
            maxWidth: "1600px",
            mx: "auto",
          }}
        >
          <Toolbar />
          <RequireAuth />
        </Box>
      </Box>
    </Box>
  );
}

export default Root;
