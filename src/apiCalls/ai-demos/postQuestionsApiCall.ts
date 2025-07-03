export async function postQuestionsApiCall(data: {
	dataToPost: {
		messages: {
			role: string;
			content: string;
		}[];
	};
	onChunk: (text: string) => void;
}) {
	const { dataToPost, onChunk } = data;

	const convertedMessages = dataToPost.messages.map((msg) => ({
		role: msg.role,
		parts: [{ text: msg.content }],
	}));

	console.log('📤 Dữ liệu gửi lên backend:', convertedMessages);

	const response = await fetch(`http://127.0.0.1:5002/api/search`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify(convertedMessages),
	});

	if (!response.ok || !response.body) {
		throw new Error('Phản hồi từ server không hợp lệ');
	}

	const reader = response.body.getReader();
	const decoder = new TextDecoder('utf-8');
	let fullText = '';

	while (true) {
		const { done, value } = await reader.read();
		if (done) break;

		const chunk = decoder.decode(value, { stream: true });
		fullText += chunk;
		onChunk(chunk);
	}

	return {
		role: 'model',
		parts: [{ text: fullText }],
	};
}
