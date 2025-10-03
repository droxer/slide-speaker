import type {NextAuthOptions} from 'next-auth';
import GoogleProvider from 'next-auth/providers/google';
import CredentialsProvider from 'next-auth/providers/credentials';
import {resolveServerApiBaseUrl} from '@/utils/serverApiBaseUrl';

const API_BASE_URL = resolveServerApiBaseUrl();

const AUTH_BASE_URL = `${API_BASE_URL.replace(/\/$/, '')}/api/auth`;

const providers: NextAuthOptions['providers'] = [];

if (process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET) {
  providers.push(
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
    }),
  );
}

providers.push(
  CredentialsProvider({
    name: 'Credentials',
    credentials: {
      email: {label: 'Email', type: 'email'},
      password: {label: 'Password', type: 'password'},
    },
    async authorize(credentials) {
      const email = credentials?.email?.toLowerCase();
      const password = credentials?.password;
      if (!email || !password) {
        return null;
      }

      const response = await fetch(`${AUTH_BASE_URL}/login`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({email, password}),
      });

      if (!response.ok) {
        return null;
      }

      const data = (await response.json()) as {user?: any};
      if (!data.user) {
        return null;
      }

      return {
        id: data.user.id,
        email: data.user.email,
        name: data.user.name,
        image: data.user.picture,
        preferred_language: data.user.preferred_language,
      };
    },
  }),
);

export const authOptions: NextAuthOptions = {
  providers,
  session: {
    strategy: 'jwt',
  },
  pages: {
    signIn: '/login',
  },
  callbacks: {
    async signIn({user, account, profile}) {
      if (account?.provider === 'google' && user?.email) {
        try {
          await fetch(`${AUTH_BASE_URL}/oauth/google`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
              id: user.id || profile?.sub,
              email: user.email,
              name: user.name,
              picture: user.image,
            }),
          });
        } catch (error) {
          console.error('Failed to sync Google user', error);
        }
      }
      return true;
    },
    async jwt({token, user}) {
      if (user) {
        token.user = {
          id: user.id,
          email: user.email,
          name: user.name,
          image: (user as any).image,
          preferred_language: (user as any).preferred_language,
        };
      }
      return token;
    },
    async session({session, token}) {
      if (token.user) {
        session.user = token.user as any;
      }
      return session;
    },
  },
};
