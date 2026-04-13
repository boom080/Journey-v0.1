import React from "react";
import { AppErrorBoundary } from "./components/error-boundary";
import "./styles/main.scss";

export default function App({ children }) {
  return <AppErrorBoundary>{children}</AppErrorBoundary>;
}
