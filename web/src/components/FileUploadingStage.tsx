'use client';

import React from 'react';
import FileUploadingView from '@/components/FileUploadingView';
import type { FileUploadingStageProps } from './types';

export const FileUploadingStage: React.FC<FileUploadingStageProps> = ({
  progress,
  fileName,
  fileSize,
  summaryItems,
  outputs,
}) => {
  return (
    <FileUploadingView
      progress={progress}
      fileName={fileName}
      fileSize={fileSize}
      summaryItems={summaryItems}
      outputs={outputs}
    />
  );
};
