import { createRoot } from 'react-dom/client';
import { useContext, useState } from 'react';
import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query';
import AuthContext, { AuthProvider } from '../src/context/AuthContext';

function Probe() {
  const auth = useContext(AuthContext);
  const client = useQueryClient();
  const [result, setResult] = useState('');
  const user = { firstName: 'Test', lastName: 'User', email: 'test@example.com', password: 'TestPassword123!' };
  return <>
    <button onClick={() => {
      void auth.SignUp({ user }).then(() => setResult('registered')).catch(() => setResult('failed'));
    }}>Register</button>
    <button onClick={() => {
      client.setQueryData(['wallet'], { secret: 'private user data' });
      void auth.SignIn(user).then(() => setResult('signed in'));
    }}>Login</button>
    <button onClick={auth.SignOut}>Logout</button>
    <button onClick={() => {
      void auth.refresh().then(() => setResult('refreshed')).catch(() => setResult('refresh failed'));
    }}>Refresh</button>
    <output id="auth-user">{auth.user?.email || 'anonymous'}</output>
    <output id="auth-cache">{client.getQueryData(['wallet']) ? 'cached' : 'empty'}</output>
    <output id="auth-tokens">{JSON.stringify(auth.authTokens)}</output>
    <output id="auth-result">{result}</output>
  </>;
}

export function mountAuthHarness() {
  const element = document.createElement('div');
  document.body.replaceChildren(element);
  createRoot(element).render(<QueryClientProvider client={new QueryClient()}>
    <AuthProvider><Probe /></AuthProvider>
  </QueryClientProvider>);
}
