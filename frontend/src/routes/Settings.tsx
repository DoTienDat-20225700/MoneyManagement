import { useState } from "react";
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  Divider,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import PersonIcon from "@mui/icons-material/Person";
import LocalOfferIcon from "@mui/icons-material/LocalOffer";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import { grey } from "@mui/material/colors";
import { LocalizationProvider, DatePicker } from "@mui/x-date-pickers";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSnackbar } from "notistack";
import { useAuth } from "../hooks/useAuth";
import { useLabels } from "../hooks/api/useLabels";
import { useLanguage } from "../context/LanguageContext";
import AddLabel from "../components/modals/AddLabel";

function Settings() {
  const { language, t } = useLanguage();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { getLabels, deleteLabel } = useLabels();
  const { enqueueSnackbar } = useSnackbar();
  const [_, setSearchParams] = useSearchParams();

  const [activeTab, setActiveTab] = useState<"general" | "labels">("general");

  const { data: labels, isLoading: isLoadingLabels } = useQuery({
    queryKey: ["labels"],
    queryFn: () => getLabels(),
  });

  const { mutate: deleteLabelMutate, isPending: isDeleting } = useMutation({
    mutationFn: (labelId: number) => deleteLabel(labelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["labels"] });
      queryClient.invalidateQueries({ queryKey: ["wallet"] });
      enqueueSnackbar(t("label_deleted"), {
        variant: "success",
        autoHideDuration: 3000,
        anchorOrigin: { horizontal: "right", vertical: "bottom" },
      });
    },
    onError: (err: any) => {
      const errorMsg = !err?.response
        ? t("no_server_response")
        : t("err_label_delete");
      enqueueSnackbar(errorMsg, {
        variant: "error",
        autoHideDuration: 3000,
        anchorOrigin: { horizontal: "right", vertical: "bottom" },
      });
    },
  });

  const fullName =
    user && (user.first_name || user.last_name)
      ? [user.first_name, user.last_name].filter(Boolean).join(" ")
      : user?.email || "—";

  const email = user?.email || "—";

  return (
    <>
      <Box
        sx={{
          display: "flex",
          flexDirection: { xs: "column", md: "row" },
          gap: { xs: 3, md: 6 },
          alignItems: "flex-start",
        }}
      >
        {/* Navigation Sidebar */}
        <Box
          component="nav"
          sx={{
            width: { xs: "100%", md: 240 },
            flexShrink: 0,
            bgcolor: "rgba(255, 255, 255, 0.02)",
            borderRadius: 3,
            p: 1,
            border: "1px solid rgba(255, 255, 255, 0.06)",
          }}
        >
          <List disablePadding>
            <ListItem disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton
                selected={activeTab === "general"}
                onClick={() => setActiveTab("general")}
                sx={{
                  borderRadius: 2,
                  py: 1.2,
                  px: 2,
                  color: activeTab === "general" ? "#4caf50" : grey[400],
                  bgcolor:
                    activeTab === "general"
                      ? "rgba(46, 125, 50, 0.15) !important"
                      : "transparent",
                  "&:hover": {
                    bgcolor: "rgba(255, 255, 255, 0.05)",
                    color: "#fff",
                  },
                  transition: "all 0.2s ease",
                }}
              >
                <ListItemIcon
                  sx={{
                    color: "inherit",
                    minWidth: 40,
                  }}
                >
                  <PersonIcon />
                </ListItemIcon>
                <ListItemText
                  primary={t("general")}
                  primaryTypographyProps={{
                    fontWeight: activeTab === "general" ? 600 : 400,
                    fontSize: "0.95rem",
                  }}
                />
              </ListItemButton>
            </ListItem>

            <ListItem disablePadding>
              <ListItemButton
                selected={activeTab === "labels"}
                onClick={() => setActiveTab("labels")}
                sx={{
                  borderRadius: 2,
                  py: 1.2,
                  px: 2,
                  color: activeTab === "labels" ? "#4caf50" : grey[400],
                  bgcolor:
                    activeTab === "labels"
                      ? "rgba(46, 125, 50, 0.15) !important"
                      : "transparent",
                  "&:hover": {
                    bgcolor: "rgba(255, 255, 255, 0.05)",
                    color: "#fff",
                  },
                  transition: "all 0.2s ease",
                }}
              >
                <ListItemIcon
                  sx={{
                    color: "inherit",
                    minWidth: 40,
                  }}
                >
                  <LocalOfferIcon />
                </ListItemIcon>
                <ListItemText
                  primary={t("labels")}
                  primaryTypographyProps={{
                    fontWeight: activeTab === "labels" ? 600 : 400,
                    fontSize: "0.95rem",
                  }}
                />
              </ListItemButton>
            </ListItem>
          </List>
        </Box>

        {/* Content Container */}
        <Container disableGutters sx={{ flex: 1, minWidth: 0 }}>
          {activeTab === "general" && (
            <Stack spacing={5}>
              {/* Profile Section */}
              <Box>
                <Typography component="h1" variant="h6" mb={2} fontWeight={600}>
                  {t("profile")}
                </Typography>
                <Divider sx={{ borderColor: "rgba(255, 255, 255, 0.08)" }} />
                <Box sx={{ display: "flex", flexDirection: "column" }}>
                  <Box
                    py={3}
                    sx={{
                      display: "flex",
                      flexDirection: { xs: "column", sm: "row" },
                      gap: { xs: 1, sm: 10 },
                    }}
                  >
                    <Typography
                      variant="body2"
                      width={{ xs: "100%", sm: "180px" }}
                      color={grey[500]}
                    >
                      {t("full_name")}
                    </Typography>
                    <Typography variant="body1" fontWeight={500}>
                      {fullName}
                    </Typography>
                  </Box>
                  <Divider sx={{ borderColor: "rgba(255, 255, 255, 0.08)" }} />
                  <Box
                    py={3}
                    sx={{
                      display: "flex",
                      flexDirection: { xs: "column", sm: "row" },
                      gap: { xs: 1, sm: 10 },
                    }}
                  >
                    <Typography
                      variant="body2"
                      width={{ xs: "100%", sm: "180px" }}
                      color={grey[500]}
                    >
                      {t("email_address")}
                    </Typography>
                    <Typography variant="body1" fontWeight={500}>
                      {email}
                    </Typography>
                  </Box>
                </Box>
              </Box>

              {/* Options Section */}
              <Box>
                <Typography component="h2" variant="h6" mb={2} fontWeight={600}>
                  {t("options")}
                </Typography>
                <Divider sx={{ borderColor: "rgba(255, 255, 255, 0.08)" }} />
                <Box sx={{ display: "flex", flexDirection: "column" }}>
                  <Box
                    py={3}
                    sx={{
                      display: "flex",
                      flexDirection: { xs: "column", sm: "row" },
                      gap: { xs: 2, sm: 10 },
                    }}
                  >
                    <Typography
                      variant="body2"
                      width={{ xs: "100%", sm: "180px" }}
                      color={grey[500]}
                      pt={1}
                    >
                      {t("first_of_the_month")}
                    </Typography>
                    <Stack gap={1}>
                      <LocalizationProvider
                        dateAdapter={AdapterDayjs}
                        adapterLocale={language}
                      >
                        <DatePicker
                          views={["day"]}
                          format="DD"
                          slotProps={{
                            textField: {
                              size: "small",
                              sx: {
                                width: "180px",
                                bgcolor: "rgba(255, 255, 255, 0.04)",
                                borderRadius: 1.5,
                              },
                            },
                          }}
                        />
                      </LocalizationProvider>
                      <Typography variant="caption" color={grey[500]}>
                        {t("first_of_the_month_desc")}
                      </Typography>
                    </Stack>
                  </Box>
                </Box>
              </Box>
            </Stack>
          )}

          {activeTab === "labels" && (
            <Box>
              <Box
                sx={{
                  display: "flex",
                  alignItems: { xs: "flex-start", sm: "center" },
                  justifyContent: "space-between",
                  flexDirection: { xs: "column", sm: "row" },
                  gap: 2,
                  mb: 2,
                }}
              >
                <Box>
                  <Typography component="h1" variant="h6" fontWeight={600}>
                    {t("labels_management")}
                  </Typography>
                  <Typography variant="body2" color={grey[500]}>
                    {t("labels_desc")}
                  </Typography>
                </Box>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<AddIcon />}
                  onClick={() => setSearchParams({ label: "1" })}
                  sx={{
                    borderRadius: 2,
                    px: 2.5,
                    py: 1,
                    textTransform: "none",
                    fontWeight: 600,
                    backgroundColor: "#2e7d32",
                    "&:hover": { backgroundColor: "#1b5e20" },
                  }}
                >
                  {t("add_new_label")}
                </Button>
              </Box>

              <Divider sx={{ borderColor: "rgba(255, 255, 255, 0.08)", mb: 3 }} />

              {isLoadingLabels ? (
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    py: 6,
                  }}
                >
                  <CircularProgress size={32} color="primary" />
                </Box>
              ) : !labels || labels.length === 0 ? (
                <Box
                  sx={{
                    textAlign: "center",
                    py: 8,
                    px: 3,
                    borderRadius: 3,
                    bgcolor: "rgba(255, 255, 255, 0.02)",
                    border: "1px dashed rgba(255, 255, 255, 0.1)",
                  }}
                >
                  <LocalOfferIcon sx={{ fontSize: 40, color: grey[600], mb: 1.5 }} />
                  <Typography variant="body1" color={grey[400]} mb={2}>
                    {t("no_labels")}
                  </Typography>
                  <Button
                    variant="outlined"
                    color="primary"
                    startIcon={<AddIcon />}
                    onClick={() => setSearchParams({ label: "1" })}
                    sx={{ textTransform: "none", borderRadius: 2 }}
                  >
                    {t("add_new_label")}
                  </Button>
                </Box>
              ) : (
                <Stack spacing={1.5}>
                  {labels.map((item) => (
                    <Box
                      key={item.id}
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        p: 2,
                        borderRadius: 2,
                        bgcolor: "rgba(255, 255, 255, 0.03)",
                        border: "1px solid rgba(255, 255, 255, 0.07)",
                        transition: "all 0.2s ease",
                        "&:hover": {
                          borderColor: "rgba(255, 255, 255, 0.15)",
                          bgcolor: "rgba(255, 255, 255, 0.05)",
                        },
                      }}
                    >
                      <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                        <Box
                          sx={{
                            width: 16,
                            height: 16,
                            borderRadius: "50%",
                            bgcolor: item.color || "#4caf50",
                            boxShadow: `0 0 8px ${item.color || "#4caf50"}60`,
                            flexShrink: 0,
                          }}
                        />
                        <Typography variant="body1" fontWeight={500} color="#fff">
                          {item.name}
                        </Typography>
                        <Chip
                          label={item.color}
                          size="small"
                          sx={{
                            height: 22,
                            fontSize: "11px",
                            bgcolor: "rgba(255, 255, 255, 0.06)",
                            color: grey[400],
                            fontFamily: "monospace",
                          }}
                        />
                      </Box>
                      <Tooltip title={t("delete_label")}>
                        <IconButton
                          size="small"
                          onClick={() => deleteLabelMutate(item.id)}
                          disabled={isDeleting}
                          sx={{
                            color: grey[500],
                            "&:hover": {
                              color: "#f44336",
                              bgcolor: "rgba(244, 67, 54, 0.1)",
                            },
                          }}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  ))}
                </Stack>
              )}
            </Box>
          )}
        </Container>
      </Box>

      {/* Modal for adding a new label */}
      <AddLabel />
    </>
  );
}

export default Settings;
