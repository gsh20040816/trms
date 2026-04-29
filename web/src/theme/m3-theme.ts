import type { ThemeOptions } from "@mui/material/styles";
import { createTheme, responsiveFontSizes } from "@mui/material/styles";

// Material 3 颜色 token，源色（seed）选用与同济 ACM 品牌接近的深蓝。
// 亮色和暗色两套通过 colorSchemes 由 MUI 自动派生 surface 层级与状态层。
const m3Palette = {
  light: {
    palette: {
      mode: "light" as const,
      primary: {
        main: "#1A53A8",
        light: "#4A7BC8",
        dark: "#0F3D7E",
        contrastText: "#FFFFFF",
      },
      secondary: {
        main: "#5A6470",
        light: "#8A95A3",
        dark: "#3F4854",
        contrastText: "#FFFFFF",
      },
      error: {
        main: "#B3261E",
        light: "#DC362E",
        dark: "#8C1D18",
        contrastText: "#FFFFFF",
      },
      warning: {
        main: "#B0531A",
        light: "#D2733A",
        dark: "#7E3A0E",
        contrastText: "#FFFFFF",
      },
      success: {
        main: "#1F7A4D",
        light: "#3FA070",
        dark: "#155939",
        contrastText: "#FFFFFF",
      },
      info: {
        main: "#0B6FB8",
        light: "#3F92D2",
        dark: "#08507F",
        contrastText: "#FFFFFF",
      },
      background: {
        default: "#FBF8FD",
        paper: "#FFFFFF",
      },
      text: {
        primary: "#1A1B20",
        secondary: "#46474C",
        disabled: "#787880",
      },
      divider: "#DDE1E8",
    },
  },
  dark: {
    palette: {
      mode: "dark" as const,
      primary: {
        main: "#A8C7FA",
        light: "#CFE0FC",
        dark: "#7FA3D8",
        contrastText: "#0E2E5C",
      },
      secondary: {
        main: "#BDC4CE",
        light: "#DCE2EA",
        dark: "#8E97A2",
        contrastText: "#27303B",
      },
      error: {
        main: "#F2B8B5",
        light: "#F7D2D0",
        dark: "#C97D78",
        contrastText: "#601410",
      },
      warning: {
        main: "#F2C29A",
        light: "#F7D7B6",
        dark: "#C18E63",
        contrastText: "#5C2A03",
      },
      success: {
        main: "#A6E2BD",
        light: "#C7EED2",
        dark: "#6FB389",
        contrastText: "#0E3D24",
      },
      info: {
        main: "#A0CAFD",
        light: "#C6DEFD",
        dark: "#7BA1D5",
        contrastText: "#06365C",
      },
      background: {
        default: "#121316",
        paper: "#1C1D20",
      },
      text: {
        primary: "#E5E2E9",
        secondary: "#C7C6CD",
        disabled: "#787880",
      },
      divider: "#34353A",
    },
  },
};

const sharedThemeOptions: ThemeOptions = {
  shape: {
    borderRadius: 12,
  },
  typography: {
    fontFamily: [
      "Roboto Flex",
      "Source Han Sans SC",
      "Noto Sans SC",
      "PingFang SC",
      "Microsoft YaHei",
      "system-ui",
      "sans-serif",
    ].join(", "),
    h1: { fontSize: "3.5rem", fontWeight: 400, letterSpacing: "-0.015em", lineHeight: 1.15 },
    h2: { fontSize: "2.25rem", fontWeight: 400, letterSpacing: "-0.01em", lineHeight: 1.2 },
    h3: { fontSize: "1.75rem", fontWeight: 500, lineHeight: 1.25 },
    h4: { fontSize: "1.5rem", fontWeight: 500, lineHeight: 1.3 },
    h5: { fontSize: "1.25rem", fontWeight: 500, lineHeight: 1.35 },
    h6: { fontSize: "1.05rem", fontWeight: 600, lineHeight: 1.4 },
    button: { fontWeight: 600, textTransform: "none", letterSpacing: "0.01em" },
    body1: { fontSize: "0.95rem", lineHeight: 1.55 },
    body2: { fontSize: "0.875rem", lineHeight: 1.5 },
  },
  shadows: [
    "none",
    "0px 1px 2px 0px rgba(15, 23, 42, 0.05)",
    "0px 1px 3px 0px rgba(15, 23, 42, 0.06), 0px 1px 2px -1px rgba(15, 23, 42, 0.04)",
    "0px 4px 8px -2px rgba(15, 23, 42, 0.08), 0px 2px 4px -2px rgba(15, 23, 42, 0.04)",
    "0px 6px 12px -3px rgba(15, 23, 42, 0.10), 0px 3px 6px -3px rgba(15, 23, 42, 0.06)",
    "0px 8px 16px -4px rgba(15, 23, 42, 0.12), 0px 4px 8px -4px rgba(15, 23, 42, 0.06)",
    "0px 10px 20px -5px rgba(15, 23, 42, 0.14), 0px 5px 10px -5px rgba(15, 23, 42, 0.08)",
    "0px 12px 24px -6px rgba(15, 23, 42, 0.16)",
    "0px 14px 28px -7px rgba(15, 23, 42, 0.18)",
    "0px 16px 32px -8px rgba(15, 23, 42, 0.20)",
    "0px 18px 36px -9px rgba(15, 23, 42, 0.22)",
    "0px 20px 40px -10px rgba(15, 23, 42, 0.24)",
    "0px 22px 44px -11px rgba(15, 23, 42, 0.26)",
    "0px 24px 48px -12px rgba(15, 23, 42, 0.28)",
    "0px 26px 52px -13px rgba(15, 23, 42, 0.30)",
    "0px 28px 56px -14px rgba(15, 23, 42, 0.32)",
    "0px 30px 60px -15px rgba(15, 23, 42, 0.34)",
    "0px 32px 64px -16px rgba(15, 23, 42, 0.36)",
    "0px 34px 68px -17px rgba(15, 23, 42, 0.38)",
    "0px 36px 72px -18px rgba(15, 23, 42, 0.40)",
    "0px 38px 76px -19px rgba(15, 23, 42, 0.42)",
    "0px 40px 80px -20px rgba(15, 23, 42, 0.44)",
    "0px 42px 84px -21px rgba(15, 23, 42, 0.46)",
    "0px 44px 88px -22px rgba(15, 23, 42, 0.48)",
    "0px 46px 92px -23px rgba(15, 23, 42, 0.50)",
  ],
  components: {
    MuiButton: {
      defaultProps: {
        disableElevation: true,
      },
      styleOverrides: {
        root: {
          borderRadius: 999,
          paddingInline: 20,
          minHeight: 40,
        },
        sizeSmall: { minHeight: 32, paddingInline: 14 },
        sizeLarge: { minHeight: 48, paddingInline: 24 },
      },
    },
    MuiCard: {
      defaultProps: { elevation: 0, variant: "outlined" },
      styleOverrides: {
        root: { borderRadius: 16 },
      },
    },
    MuiPaper: {
      styleOverrides: {
        rounded: { borderRadius: 16 },
      },
    },
    MuiAppBar: {
      defaultProps: { elevation: 0, color: "transparent" },
      styleOverrides: {
        root: ({ theme }) => ({
          backgroundColor: theme.palette.background.paper,
          borderBottom: `1px solid ${theme.palette.divider}`,
          color: theme.palette.text.primary,
        }),
      },
    },
    MuiTextField: {
      defaultProps: {
        variant: "outlined",
        size: "small",
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: { borderRadius: 12 },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { borderRadius: 8, fontWeight: 600 },
      },
    },
    MuiTooltip: {
      defaultProps: { arrow: true },
    },
    MuiTableCell: {
      styleOverrides: {
        head: ({ theme }) => ({
          fontWeight: 700,
          color: theme.palette.text.secondary,
          backgroundColor: theme.palette.action.hover,
        }),
      },
    },
  },
};

function buildThemeForMode(mode: "light" | "dark") {
  const baseTheme = createTheme({
    ...sharedThemeOptions,
    ...m3Palette[mode],
  });
  return responsiveFontSizes(baseTheme);
}

export const lightTheme = buildThemeForMode("light");
export const darkTheme = buildThemeForMode("dark");

export type AppColorScheme = "light" | "dark";

export function resolveAppColorScheme(scheme: AppColorScheme) {
  return scheme === "dark" ? darkTheme : lightTheme;
}
