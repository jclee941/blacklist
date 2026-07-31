import { describe } from 'vitest';

import { registerApiAuthFlowTests, registerApiTokenTests } from './api-auth.cases';
import { registerApiConfigurationTests, registerApiEndpointTests } from './api-endpoints.cases';
import { registerApiErrorTests, registerApiInterceptorTests } from './api-interceptors.cases';

registerApiConfigurationTests();

describe('lib/api', () => {
  registerApiTokenTests();
  registerApiInterceptorTests();
  registerApiAuthFlowTests();
  registerApiEndpointTests();
  registerApiErrorTests();
});
