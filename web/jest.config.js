const nextJest = require('next/jest');

const createJestConfig = nextJest({
  dir: './',
});

const customJestConfig = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^axios$': 'axios/dist/node/axios.cjs',
  },
  transformIgnorePatterns: ['node_modules/(?!axios)/'],
};

module.exports = createJestConfig(customJestConfig);
