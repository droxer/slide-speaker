import CreationsPageClient from './CreationsPageClient';
import { loadInitialHealth, healthRevalidate } from '../loadInitialHealth';

export const revalidate = healthRevalidate;

export default async function CreationsPage() {
  const initialHealth = await loadInitialHealth();
  return <CreationsPageClient initialHealth={initialHealth} />;
}
