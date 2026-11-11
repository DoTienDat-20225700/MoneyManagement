import { jwtDecode } from "jwt-decode";
import { createContext, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../api/services/Api";
import { User } from "../models/User";
import { UserInput } from "../routes/SignUp";

interface AuthContextData {
  user: User | null;
  SignIn({
    email,
    password,
  }: {
    email: string;
    password: string;
  }): Promise<void>;
  SignUp({ user }: { user: UserInput }): Promise<string | null>;
  SignOut(): void;
  refresh: () => Promise<string>;
  authTokens: AuthTokens | null;
  updateUser: (updated: Partial<User>) => void;
}

interface Props {
  children: React.ReactNode;
}

interface AuthTokens {
  access: string;
}

const AuthContext = createContext<AuthContextData>({} as AuthContextData);
export const AuthProvider = ({ children }: Props) => {
  const [authTokens, setAuthTokens] = useState<AuthTokens | null>(null);
  const [loggedUser, setLoggedUser] = useState<User | null>(null);
  const queryClient = useQueryClient();
  const sessionVersion = useRef(0);

  async function SignIn({
    email,
    password,
  }: {
    email: string;
    password: string;
  }) {
    try {
      const response = await api.post(
        "/token/",
        {
          email: email,
          password: password,
        },
        {
          withCredentials: true,
        }
      );
      const data = await response.data;
      setAuthTokens(data);
      setLoggedUser(jwtDecode(data.access));
    } catch (error) {
      console.log(error);
      throw error;
    }
  }

  async function SignUp({ user }: { user: UserInput }) {
    try {
      const response = await api.post("/register/", user);
      return typeof response.data === "string" ? response.data : response.data?.message ?? null;
    } catch (error) {
      console.log(error);
      throw error;
    }
  }

  function SignOut() {
    sessionVersion.current += 1;
    void api.post("/logout/", {}, { withCredentials: true })
      .catch(() => undefined)
      .finally(() => {
        setAuthTokens(null);
        setLoggedUser(null);
        void queryClient.cancelQueries();
        queryClient.clear();
      });
  }

  function updateUser(updated: Partial<User>) {
    setLoggedUser((prev) => (prev ? { ...prev, ...updated } : prev));
  }

  async function refresh() {
    const version = sessionVersion.current;
    const response = await api.post(
      "/token/refresh/",
      {},
      {
        withCredentials: true,
      }
    );
    if (version !== sessionVersion.current) {
      throw new Error("Session changed while refreshing");
    }
    setAuthTokens({
      access: response.data.access_token,
    });
    setLoggedUser(jwtDecode(response.data.access_token));
    return response.data.access_token;
  }

  return (
    <AuthContext.Provider
      value={{
        user: loggedUser,
        SignIn,
        SignUp,
        SignOut,
        refresh,
        authTokens,
        updateUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
export default AuthContext;
