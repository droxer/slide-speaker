export type UserProfile = {
  id: string;
  email: string;
  name?: string | null;
  picture?: string | null;
  preferred_language: string;
  created_at?: string | null;
  updated_at?: string | null;
};

export type ProfileResponse = {
  user: UserProfile;
};
