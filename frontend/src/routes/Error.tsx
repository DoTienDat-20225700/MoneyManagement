import { Link, useRouteError } from "react-router-dom";
import { useLanguage } from "../context/LanguageContext";
import { Button } from "@mui/material";

function Error() {
  const error: any = useRouteError();
  const { t } = useLanguage();

  return (
    <div id="error-page" className="text-white flex flex-col justify-center items-center gap-3 mt-40">
      <span className="text-gray-500 text-8xl font-logo">{error?.status || 500}</span>
      <h1 className="mt-5 text-2xl font-bold">Oops!</h1>
      <p>{t("err_unexpected")}</p>
      <p className="text-gray-500">
        <i>{error?.statusText || error?.message}</i>
      </p>
      <Link to="/" style={{ marginTop: "1rem" }}>
        <Button variant="contained" color="primary">
          {t("back_to_home")}
        </Button>
      </Link>
    </div>
  );
}

export default Error;
