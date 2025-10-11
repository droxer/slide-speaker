import LoginPageClient from './LoginPageClient';

type LoginPageProps = {
  params: Promise<{locale: string}>;
  searchParams?: Promise<{redirectTo?: string}>;
};

export default async function LoginPage({params, searchParams}: LoginPageProps) {
  const {locale} = await params;
  const query = searchParams ? await searchParams : undefined;
  const redirectTo = typeof query?.redirectTo === 'string' ? query.redirectTo : undefined;
  return <LoginPageClient locale={locale} redirectTo={redirectTo} />;
}
