import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // [ZERO HARDCODING]: The frontend compiles to static assets.
  // It will be mounted directly by the FastAPI backend.
  output: 'export'
};

export default nextConfig;
