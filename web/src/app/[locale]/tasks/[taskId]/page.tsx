import {notFound, redirect} from 'next/navigation';
import {getServerSession} from 'next-auth';
import type {Metadata} from 'next';
import TaskPageClient from '../../../tasks/TaskPageClient';
import {loadTaskById} from '../../../tasks/loadTaskById';
import {loadInitialHealth} from '../../../loadInitialHealth';
import {authOptions} from '@/auth/options';

export const revalidate = 30;

type PageParams = {
  params: Promise<{
    locale: string;
    taskId: string;
  }>;
};

export async function generateMetadata({params}: PageParams): Promise<Metadata> {
  const {taskId} = await params;
  const task = await loadTaskById(taskId);
  if (!task) {
    return {
      title: 'Task Not Found • SlideSpeaker',
      description: 'The requested task could not be located.',
    };
  }

  const taskType = String(task.task_type || 'task');
  const status = String(task.status || 'unknown');
  return {
    title: `Task ${taskId} • ${status}`,
    description: `View details for ${taskType} task ${taskId}.`,
  };
}

export default async function TaskDetailPage({params}: PageParams) {
  const {locale, taskId} = await params;

  const session = await getServerSession(authOptions);
  if (!session) {
    redirect(`/login?redirectTo=/${locale}/tasks/${taskId}`);
  }

  const [initialTask, initialHealth] = await Promise.all([
    loadTaskById(taskId),
    loadInitialHealth(),
  ]);

  if (!initialTask) {
    notFound();
  }

  return (
    <TaskPageClient
      taskId={taskId}
      initialTask={initialTask}
      initialHealth={initialHealth}
    />
  );
}
