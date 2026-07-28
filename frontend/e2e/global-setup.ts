export default function globalSetup(): void {
  if (!process.env.E2E_USERNAME || !process.env.E2E_PASSWORD) {
    throw new Error('E2E_USERNAME and E2E_PASSWORD must be set before running E2E tests.');
  }
}
