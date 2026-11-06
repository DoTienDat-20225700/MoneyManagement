import { useEffect, useRef } from "react";
import { apiPrivate } from "../api/services/Api";
import { useAuth } from "./useAuth";

function useAxiosPrivate() {
  const { authTokens, SignOut, refresh } = useAuth();
  const refreshPromiseRef = useRef<Promise<string> | null>(null);

  useEffect(() => {
    const requestIntercept = apiPrivate.interceptors.request.use(
      (config) => {
        if (!config.headers["Authorization"]) {
          config.headers["Authorization"] = `Bearer ${authTokens?.access}`;
        }
        return config;
      },
      (err) => Promise.reject(err)
    );

    const responseIntercept = apiPrivate.interceptors.response.use(
      (response) => response,
      async (err) => {
        const prevRequest = err?.config;
        if (err?.response?.status === 401 && !prevRequest?.sent) {
          prevRequest.sent = true;
          try {
            if (!refreshPromiseRef.current) {
              refreshPromiseRef.current = refresh().finally(() => {
                refreshPromiseRef.current = null;
              });
            }
            const newAccessToken = await refreshPromiseRef.current;
            prevRequest.headers["Authorization"] = `Bearer ${newAccessToken}`;
            return apiPrivate(prevRequest);
          } catch (refreshErr) {
            SignOut();
            return Promise.reject(refreshErr);
          }
        } else if (err?.response?.status === 401 && prevRequest?.sent) {
          // Retry failed with 401 -> Session permanently invalid / user deleted
          SignOut();
          return Promise.reject(err);
        } else if (err?.response?.status === 403) {
          if (prevRequest) prevRequest.sent = true;
          SignOut();
          return Promise.reject(err);
        }
        return Promise.reject(err);
      }
    );

    return () => {
      apiPrivate.interceptors.request.eject(requestIntercept);
      apiPrivate.interceptors.response.eject(responseIntercept);
    };
  }, [authTokens, SignOut, refresh]);

  return apiPrivate;
}

export default useAxiosPrivate;
