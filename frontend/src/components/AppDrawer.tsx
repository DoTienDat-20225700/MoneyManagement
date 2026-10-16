import * as React from "react";
import List from "@mui/material/List";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import MenuIcon from "@mui/icons-material/Menu";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import TranslateIcon from "@mui/icons-material/Translate";
import { AppBar, Box, Button, Drawer, Toolbar, Typography } from "@mui/material";
import { Link, useLocation } from "react-router-dom";
import { darkTheme } from "../theme";
import { navigation } from "../navigation";
import UserDropdown from "./UserDropdown";
import { useLanguage } from "../context/LanguageContext";

const drawerWidth = 260;
interface Props {
  window?: () => Window;
}

export default function DrawerAppBar(props: Props) {
  const { window } = props;
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const location = useLocation();
  const { language, toggleLanguage, t } = useLanguage();

  const handleDrawerToggle = () => {
    setMobileOpen((prevState) => !prevState);
  };

  const getNavLabel = (path: string) => {
    if (path === "/") return t("dashboard");
    if (path === "/transactions") return t("transactions");
    if (path === "/budgets") return t("budgets");
    if (path === "/reports") return t("reports");
    if (path === "/saving-plans") return t("saving_plans");
    if (path === "/debts") return t("debts");
    return path;

  };

  const drawer = (
    <Box
      onClick={handleDrawerToggle}
      sx={{
        textAlign: "center",
        background: darkTheme.palette.background.default,
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Box
        component={Link}
        to="/"
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 1.2,
          my: 2.5,
          textDecoration: "none",
          color: "inherit",
        }}
      >
        <Box
          component="img"
          src="/logo.png"
          alt="MoneyManager Logo"
          sx={{ width: 28, height: 28, objectFit: "contain" }}
        />
        <Typography variant="h6" fontWeight={700} color="#fff">
          MoneyManager
        </Typography>
      </Box>
      <Divider sx={{ borderColor: "rgba(255,255,255,0.08)" }} />
      <List sx={{ px: 1, py: 2 }}>
        {navigation.map((item) => {
          const isActive =
            item.path === "/"
              ? location.pathname === "/"
              : location.pathname.startsWith(item.path);
          return (
            <ListItem key={item.path} disablePadding sx={{ mb: 1 }}>
              <ListItemButton
                component={Link}
                to={item.path}
                sx={{
                  borderRadius: 2,
                  backgroundColor: isActive
                    ? "rgba(0, 134, 58, 0.22)"
                    : "transparent",
                  color: isActive ? "#48cc90" : "#e0e0e0",
                  border: isActive
                    ? "1px solid rgba(72, 204, 144, 0.35)"
                    : "1px solid transparent",
                  "&:hover": {
                    backgroundColor: "rgba(255,255,255,0.06)",
                  },
                }}
              >
                <ListItemIcon sx={{ color: "inherit", minWidth: 38 }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={getNavLabel(item.path)}
                  primaryTypographyProps={{ fontWeight: isActive ? 600 : 500 }}
                />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>
      <Box sx={{ mt: "auto", p: 2 }}>
        <Button
          fullWidth
          variant="outlined"
          size="small"
          onClick={(e) => {
            e.stopPropagation();
            toggleLanguage();
          }}
          startIcon={<TranslateIcon fontSize="small" />}
          sx={{
            py: 1,
            borderRadius: 2,
            borderColor: "rgba(255,255,255,0.2)",
            color: "#fff",
          }}
        >
          {language === "vi" ? "🇻🇳 Tiếng Việt" : "🇬🇧 English"}
        </Button>
      </Box>
    </Box>
  );

  const container =
    window !== undefined ? () => window().document.body : undefined;

  return (
    <Box sx={{ display: "flex" }}>
      <AppBar
        component="nav"
        sx={{
          background: "rgba(13, 14, 18, 0.85)",
          backdropFilter: "blur(14px)",
          borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
          boxShadow: "0 4px 20px rgba(0, 0, 0, 0.35)",
        }}
      >
        <Toolbar
          sx={{
            px: { xs: 2, sm: 3, md: 4 },
            display: "flex",
            justifyContent: "space-between",
          }}
        >
          {/* Left section: Logo + Divider + Navigation links */}
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
            }}
          >
            <IconButton
              color="inherit"
              aria-label="open drawer"
              edge="start"
              onClick={handleDrawerToggle}
              sx={{ mr: 2, display: { sm: "none" } }}
            >
              <MenuIcon />
            </IconButton>

            {/* Brand Logo */}
            <Box
              component={Link}
              to="/"
              sx={{
                display: { xs: "none", sm: "flex" },
                alignItems: "center",
                gap: 1.2,
                textDecoration: "none",
                color: "inherit",
                cursor: "pointer",
                "&:hover": { opacity: 0.9 },
              }}
            >
              <Box
                component="img"
                src="/logo.png"
                alt="MoneyManager Logo"
                sx={{ width: 28, height: 28, objectFit: "contain" }}
              />
              <Typography
                variant="h6"
                fontWeight={700}
                sx={{
                  background: "linear-gradient(90deg, #ffffff 0%, #a5d6a7 100%)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  letterSpacing: 0.3,
                }}
              >
                MoneyManager
              </Typography>
            </Box>

            {/* Separator Divider */}
            <Box
              sx={{
                display: { xs: "none", sm: "block" },
                width: "1px",
                height: "22px",
                bgcolor: "rgba(255, 255, 255, 0.18)",
                mx: { sm: 2.5, md: 3.5 },
              }}
            />

            {/* Navigation links with comfortable spacing and active indicator */}
            <Box
              sx={{
                display: { xs: "none", sm: "flex" },
                alignItems: "center",
                gap: 1.5,
              }}
            >
              {navigation.map((item) => {
                const isActive =
                  item.path === "/"
                    ? location.pathname === "/"
                    : location.pathname.startsWith(item.path);

                return (
                  <Box
                    component={Link}
                    to={item.path}
                    key={item.path}
                    sx={{
                      color: isActive ? "#48cc90" : "rgba(255, 255, 255, 0.7)",
                      backgroundColor: isActive
                        ? "rgba(0, 134, 58, 0.22)"
                        : "transparent",
                      border: isActive
                        ? "1px solid rgba(72, 204, 144, 0.35)"
                        : "1px solid transparent",
                      borderRadius: "8px",
                      padding: "6px 16px",
                      textDecoration: "none",
                      fontSize: "14px",
                      fontWeight: isActive ? 600 : 500,
                      transition: "all 0.2s ease",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      "&:hover": {
                        color: "#fff",
                        backgroundColor: isActive
                          ? "rgba(0, 134, 58, 0.32)"
                          : "rgba(255, 255, 255, 0.06)",
                      },
                    }}
                  >
                    {getNavLabel(item.path)}
                  </Box>
                );
              })}
            </Box>
          </Box>

          {/* Right section: Language Switcher + User Dropdown */}
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1.5,
            }}
          >
            {/* Bilingual Switcher Toggle Button */}
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
                  borderColor: "#4caf50",
                  background: "rgba(76, 175, 80, 0.15)",
                  color: "#a5d6a7",
                },
                display: "flex",
                alignItems: "center",
                gap: 0.8,
              }}
            >
              <span style={{ fontSize: "16px", lineHeight: 1 }}>
                {language === "vi" ? "🇻🇳" : "🇬🇧"}
              </span>
              <span>{language === "vi" ? "VI" : "EN"}</span>
            </Button>

            <UserDropdown />
          </Box>
        </Toolbar>
      </AppBar>
      <nav>
        <Drawer
          container={container}
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true,
          }}
          PaperProps={{
            style: { background: darkTheme.palette.background.default },
          }}
          sx={{
            display: { xs: "block", sm: "none" },
            "& .MuiDrawer-paper": {
              boxSizing: "border-box",
              width: drawerWidth,
            },
          }}
        >
          {drawer}
        </Drawer>
      </nav>
    </Box>
  );
}
