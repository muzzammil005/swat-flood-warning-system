/** @type {import('next').NextConfig} */
const nextConfig = {
  // Disable server-side generation for the homepage since it has client-side components
  // that depend on browser APIs
  reactStrictMode: false,  // Disable StrictMode to avoid react-leaflet double-mounting issues
  experimental: {
    esmExternals: true,
  },
  // Ensure ES modules are handled properly
  transpilePackages: ['react-leaflet', 'leaflet'],
};

export default nextConfig;