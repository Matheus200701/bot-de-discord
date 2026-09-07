import './globals.css';

export const metadata = {
  title: 'Discord Commerce — Dashboard',
  description: 'Operação da Discord Commerce Platform',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="pt-BR"><body>{children}</body></html>;
}
