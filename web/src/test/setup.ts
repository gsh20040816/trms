import "@testing-library/jest-dom";

// Keep frontend tests environment-agnostic even when the repo root .env
// points VITE_API_BASE_URL at a concrete local backend port for development.
const mutableImportMetaEnv = import.meta.env as Record<string, string | boolean | undefined>;
mutableImportMetaEnv.VITE_API_BASE_URL = "/api";
