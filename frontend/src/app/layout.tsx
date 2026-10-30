import type { Metadata, Viewport } from 'next';
import { AppRouterCacheProvider } from '@mui/material-nextjs/v15-appRouter';
import Providers from './providers';

export const metadata: Metadata = {
  title: 'Hunar.ai | Candidate Communication Platform',
  description: 'Candidate communication workspace for recruiters to manage candidates, send messages, track delivery, and view full communication history.',
};

export const viewport: Viewport = {
  themeColor: '#2196f3',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body style={{ margin: 0, padding: 0 }}>
        <AppRouterCacheProvider>
          <Providers>{children}</Providers>
        </AppRouterCacheProvider>
      </body>
    </html>
  );
}

