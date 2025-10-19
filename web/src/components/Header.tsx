import React, {useEffect, useMemo, useRef, useState, lazy, Suspense} from 'react';
import {useSession, signIn, signOut} from 'next-auth/react';
import {useRouter} from 'next/navigation';
import {useI18n} from '@/i18n/hooks';

// Lazy load non-critical components
const LoginButton = lazy(() => import('./LoginButton'));

export type AppView = 'studio' | 'creations' | 'profile';

type HeaderProps = {
  activeView: AppView;
  onNavigate: (view: AppView) => void;
};

const Header = ({ activeView, onNavigate }: HeaderProps) => {
  const { data: session, status } = useSession();
  const { t, locale } = useI18n();
  const router = useRouter();

  const currentLocale = useMemo(() => {
    if (typeof locale === 'string' && locale.trim().length > 0) {
      return locale.trim();
    }
    return 'en';
  }, [locale]);

  const user = session?.user;
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  const primaryName = useMemo(() => {
    const name = typeof user?.name === 'string' ? user.name.trim() : '';
    if (name.length > 0) {
      return name;
    }
    const email = typeof user?.email === 'string' ? user.email.trim() : '';
    if (email.length > 0) {
      return email;
    }
    return t('header.defaultName', undefined, 'there');
  }, [user?.name, user?.email, t]);

  const initials = useMemo(() => {
    const source = (user?.name || user?.email || '').trim();
    if (!source) return '🙂';
    const parts = source.split(/\s+/).filter(Boolean);
    if (parts.length === 0 && user?.email) {
      return user.email.slice(0, 2).toUpperCase();
    }
    if (parts.length === 1) {
      return parts[0].slice(0, 2).toUpperCase();
    }
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }, [user?.name, user?.email]);

  useEffect(() => {
    if (!menuOpen) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMenuOpen(false);
      }
    };
    window.addEventListener('mousedown', handleClickOutside);
    window.addEventListener('keydown', handleEscape);
    return () => {
      window.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('keydown', handleEscape);
    };
  }, [menuOpen]);

  const handleCredentialsLogin = () => {
    router.push('/login');
  };

  const navigateToProfile = () => {
    setMenuOpen(false);
    router.push(`/${currentLocale}/profile`);
  };

  return (
    <header className="app-header" role="banner">
      <div className="header-content">
        <div className="header-left">
          {status === 'loading' ? (
            <div className="user-chip user-chip--loading" aria-live="polite">
              <div className="user-chip__avatar" aria-hidden="true">🙂</div>
              <div className="user-chip__text">
                <span className="user-chip__name">{t('header.welcomeShort', {name: '…'}, 'Hi, …')}</span>
              </div>
            </div>
          ) : user ? (
            <div className="user-chip" ref={menuRef}>
              <button
                type="button"
                className="user-menu-trigger"
                onClick={() => setMenuOpen((prev) => !prev)}
                aria-haspopup="menu"
                aria-expanded={menuOpen}
              >
                <span className="user-chip__avatar" aria-hidden="true">{initials}</span>
                <span className="user-chip__text">
                  <span className="user-chip__name">{primaryName}</span>
                  {user.email && <span className="user-chip__email">{user.email}</span>}
                </span>
                <span className="user-menu-icon" aria-hidden="true">▾</span>
              </button>
              {menuOpen && (
                <div className="user-menu" role="menu">
                  <button type="button" role="menuitem" onClick={navigateToProfile}>
                    {t('header.profile', undefined, 'Profile')}
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setMenuOpen(false);
                      void signOut({callbackUrl: `/${currentLocale}`});
                    }}
                  >
                    {t('header.menu.logout', undefined, 'Sign out')}
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="auth-buttons">
              <Suspense fallback={<div className="login-button-loading">Loading...</div>}>
                <LoginButton onClick={() => signIn('google')} label={t('header.login')} />
              </Suspense>
              <button type="button" className="credentials-login-button" onClick={handleCredentialsLogin}>
                {t('auth.usePassword', undefined, 'Use email & password')}
              </button>
            </div>
          )}
        </div>
        <div className="header-center">
          <h1>SlideSpeaker AI</h1>
          <p>{t('header.subtitle')}</p>
        </div>
        <div className="header-right">
          <div
            className="view-toggle ai-toggle"
            role="tablist"
            aria-label="View Toggle"
          >
            <button
              type="button"
              onClick={() => onNavigate('studio')}
              className={`toggle-btn ${activeView === 'studio' ? "active" : ""}`}
              title={t('header.view.studio')}
              role="tab"
              aria-selected={activeView === 'studio'}
              aria-controls="studio-panel"
              id="studio-tab"
            >
              <span className="toggle-icon" aria-hidden="true">
                ▶
              </span>
              <span className="toggle-text">{t('header.view.studio')}</span>
            </button>
            <button
              type="button"
              onClick={() => onNavigate('creations')}
              className={`toggle-btn ${activeView === 'creations' ? "active" : ""}`}
              title={t('header.view.creations')}
              role="tab"
              aria-selected={activeView === 'creations'}
              aria-controls="monitor-panel"
              id="monitor-tab"
            >
              <span className="toggle-icon" aria-hidden="true">
                🎬
              </span>
              <span className="toggle-text">{t('header.view.creations')}</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
