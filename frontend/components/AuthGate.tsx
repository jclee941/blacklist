'use client';

import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';

import { AUTH_UNAUTHORIZED_EVENT, getToken, removeToken, verifyToken } from '@/lib/api';

type AuthGateProps = {
  readonly children: ReactNode;
  readonly navigation?: ReactNode;
};

export function AuthGate({ children, navigation }: AuthGateProps) {
  const pathname = usePathname();
  const { replace } = useRouter();
  const [authenticatedPath, setAuthenticatedPath] = useState<string | null>(null);
  const isLoginRoute = pathname === '/login';

  useEffect(() => {
    if (isLoginRoute) {
      return;
    }

    let isActive = true;
    const returnToLogin = () => {
      removeToken();
      if (isActive) {
        setAuthenticatedPath(null);
        replace('/login');
      }
    };

    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, returnToLogin);
    const token = getToken();
    if (!token) {
      returnToLogin();
    } else {
      void verifyToken()
        .then((result) => {
          if (isActive && result.valid) {
            setAuthenticatedPath(pathname);
          } else {
            returnToLogin();
          }
        })
        .catch((error: unknown) => {
          if (error instanceof Error) {
            returnToLogin();
            return;
          }
          throw error;
        });
    }

    return () => {
      isActive = false;
      window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, returnToLogin);
    };
  }, [isLoginRoute, pathname, replace]);

  if (isLoginRoute) {
    return children;
  }

  if (authenticatedPath !== pathname) {
    return null;
  }

  return (
    <>
      {navigation}
      {children}
    </>
  );
}
