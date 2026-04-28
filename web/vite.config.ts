import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

function parseDevServerPort(rawPort: string | undefined) {
  if (!rawPort) {
    return undefined;
  }

  const trimmedPort = rawPort.trim();
  if (trimmedPort.length === 0) {
    return undefined;
  }

  const port = Number.parseInt(trimmedPort, 10);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error("TRMS_WEB_PORT must be an integer between 1 and 65535");
  }

  return port;
}

export default defineConfig(({ mode }) => {
  const environmentVariables = loadEnv(mode, process.cwd(), "");
  const configuredHost = environmentVariables.TRMS_WEB_HOST?.trim();
  const configuredPort = parseDevServerPort(environmentVariables.TRMS_WEB_PORT);

  return {
    plugins: [react()],
    server: {
      host: configuredHost && configuredHost.length > 0 ? configuredHost : undefined,
      port: configuredPort,
      strictPort: configuredPort !== undefined,
    },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: "./src/test/setup.ts",
    },
  };
});
