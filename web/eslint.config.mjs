import eslintPluginNext from '@next/eslint-plugin-next'
import tseslint from "typescript-eslint";
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const tsconfigRootDir = resolve(__dirname);

export default [
  {
    ignores: [
      "**/node_modules/**",
      "**/.next/**",
      "out/**",
      "dist/**",
      "build/**",
      "coverage/**",
      "jest.config.js",
    ],
  },
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        project: './tsconfig.json',
        tsconfigRootDir,
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
    plugins: {
      '@next/next': eslintPluginNext,
      '@typescript-eslint': tseslint.plugin,
    },
    rules: {
      ...eslintPluginNext.configs.recommended.rules,
      ...eslintPluginNext.configs['core-web-vitals'].rules,
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-unused-vars": "off",
      "@typescript-eslint/no-unused-expressions": "off",
    },
  },
  {
    files: ["**/*.d.ts"],
    rules: {
      "@typescript-eslint/no-empty-object-type": "off",
    },
  },
];