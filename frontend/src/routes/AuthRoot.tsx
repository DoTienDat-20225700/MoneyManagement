import { Box, Button, Typography } from "@mui/material";
import { Outlet } from "react-router-dom";
import { useLanguage } from "../context/LanguageContext";
import { paletteTokens } from "../theme";

function AuthRoot() {
  const { language, toggleLanguage } = useLanguage();
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
            component="div"
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
          position: "relative",
        }}
      >
        <Box sx={{ position: "absolute", top: 24, right: 32 }}>
          <Button
            onClick={toggleLanguage}
            variant="outlined"
            size="small"
            sx={{
              height: 34,
              px: 1.5,
              borderRadius: "20px",
              color: "#fff",
              borderColor: "rgba(255, 255, 255, 0.2)",
              background: "rgba(255, 255, 255, 0.05)",
              backdropFilter: "blur(8px)",
              fontSize: "13px",
              fontWeight: 600,
              letterSpacing: 0.5,
              textTransform: "none",
              transition: "all 0.25s ease",
              "&:hover": {
                borderColor: paletteTokens.primary,
                background: paletteTokens.tint.primary12,
              },
            }}
          >
            {language === "vi" ? "🇻🇳 VI" : "🇺🇸 EN"}
          </Button>
        </Box>
        <Outlet />
      </Box>
    </Box>
  );
}

export default AuthRoot;
