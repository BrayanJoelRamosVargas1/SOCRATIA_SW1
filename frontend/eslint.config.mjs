import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

export default defineConfig([
  ...nextVitals,
  ...nextTypescript,
  // Third-party licensed runtimes; application adapters are linted normally.
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts", "src/vendor/**", "public/vision/**", "public/vendor/dh-live/js/**"]),
]);

