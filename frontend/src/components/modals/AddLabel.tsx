import {
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useSearchParams } from "react-router-dom";
import NewLabelForm from "../forms/NewLabelForm";
import { useLanguage } from "../../context/LanguageContext";

export default function AddLabel() {
  const { t } = useLanguage();
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down("md"));

  const [searchParams, setSearchParams] = useSearchParams();

  const isOpen = searchParams.get("label") === "1";
  function closeModal() {
    setSearchParams((state) => {
      state.delete("label");
      return state;
    });
  }

  return (
    <Dialog
      fullScreen={fullScreen}
      open={isOpen}
      onClose={closeModal}
    >
      <DialogTitle sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span>{t("add_new_label")}</span>
        <IconButton size="small" onClick={closeModal} aria-label={t("close")} sx={{ color: "text.secondary" }}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        {isOpen && <NewLabelForm />}
      </DialogContent>
    </Dialog>
  );
}
