'use client';

import { toast } from 'react-toastify';

/**
 * Shows an error toast notification
 * @param message The error message to display
 * @param options Additional options for the toast
 */
export const showErrorToast = (message: string, options?: any) => {
  toast.error(message, {
    position: 'top-right',
    autoClose: 5000,
    hideProgressBar: false,
    closeOnClick: true,
    pauseOnHover: true,
    draggable: true,
    progress: undefined,
    ...options,
  });
};

/**
 * Shows a success toast notification
 * @param message The success message to display
 * @param options Additional options for the toast
 */
export const showSuccessToast = (message: string, options?: any) => {
  toast.success(message, {
    position: 'top-right',
    autoClose: 3000,
    hideProgressBar: false,
    closeOnClick: true,
    pauseOnHover: true,
    draggable: true,
    progress: undefined,
    ...options,
  });
};

/**
 * Shows an info toast notification
 * @param message The info message to display
 * @param options Additional options for the toast
 */
export const showInfoToast = (message: string, options?: any) => {
  toast.info(message, {
    position: 'top-right',
    autoClose: 3000,
    hideProgressBar: false,
    closeOnClick: true,
    pauseOnHover: true,
    draggable: true,
    progress: undefined,
    ...options,
  });
};

/**
 * Shows a warning toast notification
 * @param message The warning message to display
 * @param options Additional options for the toast
 */
export const showWarningToast = (message: string, options?: any) => {
  toast.warn(message, {
    position: 'top-right',
    autoClose: 4000,
    hideProgressBar: false,
    closeOnClick: true,
    pauseOnHover: true,
    draggable: true,
    progress: undefined,
    ...options,
  });
};