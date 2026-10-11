import { TextField } from "@mui/material";
import Autocomplete from "@mui/material/Autocomplete";
import CircularProgress from "@mui/material/CircularProgress";
import { useQuery } from "@tanstack/react-query";
import React, { useState } from "react";
import { useWallet } from "../hooks/api/useWallet";
import { CustomLabel } from "../models/CustomLabel";
import { useLanguage } from "../context/LanguageContext";

interface Props {
  onChange: any;
  value: CustomLabel | null;
  helperText?: string;
  error?: boolean;
}

export default function AsyncAutocomplete(props: Props) {
  const { t } = useLanguage();
  const { getWallet } = useWallet();
  const [open, setOpen] = useState(false);

  const { data: wallet, isLoading } = useQuery({
    queryKey: ["wallet"],
    queryFn: () => getWallet(),
    enabled: true,
  });

  return (
    <Autocomplete
      size="small"
      loading={isLoading}
      open={open}
      onOpen={() => setOpen(true)}
      onClose={() => setOpen(false)}
      options={wallet?.labels ?? []}
      getOptionLabel={(option) =>
        typeof option === "string" ? option : option?.name ?? ""
      }
      isOptionEqualToValue={(option, value) =>
        !value || option.id === value?.id || option.name === value?.name
      }
      onChange={(_, data) => props.onChange(data)}
      value={props.value}
      renderInput={(params) => (
        <TextField
          {...params}
          label={t("label")}
          error={props.error}
          helperText={props.helperText}
          InputProps={{
            ...params.InputProps,
            endAdornment: (
              <React.Fragment>
                {isLoading ? (
                  <CircularProgress color="inherit" size={20} />
                ) : null}
                {params.InputProps.endAdornment}
              </React.Fragment>
            ),
          }}
        />
      )}
      fullWidth
    />
  );
}
