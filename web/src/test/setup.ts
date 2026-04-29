import "@testing-library/jest-dom";

// Keep frontend tests environment-agnostic even when the repo root .env
// points VITE_API_BASE_URL at a concrete local backend port for development.
const mutableImportMetaEnv = import.meta.env as Record<string, string | boolean | undefined>;
mutableImportMetaEnv.VITE_API_BASE_URL = "/api";

// MUI 在 jsdom 下读取 matchMedia / ResizeObserver；提供最小 polyfill 以避免运行时报错。
if (typeof window !== "undefined" && typeof window.matchMedia !== "function") {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: (query: string): MediaQueryList => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    }),
  });
}

class NoopResizeObserver {
  observe() {
    /* noop */
  }
  unobserve() {
    /* noop */
  }
  disconnect() {
    /* noop */
  }
}

if (typeof globalThis !== "undefined" && typeof (globalThis as { ResizeObserver?: unknown }).ResizeObserver !== "function") {
  (globalThis as unknown as { ResizeObserver: typeof NoopResizeObserver }).ResizeObserver = NoopResizeObserver;
}
