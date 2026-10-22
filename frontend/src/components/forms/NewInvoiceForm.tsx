import { useState, useEffect } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { HelpOutlineRounded, CheckCircleOutlineRounded as CheckCircleIcon } from "@mui/icons-material";
import {
  Box,
  Button,
  Checkbox,
  CircularProgress,
  FormControl,
  FormControlLabel,
  FormGroup,
  FormLabel,
  InputLabel,
  MenuItem,
  Radio,
  RadioGroup,
  Select,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { grey } from "@mui/material/colors";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSnackbar } from "notistack";
import { Controller, useForm } from "react-hook-form";
import { useSearchParams } from "react-router-dom";
import { TypeOption } from "../../enums/Enums";
import { useInvoice, ParsedInvoiceResult } from "../../hooks/api/useInvoice";
import { useLabels } from "../../hooks/api/useLabels";
import { BankInstitutions } from "../../models/Invoices";
import { typeOptionMask } from "../../models/Transaction";
import {
  NewInvoiceImportFormData,
  newInvoiceImportSchema,
} from "../../schemas/invoiceImportSchema";
import { paletteTokens } from "../../theme";
import { useLanguage } from "../../context/LanguageContext";

function NewInvoiceForm() {
  const { language, t } = useLanguage();
  const queryClient = useQueryClient();
  const { uploadInvoices, previewInvoices } = useInvoice();
  const { getLabels } = useLabels();
  const { data: labels } = useQuery({
    queryKey: ["labels"],
    queryFn: getLabels,
  });
  const { enqueueSnackbar } = useSnackbar();
  const [_, setSearchParams] = useSearchParams();

  const [previewResults, setPreviewResults] = useState<ParsedInvoiceResult[] | null>(null);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);

  const {
    handleSubmit,
    control,
    formState: { errors },
    setValue,
    watch,
  } = useForm<NewInvoiceImportFormData>({
    resolver: zodResolver(newInvoiceImportSchema),
    defaultValues: {
      invoices: undefined,
      institution: BankInstitutions.GENERAL_VN,
      type: undefined,
      label: undefined,
      updateWallet: undefined,
    },
  });

  const currentInstitution = watch("institution");

  // Live scan handler when user picks files
  const handleFileChange = async (files: FileList | null) => {
    setSelectedFiles(files);
    setValue("invoices", files as any);
    if (!files || files.length === 0) {
      setPreviewResults(null);
      return;
    }
    try {
      setIsPreviewLoading(true);
      const results = await previewInvoices({
        invoices: files,
        institution: currentInstitution || BankInstitutions.GENERAL_VN,
      });
      setPreviewResults(results);
    } catch (err) {
      console.error(err);
      setPreviewResults(null);
    } finally {
      setIsPreviewLoading(false);
    }
  };

  // Re-scan if institution changes and files are already chosen
  useEffect(() => {
    if (selectedFiles && selectedFiles.length > 0) {
      let isCancelled = false;
      setIsPreviewLoading(true);
      previewInvoices({
        invoices: selectedFiles,
        institution: currentInstitution || BankInstitutions.GENERAL_VN,
      })
        .then((res) => {
          if (!isCancelled) setPreviewResults(res);
        })
        .catch(() => {
          if (!isCancelled) setPreviewResults(null);
        })
        .finally(() => {
          if (!isCancelled) setIsPreviewLoading(false);
        });
      return () => {
        isCancelled = true;
      };
    }
  }, [currentInstitution]);

  const { mutateAsync, isPending } = useMutation({
    mutationFn: uploadInvoices,
    onSuccess: (res) => {
      setSearchParams((state) => {
        state.delete("invoice");
        return state;
      });
      queryClient.invalidateQueries({
        queryKey: ["transactions"],
      });
      queryClient.invalidateQueries({
        queryKey: ["wallet"],
      });
      queryClient.invalidateQueries({
        queryKey: ["budgets"],
      });
      queryClient.invalidateQueries({
        queryKey: ["budget_summary"],
      });

      const imported = res?.imported || [];
      let successMsg = t("invoice_import_success");
      if (imported.length === 1 && (imported[0].title || imported[0].formatted_value)) {
        const it = imported[0];
        const detailParts: string[] = [];
        if (it.title) detailParts.push(it.title);
        if (it.formatted_value) detailParts.push(it.formatted_value);
        if (it.date) detailParts.push(it.date);
        successMsg = language === "vi"
          ? `Đã nhập hoá đơn: ${detailParts.join(" • ")}`
          : `Imported invoice: ${detailParts.join(" • ")}`;
      } else if (imported.length > 1) {
        successMsg = language === "vi"
          ? `Đã nhập thành công ${imported.length} hoá đơn!`
          : `Successfully imported ${imported.length} invoices!`;
      }

      enqueueSnackbar(successMsg, {
        variant: "success",
        autoHideDuration: 4500,
        anchorOrigin: { horizontal: "right", vertical: "bottom" },
      });
    },
    onError: (err: any) => {
      const isParseError =
        err?.response?.data?.message?.includes("phân tích") ||
        err?.response?.data?.message?.includes("parse");
      const errorMsg = !err?.response
        ? t("no_server_response")
        : isParseError
        ? t("err_invoice_parse")
        : t("err_invoice_save");
      enqueueSnackbar(errorMsg, {
        variant: "error",
        autoHideDuration: 3500,
        anchorOrigin: { horizontal: "right", vertical: "bottom" },
      });
    },
  });

  async function importFiles(data: NewInvoiceImportFormData) {
    await mutateAsync({
      invoices: data.invoices,
      institution: data.institution,
      type: data?.type,
      label: data?.label,
      updateWallet: data?.updateWallet,
    });
  }

  return (
    <form
      onSubmit={handleSubmit(importFiles)}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 20,
        width: "500px",
        marginTop: 10,
      }}
    >
      <Controller
        name="invoices"
        control={control}
        render={() => (
          <FormControl sx={{ width: "100%" }}>
            <TextField
              fullWidth
              autoFocus
              type="file"
              helperText={
                errors.invoices
                  ? errors.invoices.message === "err_file_size"
                    ? t("err_file_size")
                    : errors.invoices.message === "err_file_type"
                    ? t("err_file_type")
                    : t("err_invoice_req")
                  : t("invoice_file_tip")
              }
              error={!!errors.invoices}
              onChange={(e: any) => {
                handleFileChange(e.target.files);
              }}
              size="small"
              inputProps={{
                multiple: true,
                accept: ".pdf,.png,.jpg,.jpeg,.webp,image/*",
                "aria-label": t("upload_invoice"),
              }}
            />
          </FormControl>
        )}
      />

      {/* Loading state when scanning image */}
      {isPreviewLoading && (
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1.5,
            p: 1.5,
            borderRadius: 2,
            backgroundColor: "rgba(0, 134, 58, 0.05)",
            border: "1px dashed #00863A",
          }}
        >
          <CircularProgress size={18} sx={{ color: "#48cc90" }} />
          <Typography variant="body2" sx={{ color: "#48cc90", fontWeight: 500 }}>
            {language === "vi"
              ? "Đang quét và đọc thông tin trong ảnh..."
              : "Scanning and extracting information from image..."}
          </Typography>
        </Box>
      )}

      {/* Extracted Information Message Box */}
      {!isPreviewLoading && previewResults && previewResults.length > 0 && (
        <Box
          sx={{
            p: 2,
            borderRadius: 2,
            backgroundColor: "rgba(0, 134, 58, 0.08)",
            border: "1px solid #00863A",
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5 }}>
            <CheckCircleIcon sx={{ color: "#48cc90", fontSize: 20 }} />
            <Typography variant="subtitle2" fontWeight={700} sx={{ color: "#48cc90" }}>
              {language === "vi"
                ? "Đã đọc được thông tin trong ảnh:"
                : "Successfully read from image:"}
            </Typography>
          </Box>

          {previewResults.map((item, idx) => {
            const hasData = item.value || item.formatted_date || (item.title && item.title !== "Giao dịch chuyển khoản");
            return (
              <Box
                key={idx}
                sx={{
                  mt: idx > 0 ? 1.5 : 0,
                  pt: idx > 0 ? 1.5 : 0,
                  borderTop: idx > 0 ? "1px dashed rgba(255,255,255,0.15)" : "none",
                }}
              >
                {previewResults.length > 1 && (
                  <Typography variant="caption" sx={{ color: grey[400], fontWeight: 600 }}>
                    {item.file_name}:
                  </Typography>
                )}
                {hasData ? (
                  <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5, mt: 0.5 }}>
                    <Typography variant="body2" sx={{ color: grey[200] }}>
                      • <strong>{language === "vi" ? "Tiêu đề / Lời nhắn" : "Title / Note"}:</strong>{" "}
                      <span>{item.title || "—"}</span>
                    </Typography>
                    <Typography variant="body2" sx={{ color: grey[200] }}>
                      • <strong>{language === "vi" ? "Số tiền" : "Amount"}:</strong>{" "}
                      <span style={{ color: "#48cc90", fontWeight: 700, fontSize: "15px" }}>
                        {item.formatted_value || "—"}
                      </span>
                    </Typography>
                    <Typography variant="body2" sx={{ color: grey[200] }}>
                      • <strong>{language === "vi" ? "Ngày giao dịch" : "Date"}:</strong>{" "}
                      <span>{item.formatted_date || "—"}</span>
                    </Typography>
                  </Box>
                ) : (
                  <Typography variant="caption" sx={{ color: paletteTokens.warning, mt: 0.5, display: "block" }}>
                    {language === "vi"
                      ? "⚠️ Ảnh mờ hoặc chưa nhận diện rõ chữ số. Hệ thống sẽ tự phân tích lại khi bấm Nhập hoá đơn."
                      : "⚠️ Could not clearly extract fields. System will re-attempt upon submit."}
                  </Typography>
                )}
              </Box>
            );
          })}
        </Box>
      )}

      <Controller
        name="institution"
        control={control}

        render={({ field: { onChange, value } }) => (
          <FormControl fullWidth size="small">
            <InputLabel id="import-bank-institution-label">
              {t("bank_institution")}
            </InputLabel>
            <Select
              labelId="import-bank-institution-label"
              id="import-bank-institution-select"
              value={value}
              label={t("bank_institution")}
              onChange={onChange}
            >
              {Object.values(BankInstitutions).map((item, index) => {
                return (
                  <MenuItem key={index} value={item}>
                    {item}
                  </MenuItem>
                );
              })}
            </Select>
          </FormControl>
        )}
      />

      <Controller
        name="label"
        control={control}
        render={({ field: { onChange, value } }) => (
          <FormControl fullWidth size="small">
            <InputLabel id="import-label-select-label">
              {t("col_label")}
            </InputLabel>
            <Select<number | string>
              labelId="import-label-select-label"
              id="import-label-select"
              value={
                value !== undefined && value !== null && value !== ""
                  ? Number(value)
                  : ""
              }
              label={t("col_label")}
              onChange={(e) =>
                onChange(
                  e.target.value === "" ? undefined : Number(e.target.value)
                )
              }
            >
              <MenuItem value="">
                <em>{t("uncategorized")}</em>
              </MenuItem>
              {labels?.map((item) => (
                <MenuItem key={item.id} value={Number(item.id)}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Box
                      sx={{
                        width: 12,
                        height: 12,
                        borderRadius: "50%",
                        backgroundColor: item.color,
                      }}
                    />
                    {item.name}
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}
      />

      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-start",
        }}
      >
        <Typography component="h2">{t("global_optional_options")}</Typography>
        <Tooltip
          title={t("global_options_tooltip")}
          arrow
          placement="top"
        >
          <HelpOutlineRounded
            sx={{
              fontSize: "16px",
              marginLeft: 0.5,
            }}
          />
        </Tooltip>
      </Box>

      <Controller
        name="type"
        control={control}
        render={({ field: { onChange, value, name } }) => (
          <FormControl>
            <FormLabel
              sx={{ mb: 1, "&.Mui-disabled": { color: "white" } }}
              disabled={true}
              about="teste"
            >
              {t("type")}
            </FormLabel>
            <RadioGroup
              defaultValue={undefined}
              name={name}
              value={value}
              onChange={onChange}
            >
              {Object.values(TypeOption).map((item, i) => {
                return (
                  <FormControlLabel
                    key={i}
                    value={item}
                    control={<Radio />}
                    label={typeOptionMask(item, language)}
                    sx={{
                      backgroundColor: grey[900],
                      p: 1,
                      m: 0.5,
                      borderRadius: 2,
                    }}
                  />
                );
              })}
            </RadioGroup>
          </FormControl>
        )}
      />
      <FormGroup>
        <FormControlLabel
          control={
            <Controller
              name="updateWallet"
              control={control}
              render={({ field: { onChange, value, name } }) => (
                <Checkbox
                  name={name}
                  checked={value}
                  onChange={onChange}
                  inputProps={{ "aria-label": "controlled" }}
                />
              )}
            />
          }
          label={t("update_wallet")}
        />
      </FormGroup>

      <Button
        type="submit"
        variant="contained"
        disabled={isPending || isPreviewLoading}
        startIcon={isPending ? <CircularProgress size={16} color="inherit" /> : null}
      >
        {isPending
          ? (language === "vi" ? "Đang nhập hoá đơn..." : "Importing...")
          : t("import_btn")}
      </Button>

    </form>
  );
}

export default NewInvoiceForm;
