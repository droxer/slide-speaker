'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { showErrorToast } from '@/utils/toast';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  errorMessage?: string;
  somethingWentWrong?: string;
  tryAgain?: string;
}

interface State {
  hasError: boolean;
}

/**
 * Error boundary component that catches JavaScript errors anywhere in the child component tree,
 * logs those errors, and displays a fallback UI.
 */
class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(_: Error): State {
    // Update state so the next render will show the fallback UI.
    return { hasError: true };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
    // For now, we'll use the fallback text since this is a class component
    // and getting i18n here is complex. The parent component should handle i18n.
    showErrorToast('An unexpected error occurred. Please try again.');
  }

  public render() {
    if (this.state.hasError) {
      // You can render any custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }
      
      return (
        <div className="error-boundary">
          <h2>{this.props.somethingWentWrong || 'Something went wrong.'}</h2>
          <button onClick={() => this.setState({ hasError: false })}>
            {this.props.tryAgain || 'Try again?'}
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;