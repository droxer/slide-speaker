import {cookies} from 'next/headers';
import resolveServerApiBaseUrl from '@/utils/serverApiBaseUrl';
import type {ProfileResponse, UserProfile} from '@/types/user';

export async function loadCurrentUser(): Promise<UserProfile | null> {
  const baseUrl = resolveServerApiBaseUrl();
  const cookieStore = await cookies();
  const cookieHeader = cookieStore
    .getAll()
    .map(({name, value}) => `${name}=${value}`)
    .join('; ');

  const headers: Record<string, string> = {Accept: 'application/json'};
  if (cookieHeader) {
    headers.Cookie = cookieHeader;
  }

  const response = await fetch(`${baseUrl}/api/users/me`, {
    headers,
    credentials: 'include',
    cache: 'no-store',
  });

  if (!response.ok) {
    return null;
  }

  const data = (await response.json()) as ProfileResponse;
  return data.user;
}
