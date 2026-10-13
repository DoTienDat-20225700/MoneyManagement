import AddIcon from "@mui/icons-material/Add";
import FileUploadIcon from "@mui/icons-material/FileUpload";
import { Box, Button, Grid, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import LatestTransactions from "../components/LatestTransactions";
import CurrentMonthChart from "../components/charts/CurrentMonthChart";
import ProfileChart from "../components/charts/ProfileChart";
import WalletGridRow from "../components/dashboard/WalletGridRow";
import DashboardBudgetSummary from "../components/dashboard/DashboardBudgetSummary";
import AddLabel from "../components/modals/AddLabel";
import AddTransaction from "../components/modals/AddTransaction";
import ImportInvoice from "../components/modals/ImportInvoices";
import { useTransactions } from "../hooks/api/useTransactions";
import { useWallet } from "../hooks/api/useWallet";
import { useLanguage } from "../context/LanguageContext";
import { Transaction } from "../models/Transaction";

const QUERY_LIMIT = 10;
function Home() {
  const { t } = useLanguage();
  const { getTransactions } = useTransactions();
  const { getWallet } = useWallet();
  const [_, setSearchParams] = useSearchParams();

  const { data: transactions } = useQuery({
    queryKey: ["transactions"],
    queryFn: () => getTransactions(QUERY_LIMIT) as Promise<Transaction[]>,
  });

  const {
    data: wallet,
    isPending,
    isError,
  } = useQuery({
    queryKey: ["wallet"],
    queryFn: () => getWallet(),
  });

  return (
    <>
      <Box
        sx={{
          display: "flex",
          flexDirection: {
            xs: "column",
            md: "row",
          },
          justifyContent: "space-between",
          alignItems: {
            xs: "start",
            md: "center",
          },
        }}
      >
        <Typography component="h1" variant="h4" fontWeight={600}>
          {t("dashboard_title")}
        </Typography>
        <Box sx={{ marginTop: { xs: 2, md: 0 } }}>
          <Button
            variant="outlined"
            size="medium"
            sx={{ marginRight: 2 }}
            startIcon={<FileUploadIcon />}
            onClick={() =>
              setSearchParams((state) => {
                if (!state.get("invoice")) state.set("invoice", "1");
                return state;
              })
            }
          >
            {t("import_invoice")}
          </Button>
          <Button
            variant="contained"
            size="medium"
            startIcon={<AddIcon />}
            onClick={() =>
              setSearchParams((state) => {
                if (!state.get("transaction")) state.set("transaction", "1");
                return state;
              })
            }
          >
            {t("new_transaction")}
          </Button>
        </Box>
      </Box>
      <Grid mt={2} container spacing={2} alignItems={"stretch"}>
        <WalletGridRow
          wallet={wallet}
          isPending={isPending}
          isError={isError}
        />
        <DashboardBudgetSummary />
        <Grid item xs={12} lg={6}>
          {transactions ? (
            <CurrentMonthChart />
          ) : (
            <Typography component="p" variant="body1">
              {t("unable_to_load_chart")}
            </Typography>
          )}
        </Grid>
        <Grid item xs={12} lg={6}>
          <ProfileChart />
        </Grid>
        <Grid item xs={12}>
          <Box height={"auto"}>
            <Typography component="h2" variant="h6" mb={1} mt={2}>
              {t("latest_transactions")}
            </Typography>
            {transactions && (
              <>
                <LatestTransactions data={transactions} headOnly={true} />
                <Link to={"/transactions"}>
                  <Button
                    variant="contained"
                    size="medium"
                    sx={{ marginTop: 2 }}
                  >
                    {t("show_more")}
                  </Button>
                </Link>
              </>
            )}
          </Box>
        </Grid>
      </Grid>

      <ImportInvoice />
      <AddTransaction />
      <AddLabel />
    </>
  );
}

export default Home;
