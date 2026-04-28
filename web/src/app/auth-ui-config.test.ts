import { resolveAuthUiConfig } from "./auth-ui-config";

describe("resolveAuthUiConfig", () => {
  it("defaults to hiding dev auth routes in production builds", () => {
    expect(resolveAuthUiConfig({ PROD: true, MODE: "production" })).toEqual({
      enableDevRoleEntries: false,
      allowPrivilegedSelfRegistration: false,
    });
  });

  it("allows explicit override for non-production debugging", () => {
    expect(resolveAuthUiConfig({
      PROD: true,
      MODE: "production",
      VITE_ENABLE_DEV_AUTH_ROUTES: "true",
    })).toEqual({
      enableDevRoleEntries: true,
      allowPrivilegedSelfRegistration: true,
    });
  });
});
