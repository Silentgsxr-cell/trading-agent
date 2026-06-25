/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Mission Control is read-only against the local trading project + vault.
  // Nothing here touches the network; everything is filesystem-driven.
};

export default nextConfig;
