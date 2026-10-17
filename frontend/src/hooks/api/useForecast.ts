import { CashFlowForecastResponse, ForecastParams } from "../../models/CashFlowForecast";
import useAxiosPrivate from "../useAxiosPrivate";

export function useForecast() {
  const axiosPrivate = useAxiosPrivate();

  async function getCashFlowForecast(params?: ForecastParams): Promise<CashFlowForecastResponse> {
    const cleanParams: Record<string, string | number> = {};
    if (params?.days) cleanParams.days = params.days;
    if (params?.safety_buffer !== undefined && params?.safety_buffer !== "") {
      cleanParams.safety_buffer = params.safety_buffer;
    }

    const response = await axiosPrivate.get("/forecast/cashflow/", { params: cleanParams });
    return response.data as CashFlowForecastResponse;
  }

  return { getCashFlowForecast };
}
