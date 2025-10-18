'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { showErrorToast } from '@/utils/toast';
import { useI18n } from '@/i18n/hooks';

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
        <div className="error-boundary" role="alert">
          <div className="error-boundary-content">
            <h2 className="error-boundary-title">
              {this.props.somethingWentWrong || 'Something went wrong.'}
            </h2>
            <p className="error-boundary-message">
              {this.props.errorMessage || 'An unexpected error occurred. Please try again.'}
            </p>
            <button
              className="error-boundary-button"
              onClick={() => this.setState({ hasError: false })}
            >
              {this.props.tryAgain || 'Try again?'}
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Wrapper component to provide i18n support
export function ErrorBoundaryWithI18n({ children }: { children: ReactNode }) {
  const { t } = useI18n();

  return (
    <ErrorBoundary
      somethingWentWrong={t('errorBoundary.somethingWentWrong', undefined, 'Something went wrong.')}
      errorMessage={t('errorBoundary.unexpectedError', undefined, 'An unexpected error occurred. Please try again.')}
      tryAgain={t('errorBoundary.tryAgain', undefined, 'Try again?')}
    >
      {children}
    </ErrorBoundary>
  );
}

export default ErrorBoundary;