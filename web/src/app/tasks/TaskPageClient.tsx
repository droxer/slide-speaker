'use client';

import React from 'react';
import TaskDetail from '@/components/TaskDetail';
import Footer from '@/components/Footer';
import { resolveApiBaseUrl } from '@/utils/apiBaseUrl';
import { useTaskQuery, useDownloadsQuery, useCancelTaskMutation } from '@/services/queries';
import { useQueryClient } from '@tanstack/react-query';
import type { Task } from '@/types';

const apiBaseUrl = resolveApiBaseUrl();

type TaskPageClientProps = {
  taskId: string;
  initialTask: Task;
};

const TaskPageClient: React.FC<TaskPageClientProps> = ({ taskId, initialTask }) => {
  const queryClient = useQueryClient();
  const taskQuery = useTaskQuery(taskId, initialTask);
  const task = taskQuery.data;
  const downloadsQuery = useDownloadsQuery(taskId, Boolean(task));
  const cancelMutation = useCancelTaskMutation();

  const downloads = downloadsQuery.data?.items;

  const isLoading = taskQuery.isLoading;
  const isError = taskQuery.isError;

  if (isLoading && !task) {
    return (
      <div className="task-detail-page">
        <div className="content-card wide task-detail-card">
          <p className="task-detail-card__empty">Loading task…</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="task-detail-page">
        <div className="content-card wide task-detail-card">
          <p className="task-detail-card__empty">Failed to load task details. Please try again.</p>
        </div>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="task-detail-page">
        <div className="content-card wide task-detail-card">
          <p className="task-detail-card__empty">Task not found.</p>
        </div>
      </div>
    );
  }

  const handleCancel = async (id: string) => {
    if (!window.confirm('Cancel this task?')) return;
    await cancelMutation.mutateAsync(id);
    await queryClient.invalidateQueries({ queryKey: ['task', taskId] });
  };

  return (
    <>
      <TaskDetail
        task={task}
        downloads={downloads}
        apiBaseUrl={apiBaseUrl}
        onCancel={handleCancel}
        isCancelling={cancelMutation.isPending}
        downloadsLoading={downloadsQuery.isLoading}
      />
      <Footer queueUnavailable={false} redisLatencyMs={null} />
    </>
  );
};

export default TaskPageClient;
