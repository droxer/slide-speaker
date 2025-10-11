'use client';

import React from 'react';
import ErrorView from '@/components/ErrorView';
import type { ErrorStageProps } from './types';

export const ErrorStage: React.FC<ErrorStageProps> = ({ onResetForm }) => {
  return <ErrorView onResetForm={onResetForm} />;
};