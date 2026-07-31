import { vi } from 'vitest';

const mocks = vi.hoisted(() => {
  const apiInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  };
  const collectionInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  };
  const create = vi.fn().mockReturnValueOnce(apiInstance).mockReturnValueOnce(collectionInstance);

  return { apiInstance, collectionInstance, create };
});

vi.mock('axios', () => ({
  default: {
    create: mocks.create,
    isAxiosError: (error: unknown) =>
      typeof error === 'object' && error !== null && 'response' in error,
  },
}));

export const getMocks = () => mocks;
export const getResponseErrorHandler = () =>
  mocks.apiInstance.interceptors.response.use.mock.calls[0]?.[1];
