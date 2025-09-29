import StudioPageClient from './StudioPageClient';
import { loadInitialHealth, healthRevalidate } from './loadInitialHealth';

export const revalidate = healthRevalidate;

export default async function StudioPage() {
  const initialHealth = await loadInitialHealth();
  return <StudioPageClient initialHealth={initialHealth} />;
}
