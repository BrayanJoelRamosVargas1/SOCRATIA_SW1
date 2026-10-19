import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async headers() {
    // Public models and clips may be reused. Revalidate after one day; never cache user APIs here.
    return ["/vision/:path*", "/vendor/dh-live/:path*", "/avatars/:path*"].map(source => ({
      source,
      headers: [{key:"Cache-Control",value:"public, max-age=86400, stale-while-revalidate=604800"}],
    }));
  },
  // Optional worker threads for local environments without child-process support.
  experimental: {
    workerThreads: process.env.SOCRATIA_WORKER_THREADS === "1",
    useTypeScriptCli: process.env.SOCRATIA_WORKER_THREADS !== "1",
  },
};

export default nextConfig;

