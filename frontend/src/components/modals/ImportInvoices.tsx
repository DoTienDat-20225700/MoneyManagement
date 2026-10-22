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
import NewInvoiceForm from "../forms/NewInvoiceForm";
import { useLanguage } from "../../context/LanguageContext";

export default function ImportInvoice() {
  const { t } = useLanguage();
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down("md"));

  const [searchParams, setSearchParams] = useSearchParams();

  const isOpen = searchParams.get("invoice") === "1";
  function closeModal() {
    setSearchParams((state) => {
      state.delete("invoice");
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
        <span>{t("import_invoices")}</span>
        <IconButton size="small" onClick={closeModal} aria-label={t("close")} sx={{ color: "text.secondary" }}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        {isOpen && <NewInvoiceForm />}
      </DialogContent>
    </Dialog>
  );
}
