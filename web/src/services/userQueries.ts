import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { getCurrentUserProfile, updateCurrentUserProfile } from './client';
import type { ProfileResponse } from '@/types/user';

// Query key for user profile
export const userProfileQueryKey = ['user', 'profile'] as const;

// Prefetch user profile for better performance
export const prefetchUserProfile = async (qc: any) => {
  return qc.prefetchQuery({
    queryKey: userProfileQueryKey,
    queryFn: getCurrentUserProfile,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useUserProfileQuery = () => {
  return useQuery<ProfileResponse>({
    queryKey: userProfileQueryKey,
    queryFn: getCurrentUserProfile,
    staleTime: 5 * 60 * 1000, // 5 minutes
    // Disable polling when page is not visible to enable bfcache
    refetchIntervalInBackground: false,
  });
};

export const useUpdateUserProfileMutation = () => {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: updateCurrentUserProfile,
    onSuccess: (updatedProfile) => {
      // Update the cache with the new profile data
      qc.setQueryData(userProfileQueryKey, updatedProfile);
    },
  });
};