import * as React from "react";
import { Link, useLocation } from "react-router-dom";
import {
  AppBar,
  Box,
  Button,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Tooltip,
  Typography,
} from "@mui/material";
import ViewSidebarOutlinedIcon from "@mui/icons-material/ViewSidebarOutlined";
import TranslateIcon from "@mui/icons-material/Translate";
import { navigation } from "../navigation";
import UserDropdown from "./UserDropdown";
import { useLanguage } from "../context/LanguageContext";
import { usePrefersReducedMotion } from "../hooks/usePrefersReducedMotion";

export const SIDEBAR_WIDTH = 240;
export const SIDEBAR_COLLAPSED_WIDTH = 0;
export const TOPBAR_HEIGHT = 56;

interface AppDrawerProps {
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  window?: () => Window;
}

export default function AppDrawer(props: AppDrawerProps) {
  const { collapsed: controlledCollapsed, onToggleCollapse, window } = props;
  const location = useLocation();
  const { language, toggleLanguage, t } = useLanguage();
  const prefersReducedMotion = usePrefersReducedMotion();

  // Internal state fallback (defaults to open: false) - NO localStorage
  const [internalCollapsed, setInternalCollapsed] = React.useState<boolean>(false);

  const isCollapsed =
    controlledCollapsed !== undefined ? controlledCollapsed : internalCollapsed;

  const handleToggle = () => {
    if (onToggleCollapse) {
      onToggleCollapse();
    } else {
      setInternalCollapsed((prev) => !prev);
    }
  };

  // Mobile drawer state
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const hamburgerRef = React.useRef<HTMLButtonElement | null>(null);

  const handleMobileToggle = () => {
    setMobileOpen((prev) => !prev);
  };

  const handleDrawerClose = () => {
    setMobileOpen(false);
    setTimeout(() => {
      hamburgerRef.current?.focus();
    }, 0);
  };

  // Reusable active matching (exact root "/" or startsWith sub-route)
  const checkIsActive = (path: string) => {
    return path === "/"
      ? location.pathname === "/"
      : location.pathname.startsWith(path);
  };

  const transitionDuration = prefersReducedMotion ? "none" : "0.2s cubic-bezier(0.4, 0, 0.2, 1)";
  const sidebarTransition = prefersReducedMotion
    ? "none"
    : `width ${transitionDuration}, visibility ${transitionDuration}`;

  // Mobile Drawer content
  const mobileDrawerContent = (
    <Box
      sx={{
        width: SIDEBAR_WIDTH,
        height: "100%",
        display: "flex",
        flexDirection: "column",
        backgroundColor: "#0d0e12",
        color: "#fff",
      }}
    >
      {/* Mobile drawer header */}
      <Box
        component={Link}
        to="/"
        onClick={handleDrawerClose}
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1.5,
          p: 2,
          textDecoration: "none",
          color: "inherit",
          minHeight: TOPBAR_HEIGHT,
        }}
      >
        <Box
          component="img"
          src="/logo.png"
          alt=""
          aria-hidden="true"
          sx={{ width: 28, height: 28, objectFit: "contain" }}
        />
        <Typography
          variant="h6"
          fontWeight={700}
          sx={{
            color: "#ffffff",
            letterSpacing: 0.3,
          }}
        >
          MoneyManager
        </Typography>
      </Box>

      <Divider sx={{ borderColor: "rgba(255, 255, 255, 0.08)" }} />

      {/* Mobile nav items */}
      <List component="nav" aria-label={t("mobile_navigation")} sx={{ px: 1.5, py: 2, flexGrow: 1 }}>
        {navigation.map((item) => {
          const isActive = checkIsActive(item.path);
          const label = t(item.translationKey);

          return (
            <ListItem key={item.path} disablePadding sx={{ mb: 1 }}>
              <ListItemButton
                component={Link}
                to={item.path}
                onClick={handleDrawerClose}
                aria-current={isActive ? "page" : undefined}
                sx={{
                  minHeight: 48,
                  borderRadius: "8px",
                  backgroundColor: isActive
                    ? "rgba(0, 134, 58, 0.14)"
                    : "transparent",
                  color: isActive ? "#48cc90" : "#e0e0e0",
                  border: "1px solid transparent",
                  transition: prefersReducedMotion ? "none" : "all 0.2s ease",
                  "&:hover": {
                    backgroundColor: isActive
                      ? "rgba(0, 134, 58, 0.32)"
                      : "rgba(255, 255, 255, 0.06)",
                    color: "#fff",
                  },
                  "&.Mui-focusVisible": {
                    outline: "2px solid #00863A",
                    outlineOffset: 2,
                  },
                }}
              >
                <ListItemIcon sx={{ color: "inherit", minWidth: 40 }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={label}
                  primaryTypographyProps={{
                    fontSize: "15px",
                    fontWeight: isActive ? 600 : 500,
                  }}
                />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>

      {/* Mobile drawer footer */}
      <Box sx={{ p: 2, borderTop: "1px solid rgba(255, 255, 255, 0.08)" }}>
        <Button
          fullWidth
          variant="outlined"
          size="medium"
          onClick={toggleLanguage}
          startIcon={<TranslateIcon fontSize="small" aria-hidden="true" />}
          sx={{
            py: 1,
            borderRadius: "8px",
            borderColor: "rgba(255, 255, 255, 0.2)",
            color: "#fff",
            textTransform: "none",
            "&:hover": {
              borderColor: "#48cc90",
              background: "rgba(72, 204, 144, 0.10)",
            },
            "&.Mui-focusVisible": {
              outline: "2px solid #00863A",
              outlineOffset: 2,
            },
          }}
        >
          {language === "vi" ? "🇻🇳 Tiếng Việt" : "🇬🇧 English"}
        </Button>
      </Box>
    </Box>
  );

  const container =
    window !== undefined ? () => window().document.body : undefined;

  // Accessible labels for the unified single hamburger button
  const desktopAriaLabel = isCollapsed ? t("expand_sidebar") : t("collapse_sidebar");
  const mobileAriaLabel = mobileOpen ? t("close_drawer") : t("open_drawer");

  return (
    <>
      {/* =========================================================================
          1. DESKTOP SIDEBAR (>= md breakpoint)
             - Completely hidden when collapsed (width: 0, visibility: hidden)
             - Anchored below TopBar (top: TOPBAR_HEIGHT)
         ========================================================================= */}
      <Box
        component="nav"
        id="main-sidebar-nav"
        aria-label={t("main_navigation")}
        sx={{
          display: { xs: "none", md: "flex" },
          flexDirection: "column",
          position: "fixed",
          top: `${TOPBAR_HEIGHT}px`,
          bottom: 0,
          left: 0,
          width: isCollapsed ? 0 : SIDEBAR_WIDTH,
          visibility: isCollapsed ? "hidden" : "visible",
          zIndex: 1100,
          backgroundColor: "#0d0e12",
          borderRight: isCollapsed ? "none" : "1px solid rgba(255, 255, 255, 0.08)",
          boxShadow: isCollapsed ? "none" : "4px 0 20px rgba(0, 0, 0, 0.35)",
          transition: sidebarTransition,
          overflowX: "hidden",
          pointerEvents: isCollapsed ? "none" : "auto",
          "@media print": {
            display: "none !important",
          },
        }}
      >
        {/* Sidebar Navigation Items */}
        <List
          sx={{
            px: 1.25,
            py: 1.5,
            flexGrow: 1,
            overflowY: "auto",
            overflowX: "hidden",
            width: `${SIDEBAR_WIDTH}px`,
            boxSizing: "border-box",
          }}
        >
          {navigation.map((item) => {
            const isActive = checkIsActive(item.path);
            const label = t(item.translationKey);

            return (
              <ListItem
                key={item.path}
                disablePadding
                sx={{
                  mb: 1,
                  display: "flex",
                  width: "100%",
                }}
              >
                <ListItemButton
                  component={Link}
                  to={item.path}
                  tabIndex={isCollapsed ? -1 : 0}
                  aria-current={isActive ? "page" : undefined}
                  sx={{
                    minHeight: 44,
                    width: "100%",
                    borderRadius: "8px",
                    justifyContent: "flex-start",
                    px: 2,
                    backgroundColor: isActive
                      ? "rgba(0, 134, 58, 0.14)"
                      : "transparent",
                    color: isActive ? "#48cc90" : "#9e9e9e",
                    border: "1px solid transparent",
                    transition: prefersReducedMotion ? "none" : "all 0.2s ease",
                    "&:hover": {
                      backgroundColor: isActive
                        ? "rgba(0, 134, 58, 0.32)"
                        : "rgba(255, 255, 255, 0.06)",
                      color: "#ffffff",
                      "& .MuiListItemIcon-root": {
                        color: isActive ? "#48cc90" : "#ffffff",
                      },
                    },
                    "&.Mui-focusVisible": {
                      outline: "2px solid #00863A",
                      outlineOffset: 2,
                    },
                  }}
                >
                  <ListItemIcon
                    sx={{
                      minWidth: 38,
                      color: "inherit",
                      justifyContent: "center",
                      mr: 1,
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={label}
                    primaryTypographyProps={{
                      fontSize: "14px",
                      fontWeight: isActive ? 600 : 500,
                      noWrap: true,
                    }}
                  />
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>
      </Box>

      {/* =========================================================================
          2. TOP BAR (Header)
             - Fixed at top (0, 0), spans 100% width
             - Order: [Sidebar Toggle Button] -> [Logo] -> [MoneyManager]
         ========================================================================= */}
      <AppBar
        component="header"
        elevation={0}
        sx={{
          height: TOPBAR_HEIGHT,
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          width: "100%",
          backgroundColor: "rgba(13, 14, 18, 0.85)",
          backdropFilter: "blur(14px)",
          borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
          boxShadow: "0 4px 20px rgba(0, 0, 0, 0.25)",
          zIndex: 1200,
          "@media print": {
            display: "none !important",
          },
        }}
      >
        <Toolbar
          variant="dense"
          disableGutters
          sx={{
            height: TOPBAR_HEIGHT,
            minHeight: TOPBAR_HEIGHT,
            px: { xs: 1.5, sm: 2, md: 2.5 },
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          {/* Left section: [Sidebar Toggle Button] -> [Logo] -> [MoneyManager] */}
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.25 }}>
            {/* Desktop Sidebar Toggle Button */}
            <Tooltip
              title={desktopAriaLabel}
              placement="bottom"
              arrow
              disableFocusListener={false}
            >
              <IconButton
                id="main-hamburger-btn-desktop"
                color="inherit"
                aria-label={desktopAriaLabel}
                aria-controls="main-sidebar-nav"
                aria-expanded={!isCollapsed}
                edge="start"
                onClick={handleToggle}
                sx={{
                  display: { xs: "none", md: "inline-flex" },
                  minWidth: 40,
                  minHeight: 40,
                  width: 40,
                  height: 40,
                  color: "#e0e0e0",
                  borderRadius: "8px",
                  "&:hover": {
                    color: "#ffffff",
                    backgroundColor: "rgba(255, 255, 255, 0.06)",
                  },
                  "&.Mui-focusVisible": {
                    outline: "2px solid #00863A",
                    outlineOffset: 2,
                  },
                }}
              >
                <ViewSidebarOutlinedIcon aria-hidden="true" />
              </IconButton>
            </Tooltip>

            {/* Mobile Sidebar Toggle Button */}
            <Tooltip
              title={mobileAriaLabel}
              placement="bottom"
              arrow
              disableFocusListener={false}
            >
              <IconButton
                id="main-hamburger-btn-mobile"
                ref={hamburgerRef}
                color="inherit"
                aria-label={mobileAriaLabel}
                aria-controls="mobile-nav-drawer"
                aria-expanded={mobileOpen}
                edge="start"
                onClick={handleMobileToggle}
                sx={{
                  display: { xs: "inline-flex", md: "none" },
                  minWidth: 40,
                  minHeight: 40,
                  width: 40,
                  height: 40,
                  color: "#e0e0e0",
                  borderRadius: "8px",
                  "&:hover": {
                    color: "#ffffff",
                    backgroundColor: "rgba(255, 255, 255, 0.06)",
                  },
                  "&.Mui-focusVisible": {
                    outline: "2px solid #00863A",
                    outlineOffset: 2,
                  },
                }}
              >
                <ViewSidebarOutlinedIcon aria-hidden="true" />
              </IconButton>
            </Tooltip>

            {/* Logo + Web Name: MoneyManager (always next to button) */}
            <Box
              component={Link}
              to="/"
              aria-label="MoneyManager"
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1.25,
                textDecoration: "none",
                color: "inherit",
                borderRadius: "6px",
                py: 0.5,
                px: 0.5,
                "&:focus-visible": {
                  outline: "2px solid #00863A",
                  outlineOffset: 2,
                },
              }}
            >
              <Box
                component="img"
                src="/logo.png"
                alt=""
                aria-hidden="true"
                sx={{ width: 28, height: 28, objectFit: "contain", flexShrink: 0 }}
              />
              <Typography
                variant="h6"
                fontWeight={700}
                sx={{
                  color: "#ffffff",
                  letterSpacing: 0.3,
                  fontSize: "1.05rem",
                  lineHeight: 1,
                  userSelect: "none",
                }}
              >
                MoneyManager
              </Typography>
            </Box>
          </Box>

          {/* Right section: Bilingual Switcher + User Dropdown */}
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            <Button
              onClick={toggleLanguage}
              variant="outlined"
              size="small"
              sx={{
                height: 32,
                minWidth: 40,
                px: 1.25,
                borderRadius: "16px",
                color: "#ffffff",
                borderColor: "rgba(255, 255, 255, 0.2)",
                background: "rgba(255, 255, 255, 0.05)",
                fontSize: "13px",
                fontWeight: 600,
                textTransform: "none",
                letterSpacing: 0.5,
                transition: prefersReducedMotion ? "none" : "all 0.2s ease",
                "&:hover": {
                  borderColor: "#48cc90",
                  background: "rgba(72, 204, 144, 0.10)",
                  color: "#ffffff",
                },
                "&.Mui-focusVisible": {
                  outline: "2px solid #00863A",
                  outlineOffset: 2,
                },
                display: "flex",
                alignItems: "center",
                gap: 0.75,
              }}
            >
              <span style={{ fontSize: "15px", lineHeight: 1 }}>
                {language === "vi" ? "🇻🇳" : "🇬🇧"}
              </span>
              <span>{language === "vi" ? "VI" : "EN"}</span>
            </Button>

            <UserDropdown />
          </Box>
        </Toolbar>
      </AppBar>

      {/* =========================================================================
          3. MOBILE TEMPORARY DRAWER (< md breakpoint)
         ========================================================================= */}
      <Drawer
        id="mobile-nav-drawer"
        container={container}
        variant="temporary"
        open={mobileOpen}
        onClose={handleDrawerClose}
        ModalProps={{
          keepMounted: true,
        }}
        PaperProps={{
          sx: {
            backgroundColor: "#0d0e12",
            backgroundImage: "none",
            borderRight: "1px solid rgba(255, 255, 255, 0.08)",
          },
        }}
        sx={{
          display: { xs: "block", md: "none" },
          "& .MuiDrawer-paper": {
            boxSizing: "border-box",
            width: SIDEBAR_WIDTH,
          },
        }}
      >
        {mobileDrawerContent}
      </Drawer>
    </>
  );
}
