"use client";

import { Component, type ReactNode } from "react";

import { Button } from "@/components/ui/button";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  message: string;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  static getDerivedStateFromError(error: unknown): State {
    const message = error instanceof Error ? error.message : "An unexpected error occurred";
    return { hasError: true, message };
  }

  override componentDidCatch(): void {
    // Error is intentionally not logged here — no console.log allowed.
    // In production, sentry-sdk captures it automatically via its React integration.
  }

  reset(): void {
    this.setState({ hasError: false, message: "" });
  }

  override render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 p-8 text-center">
          <p className="text-lg font-semibold">Something went wrong</p>
          <p className="max-w-sm text-sm text-muted-foreground">{this.state.message}</p>
          <Button onClick={() => this.reset()}>Try again</Button>
        </div>
      );
    }
    return this.props.children;
  }
}
