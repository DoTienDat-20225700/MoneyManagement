import { ReactNode } from "react";
import DashboardIcon from "@mui/icons-material/Dashboard";
import ReceiptIcon from "@mui/icons-material/Receipt";
import SavingsIcon from "@mui/icons-material/Savings";
import AccountBalanceWalletIcon from "@mui/icons-material/AccountBalanceWallet";
import AssessmentIcon from "@mui/icons-material/Assessment";
import HandshakeIcon from "@mui/icons-material/Handshake";
import { TranslationKey } from "./i18n/translations";

export interface NavigationItem {
  label: string;
  path: string;
  icon: ReactNode;
  translationKey: TranslationKey;
}

export const navigation: NavigationItem[] = [
  {
    label: "Dashboard",
    path: "/",
    icon: <DashboardIcon aria-hidden="true" />,
    translationKey: "dashboard",
  },
  {
    label: "Transactions",
    path: "/transactions",
    icon: <ReceiptIcon aria-hidden="true" />,
    translationKey: "transactions",
  },
  {
    label: "Budgets",
    path: "/budgets",
    icon: <AccountBalanceWalletIcon aria-hidden="true" />,
    translationKey: "budgets",
  },
  {
    label: "Reports",
    path: "/reports",
    icon: <AssessmentIcon aria-hidden="true" />,
    translationKey: "reports",
  },
  {
    label: "SavingPlans",
    path: "/saving-plans",
    icon: <SavingsIcon aria-hidden="true" />,
    translationKey: "saving_plans",
  },
  {
    label: "Debts",
    path: "/debts",
    icon: <HandshakeIcon aria-hidden="true" />,
    translationKey: "debts",
  },
];

