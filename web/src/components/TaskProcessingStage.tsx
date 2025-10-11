'use client';

import React from 'react';
import TaskProcessingSteps from '@/components/TaskProcessingSteps';
import type { TaskProcessingStageProps } from './types';

export const TaskProcessingStage: React.FC<TaskProcessingStageProps> = ({
  taskId,
  fileId,
  fileName,
  progress,
  onStop,
  processingDetails,
  formatStepNameWithLanguages,
}) => {
  if (!processingDetails) return null;

  return (
    <TaskProcessingSteps
      taskId={taskId}
      fileId={fileId}
      fileName={fileName}
      progress={progress}
      onStop={onStop}
      processingDetails={processingDetails}
      formatStepNameWithLanguages={formatStepNameWithLanguages}
    />
  );
};
