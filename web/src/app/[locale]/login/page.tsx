import LoginPageClient from './LoginPageClient';

type LoginPageProps = {
  params: {locale: string};
  searchParams?: {redirectTo?: string};
};

export default function LoginPage({params, searchParams}: LoginPageProps) {
  const redirectTo = typeof searchParams?.redirectTo === 'string' ? searchParams.redirectTo : undefined;
  return <LoginPageClient locale={params.locale} redirectTo={redirectTo} />;
}
