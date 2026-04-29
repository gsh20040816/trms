import React from "react";
import ReactDOM from "react-dom/client";

// Roboto Flex 是 variable font，单个 400.css 已覆盖整个字重范围。
import "@fontsource/roboto-flex/400.css";

import { App } from "./app/App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
