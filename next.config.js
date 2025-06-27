/** @type {import('next').NextConfig} */
const nextConfig = {
	webpack: function (config) {
		config.module.rules.push({
			test: /\.md$/,
			use: 'raw-loader',
		});
		return config;
	},
	output: 'standalone',
	images: {
		remotePatterns: [
			{
				protocol: 'https',
				hostname: 'storage.googleapis.com',
				port: '',
				pathname: '/protonx-cloud-storage/cropped-cropped-ProtonX-logo-1-1-300x100.png',
			},
			{
				protocol: 'https',
				hostname: 'oaidalleapiprodscus.blob.core.windows.net',
				port: '',
			},
			{
				protocol: 'https',
				hostname: 'ssg.vn', // 👈 Thêm dòng này
				port: '',
				pathname: '/wp-content/uploads/**', // wildcard cho ảnh từ ssg.vn
			},
			{
				protocol: 'https',
				hostname: 'digitalbiz.com.vn', // 👈 THÊM domain mới này
				port: '',
				pathname: '/wp-content/uploads/**', // hoặc '/**' để an toàn
			},
		],
	},
	eslint: {
		// Warning: This allows production builds to successfully complete even if
		// your project has ESLint errors.
		ignoreDuringBuilds: true,
	},
	typescript: {
		// !! WARN !!
		// Dangerously allow production builds to successfully complete even if
		// your project has type errors.
		// !! WARN !!
		ignoreBuildErrors: true,
	},
};

module.exports = nextConfig;
