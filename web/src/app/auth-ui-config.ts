export type AuthUiEnvironment = {
  PROD?: boolean;
  MODE?: string;
  VITE_ENABLE_DEV_AUTH_ROUTES?: string;
};

export type AuthUiConfig = {
  enableDevRoleEntries: boolean;
  allowPrivilegedSelfRegistration: boolean;
};

function parseBooleanEnv(value: string | undefined) {
  if (value === undefined) {
    return null;
  }

  const normalized = value.trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(normalized)) {
    return true;
  }
  if (["0", "false", "no", "off"].includes(normalized)) {
    return false;
  }
  return null;
}

export function resolveAuthUiConfig(environment: AuthUiEnvironment = import.meta.env): AuthUiConfig {
  const explicitDevRoutes = parseBooleanEnv(environment.VITE_ENABLE_DEV_AUTH_ROUTES);
  const enableDevRoleEntries = explicitDevRoutes ?? !(environment.PROD || environment.MODE === "production");

  return {
    enableDevRoleEntries,
    allowPrivilegedSelfRegistration: enableDevRoleEntries,
  };
}
