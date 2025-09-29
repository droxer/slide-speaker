import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import TaskPageClient from '@/app/tasks/TaskPageClient';
import { loadTaskById, taskRevalidate } from '@/app/tasks/loadTaskById';

export const revalidate = taskRevalidate;

type PageParams = {
  params: {
    taskId: string;
  };
};

export async function generateMetadata({ params }: PageParams): Promise<Metadata> {
  const task = await loadTaskById(params.taskId);
  if (!task) {
    return {
      title: 'Task Not Found • SlideSpeaker',
      description: 'The requested task could not be located.',
    };
  }

  const taskType = String(task.task_type || 'task');
  const status = String(task.status || 'unknown');
  return {
    title: `Task ${params.taskId} • ${status}`,
    description: `View details for ${taskType} task ${params.taskId}.`,
  };
}

export default async function TaskDetailPage({ params }: PageParams) {
  const { taskId } = params;
  const initialTask = await loadTaskById(taskId);

  if (!initialTask) {
    notFound();
  }

  return <TaskPageClient taskId={taskId} initialTask={initialTask} />;
}
