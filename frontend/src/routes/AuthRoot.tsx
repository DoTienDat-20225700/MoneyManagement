import { Box, Typography } from "@mui/material";
import { grey } from "@mui/material/colors";
import { Outlet } from "react-router-dom";
function AuthRoot() {
  return (
    <Box
      sx={{ display: "flex", justifyContent: "space-between", height: "100vh" }}
    >
      <Box
        sx={{
          flex: 1,
          position: "relative",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          height: "100%",
        }}
      >
        {/* Background image layer with blur and overlay */}
        <Box
          sx={{
            position: "absolute",
            inset: -15,
            backgroundImage: "url('/auth-bg.png')",
            backgroundSize: "cover",
            backgroundPosition: "center",
            filter: "blur(8px)",
            transform: "scale(1.08)",
            zIndex: 0,
          }}
        />
        <Box
          sx={{
            position: "absolute",
            inset: 0,
            backgroundColor: "rgba(18, 18, 18, 0.65)",
            zIndex: 1,
          }}
        />

        <Box
          sx={{
            position: "relative",
            zIndex: 2,
            p: 5,
            display: "flex",
            alignItems: "center",
            gap: 1.5,
          }}
        >
          <Box
            component="img"
            src="/logo.png"
            alt="MoneyManager Logo"
            sx={{
              width: 38,
              height: 38,
              objectFit: "contain",
              filter: "drop-shadow(0 2px 6px rgba(0,0,0,0.5))",
            }}
          />
          <Typography
            variant="h6"
            component="h1"
            fontWeight={700}
            sx={{
              color: "#ffffff",
              letterSpacing: "0.5px",
              textShadow: "0 2px 4px rgba(0,0,0,0.6)",
            }}
          >
            MoneyManager
          </Typography>
        </Box>
      </Box>
      <Box
        sx={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <Outlet />
      </Box>
    </Box>
  );
}

export default AuthRoot;
