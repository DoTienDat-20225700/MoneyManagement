import axios from "axios";
const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8008/api";

export const api = axios.create({
  baseURL: BASE_URL,
});

export const apiPrivate = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});
