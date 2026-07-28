type E2ECredentials = {
  readonly username: string;
  readonly password: string;
};

export function getE2ECredentials(): E2ECredentials {
  const username = process.env.E2E_USERNAME;
  const password = process.env.E2E_PASSWORD;

  if (!username || !password) {
    throw new Error('E2E_USERNAME and E2E_PASSWORD must be set for authenticated E2E tests.');
  }

  return { username, password };
}
