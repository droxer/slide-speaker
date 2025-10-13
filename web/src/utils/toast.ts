'use client';

import { toast } from 'react-toastify';

const DEFAULT_TOAST_CONFIG = {
  position: 'top-right',
  autoClose: 3000,
  hideProgressBar: false,
  closeOnClick: true,
  pauseOnHover: true,
  draggable: true,
  progress: undefined,
} as const;

export const showErrorToast = (message: string, options?: any) => {
  toast.error(message, {
    ...DEFAULT_TOAST_CONFIG,
    autoClose: 5000,
    ...options,
  });
};

export const showSuccessToast = (message: string, options?: any) => {
  toast.success(message, {
    ...DEFAULT_TOAST_CONFIG,
    autoClose: 3000,
    ...options,
  });
};

export const showInfoToast = (message: string, options?: any) => {
  toast.info(message, {
    ...DEFAULT_TOAST_CONFIG,
    autoClose: 3000,
    ...options,
  });
};

export const showWarningToast = (message: string, options?: any) => {
  toast.warn(message, {
    ...DEFAULT_TOAST_CONFIG,
    autoClose: 4000,
    ...options,
  });
};