import { useState, useEffect } from "react";
import SearchIcon from "@mui/icons-material/Search";
import ClearIcon from "@mui/icons-material/Clear";
import {
  Box,
  CircularProgress,
  IconButton,
  InputAdornment,
  TextField,
  Typography,
  Alert,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import LatestTransactions from "../components/LatestTransactions";
import { useTransactions } from "../hooks/api/useTransactions";
import { useLanguage } from "../context/LanguageContext";
import { Transaction } from "../models/Transaction";
import { paletteTokens } from "../theme";

function Transactions() {
  const { t } = useLanguage();
  const { getTransactions } = useTransactions();
  const [searchTerm, setSearchTerm] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchTerm);
    }, 300);
    return () => clearTimeout(handler);
  }, [searchTerm]);

  const {
    data: transactions,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["transactions", debouncedSearch],
    queryFn: () =>
      getTransactions({ search: debouncedSearch }) as Promise<Transaction[]>,
  });

  return (
    <>
      <Typography component="h1" variant="h4" fontWeight={600} mb={4}>
        {t("transactions")}
      </Typography>
      <Box>
        <Box component="form" onSubmit={(e) => e.preventDefault()} sx={{ mb: 2 }}>
          <TextField
            fullWidth
            label=""
            variant="outlined"
            size="medium"
            placeholder={t("find_transaction")}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              style: { fontSize: "14px", height: "40px" },
              startAdornment: (
                <InputAdornment position="start" sx={{ color: paletteTokens.textSecondary }}>
                  <SearchIcon />
                </InputAdornment>
              ),
              endAdornment: (
                <>
                  {isLoading && <CircularProgress size={18} sx={{ mr: 1 }} />}
                  {searchTerm && (
                    <InputAdornment position="end">
                      <IconButton
                        size="small"
                        onClick={() => setSearchTerm("")}
                        edge="end"
                      >
                        <ClearIcon fontSize="small" />
                      </IconButton>
                    </InputAdornment>
                  )}
                </>
              ),
            }}
          />
        </Box>

        {isError && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => refetch()}>
            {t("unable_to_load_data")}
          </Alert>
        )}

        <LatestTransactions data={transactions ?? []} headOnly={false} />
      </Box>
    </>
  );
}

export default Transactions;
