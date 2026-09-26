import type { NextConfig } from "next";

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
];

const nextConfig: NextConfig = {
  reactCompiler: true,
  agentRules: false,
  // Standalone output is what the container image runs.
  output: "standalone",
  poweredByHeader: false,
  async headers() {
    // The notebook runtime is framed by the Notebooks page on the same origin, so only that path allows framing.
    return [
      { source: "/((?!jupyterlite).*)", headers: securityHeaders },
      { source: "/jupyterlite/:path*", headers: [...securityHeaders.filter((h) => h.key !== "X-Frame-Options"), { key: "X-Frame-Options", value: "SAMEORIGIN" }] },
    ];
  },
};

export default nextConfig;
