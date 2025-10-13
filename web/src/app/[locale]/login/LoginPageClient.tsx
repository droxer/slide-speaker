'use client';

import React, { useState } from 'react';
import { signIn } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import LoginButton from '@/components/LoginButton';
import { useI18n } from '@/i18n/hooks';
import { resolveApiBaseUrl } from '@/utils/apiBaseUrl';

const API_BASE_URL = resolveApiBaseUrl();
const AUTH_BASE_URL = API_BASE_URL ? `${API_BASE_URL}/api/auth` : '/api/auth';

export type LoginPageClientProps = {
  locale: string;
  redirectTo?: string;
};

const isSafeRedirect = (value: string | undefined): value is string => {
  if (!value) return false;
  return value.startsWith('/') && !value.startsWith('//');
};

export default function LoginPageClient({ locale, redirectTo }: LoginPageClientProps) {
  const { t } = useI18n();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const redirectTarget = isSafeRedirect(redirectTo) ? redirectTo : `/${locale}`;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setMessage(null);

    try {
      if (mode === 'register') {
        const response = await fetch(`${AUTH_BASE_URL}/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        });

        if (!response.ok) {
          const data = await response.json().catch(() => ({ error: 'Registration failed' }));
          setMessage(data.error || t('auth.errors.registerFailed', undefined, 'Registration failed'));
          setLoading(false);
          return;
        }

        setMessage(t('auth.messages.registerSuccess', undefined, 'Account created. You can sign in now.'));
        setMode('login');
        setLoading(false);
        return;
      }

      const result = await signIn('credentials', {
        email,
        password,
        redirect: false,
        callbackUrl: redirectTarget,
      });

      if (result?.ok) {
        router.push(redirectTarget);
      } else {
        setMessage(t('auth.errors.invalidCredentials', undefined, 'Invalid email or password.'));
      }
    } catch (error) {
      console.error('Auth error', error);
      setMessage(t('auth.errors.generic', undefined, 'Something went wrong.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>{mode === 'login' ? t('auth.loginTitle', undefined, 'Sign in') : t('auth.registerTitle', undefined, 'Create account')}</h1>
        <form onSubmit={handleSubmit} className="auth-form">
          <label htmlFor="email">{t('auth.emailLabel', undefined, 'Email')}</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />

          <label htmlFor="password">{t('auth.passwordLabel', undefined, 'Password')}</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />

          {message && <p className="auth-message" role="alert">{message}</p>}

          <button type="submit" className="primary" disabled={loading}>
            {loading
              ? t('auth.loading', undefined, 'Please wait…')
              : mode === 'login'
              ? t('auth.loginAction', undefined, 'Sign in')
              : t('auth.registerAction', undefined, 'Create account')}
          </button>
        </form>

        <div className="auth-separator">
          <span>{t('auth.separator', undefined, 'or')}</span>
        </div>

        <LoginButton onClick={() => signIn('google', { callbackUrl: redirectTarget })} label={t('auth.loginWithGoogle', undefined, 'Sign in with Google')} />

        <button
          type="button"
          className="alternate-link"
          onClick={() => {
            setMode(mode === 'login' ? 'register' : 'login');
            setMessage(null);
          }}
        >
          {mode === 'login'
            ? t('auth.switchToRegister', undefined, "Don't have an account? Create one")
            : t('auth.switchToLogin', undefined, 'Already have an account? Sign in')}
        </button>
      </div>
    </div>
  );
}
