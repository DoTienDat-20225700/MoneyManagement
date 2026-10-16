import { ReactNode } from "react";
import DashboardIcon from "@mui/icons-material/Dashboard";
import ReceiptIcon from "@mui/icons-material/Receipt";
import SavingsIcon from "@mui/icons-material/Savings";
import AccountBalanceWalletIcon from "@mui/icons-material/AccountBalanceWallet";
import AssessmentIcon from "@mui/icons-material/Assessment";
import HandshakeIcon from "@mui/icons-material/Handshake";

interface NavigationItem {
  label: string;
  path: string;
  icon: ReactNode;
}

export const navigation: NavigationItem[] = [
  {
    label: "Dashboard",
    path: "/",
    icon: <DashboardIcon />,
  },
  {
    label: "Transactions",
    path: "/transactions",
    icon: <ReceiptIcon />,
  },
  {
    label: "Budgets",
    path: "/budgets",
    icon: <AccountBalanceWalletIcon />,
  },
  {
    label: "Reports",
    path: "/reports",
    icon: <AssessmentIcon />,
  },
  {
    label: "SavingPlans",
    path: "/saving-plans",
    icon: <SavingsIcon />,
  },
  {
    label: "Debts",
    path: "/debts",
    icon: <HandshakeIcon />,
  },
];

