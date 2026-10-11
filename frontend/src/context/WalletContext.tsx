import { createContext } from "react";
interface WalletContextData {
  wallet: string;
  transactions: string;
  getWallet(authTokens: string): Promise<void>;
  getTransactions(authTokens: string): Promise<void>;
}

interface Props {
  children: React.ReactNode;
}

const WalletContext = createContext<WalletContextData>({} as WalletContextData);
export const WalletProvider = ({ children }: Props) => {
  return <>{children}</>;
};
export default WalletContext;
