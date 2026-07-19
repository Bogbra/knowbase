type LogLevel = "debug" | "info" | "warn" | "error";

const isDev = process.env["NODE_ENV"] === "development";

function log(level: LogLevel, message: string, meta?: Record<string, unknown>): void {
  if (level === "debug" && !isDev) return;

  const entry = {
    level,
    message,
    timestamp: new Date().toISOString(),
    ...meta,
  };

  if (typeof window === "undefined") {
    // Server-side: write to stdout/stderr as JSON
    const output = JSON.stringify(entry) + "\n";
    if (level === "error" || level === "warn") {
      process.stderr.write(output);
    } else {
      process.stdout.write(output);
    }
  }
  // Client-side: intentionally silent in production; dev gets nothing (no console.log)
}

export const logger = {
  debug: (message: string, meta?: Record<string, unknown>) => log("debug", message, meta),
  info: (message: string, meta?: Record<string, unknown>) => log("info", message, meta),
  warn: (message: string, meta?: Record<string, unknown>) => log("warn", message, meta),
  error: (message: string, meta?: Record<string, unknown>) => log("error", message, meta),
};
