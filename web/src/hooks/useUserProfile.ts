import {useQuery, useQueryClient} from '@tanstack/react-query';
import {getCurrentUserProfile, updateCurrentUserProfile} from '@/services/client';
import type {ProfileResponse} from '@/types/user';

// Query key for user profile
export const userProfileQueryKey = ['user', 'profile'];

// Prefetch user profile for better performance
export const prefetchUserProfile = async (queryClient: any) => {
  await queryClient.prefetchQuery({
    queryKey: userProfileQueryKey,
    queryFn: getCurrentUserProfile,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export function useUserProfile() {
  const queryClient = useQueryClient();

  const profileQuery = useQuery<ProfileResponse>({
    queryKey: userProfileQueryKey,
    queryFn: getCurrentUserProfile,
    staleTime: 5 * 60 * 1000, // 5 minutes
    // Disable polling when page is not visible to enable bfcache
    refetchIntervalInBackground: false,
  });

  // Prefetch user profile when the hook is used
  const prefetch = () => {
    prefetchUserProfile(queryClient).catch(console.warn);
  };

  return {
    ...profileQuery,
    prefetch,
  };
}

export function useUpdateUserProfile() {
  const queryClient = useQueryClient();

  return async (payload: {name?: string | null; preferred_language?: string | null}) => {
    const updatedProfile = await updateCurrentUserProfile(payload);
    // Update the cache with the new profile data
    queryClient.setQueryData(userProfileQueryKey, updatedProfile);
    return updatedProfile;
  };
}