import 'next-auth';
import 'next-auth/jwt';

declare module 'next-auth' {
  interface Session {
    user?: {
      id: string;
      email?: string | null;
      name?: string | null;
      image?: string | null;
      preferred_language?: string | null;
      preferred_theme?: string | null;
    };
  }

  interface User {
    id: string;
    email?: string | null;
    name?: string | null;
    image?: string | null;
    preferred_language?: string | null;
    preferred_theme?: string | null;
  }

  interface JWT {
    user?: {
      id: string;
      email?: string | null;
      name?: string | null;
      image?: string | null;
      preferred_language?: string | null;
      preferred_theme?: string | null;
    };
  }

  export interface NextAuthOptions extends Record<string, any> {}
}

declare module 'next-auth/jwt' {
  interface JWT {
    user?: {
      id: string;
      email?: string | null;
      name?: string | null;
      image?: string | null;
      preferred_language?: string | null;
      preferred_theme?: string | null;
    };
  }
}

declare module 'next-auth/react' {
  import type { ReactNode } from 'react';

  export function useSession(): {
    data: any;
    status: 'loading' | 'authenticated' | 'unauthenticated';
    update?: (session?: any) => Promise<any>;
  };
  export function signIn(provider?: string, options?: any): Promise<any>;
  export function signOut(options?: any): Promise<any>;
  export const SessionProvider: ({ children }: { children: ReactNode }) => JSX.Element;
}

declare module 'next-auth/providers/google' {
  const GoogleProvider: (options: any) => any;
  export default GoogleProvider;
}

declare module 'next-auth/providers/credentials' {
  const CredentialsProvider: (options: any) => any;
  export default CredentialsProvider;
}

declare module 'next-auth' {
  const NextAuth: (options: any) => any;
  export default NextAuth;
}
