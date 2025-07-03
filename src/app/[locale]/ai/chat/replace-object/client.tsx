'use client';
import { useState } from 'react';

export default function CrawlPage() {
	const [url, setUrl] = useState('');
	const [topic, setTopic] = useState('');
	const [loading, setLoading] = useState(false);
	const [result, setResult] = useState(null);

	const handleCrawl = async () => {
		setLoading(true);
		setResult(null);
		try {
			const res = await fetch('http://127.0.0.1:8000/crawl', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ urls: [url], topic }), // ✅ Sửa tại đây
			});

			const data = await res.json();
			if (res.ok) {
				setResult({ success: true, message: 'Đã lưu thành công!' });
			} else {
				setResult({ success: false, message: data.detail || 'Lỗi không xác định' });
			}
		} catch (err) {
			setResult({ success: false, message: err.message });
		}
		setLoading(false);
	};

	return (
		<div style={{ maxWidth: 600, margin: 'auto', padding: 32 }}>
			<h1>Cào dữ liệu từ Website</h1>
			<div style={{ marginBottom: 16 }}>
				<label>Link bài viết:</label>
				<input
					type='text'
					value={url}
					onChange={(e) => setUrl(e.target.value)}
					placeholder='https://example.com/...'
					style={{ width: '100%', padding: 8 }}
				/>
			</div>

			<div style={{ marginBottom: 16 }}>
				<label>Chủ đề (topic):</label>
				<input
					type='text'
					value={topic}
					onChange={(e) => setTopic(e.target.value)}
					placeholder='vd: skincare, niacinamide'
					style={{ width: '100%', padding: 8 }}
				/>
			</div>

			<button
				onClick={handleCrawl}
				disabled={loading}
				className={`rounded-lg px-6 py-2 font-semibold text-white shadow-md transition-all duration-200
    ${loading ? 'cursor-not-allowed bg-gray-400' : 'bg-green-500 hover:scale-105 hover:bg-green-600'}`}>
				{loading ? 'Đang xử lý...' : 'Cào & Lưu lên DB'}
			</button>

			{result && (
				<div style={{ marginTop: 20, color: result.success ? 'green' : 'red' }}>
					{result.message}
				</div>
			)}
		</div>
	);
}
