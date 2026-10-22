import React, { createContext, useContext, useEffect, useState } from "react";
import dayjs from "dayjs";
import "dayjs/locale/vi";
import "dayjs/locale/en";
import { Language, TranslationKey, translations } from "../i18n/translations";

interface LanguageContextType {
  language: Language;
  dateFormat: string;
  setLanguage: (lang: Language) => void;
  toggleLanguage: () => void;
  t: (key: TranslationKey, params?: Record<string, string | number>) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [language, setLanguageState] = useState<Language>(() => {
    const saved = localStorage.getItem("app_language");
    if (saved === "vi" || saved === "en") return saved;
    return "vi"; // default to Vietnamese
  });

  // Universal system-wide default date format (DD/MM/YYYY) regardless of language
  const dateFormat = "DD/MM/YYYY";

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem("app_language", lang);
    dayjs.locale(lang);
  };

  const toggleLanguage = () => {
    setLanguage(language === "vi" ? "en" : "vi");
  };

  useEffect(() => {
    dayjs.locale(language);
  }, [language]);

  const t = (key: TranslationKey, params?: Record<string, string | number>): string => {
    const langDict = translations[language];
    let str: string = langDict && key in langDict ? langDict[key] : (translations.en[key] || key);
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        str = str.replace(new RegExp(`\\{${k}\\}`, "g"), String(v));
      });
    }
    return str;
  };

  return (
    <LanguageContext.Provider
      value={{ language, dateFormat, setLanguage, toggleLanguage, t }}
    >
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
};
