'use client';

import React from 'react';
import TaskDetailPage from '@/components/TaskDetailPage';
import AppShell from '@/components/AppShell';
import { resolveApiBaseUrl } from '@/utils/apiBaseUrl';
import { useTaskQuery, useDownloadsQuery, useCancelTaskMutation } from '@/services/queries';
import { useQueryClient } from '@tanstack/react-query';
import { useLocale } from 'next-intl';
import { useRouter } from '@/navigation';
import type { Task } from '@/types';
import type { HealthStatus } from '@/types/health';

const apiBaseUrl = resolveApiBaseUrl();

type TaskPageClientProps = {
  taskId: string;
  initialTask: Task;
  initialHealth?: HealthStatus | null;
};

const TaskPageClient: React.FC<TaskPageClientProps> = ({ taskId, initialTask, initialHealth = null }) => {
  const queryClient = useQueryClient();
  const router = useRouter();
  const locale = useLocale();
  const taskQuery = useTaskQuery(taskId, initialTask);
  const task = taskQuery.data;
  const downloadsQuery = useDownloadsQuery(taskId, Boolean(task));
  const cancelMutation = useCancelTaskMutation();

  const downloads = downloadsQuery.data?.items;

  const isLoading = taskQuery.isLoading;
  const isError = taskQuery.isError;

  const renderBody = () => {
    if (isLoading && !task) {
      return (
        <div className="content-card wide task-detail-card">
          <p className="task-detail-card__empty">Loading task…</p>
        </div>
      );
    }

    if (isError) {
      return (
        <div className="content-card wide task-detail-card">
          <p className="task-detail-card__empty">Failed to load task details. Please try again.</p>
        </div>
      );
    }

    if (!task) {
      return (
        <div className="content-card wide task-detail-card">
          <p className="task-detail-card__empty">Task not found.</p>
        </div>
      );
    }

    return (
      <TaskDetailPage
        task={task}
        downloads={downloads}
        apiBaseUrl={apiBaseUrl}
      />
    );
  };

  const handleCancel = async (id: string) => {
    if (!window.confirm('Cancel this task?')) return;
    await cancelMutation.mutateAsync(id);
    await queryClient.invalidateQueries({ queryKey: ['task', taskId] });
  };

  return (
    <AppShell
      activeView="creations"
      initialHealth={initialHealth}
      onNavigate={(view) => {
        if (view === 'studio') {
          router.push('/', { locale });
        }
        if (view === 'creations') {
          router.push('/creations', { locale });
        }
      }}
    >
      <div className="task-detail-page">{renderBody()}</div>
    </AppShell>
  );
};

export default TaskPageClient;
