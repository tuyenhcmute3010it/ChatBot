// import axios from 'axios';
// import { AI_DEMOS_URI, HOST } from '@/constant';

// export function postQuestionsApiCall(data: {
// 	dataToPost: {
// 		messages: IChat[];
// 	};
// }) {
// 	const { dataToPost } = data;
// 	return axios({
// 		method: 'post',
// 		// url: `http://127.0.0.1:5000/chat`,
// 		url: `http://127.0.0.1:5000/api/search`,
// 		data: dataToPost,
// 	});
// }

import axios from 'axios';

export function postQuestionsApiCall(data: {
	dataToPost: {
		messages: {
			role: string;
			content: string;
		}[];
	};
}) {
	const { dataToPost } = data;

	const convertedMessages = dataToPost.messages.map((msg) => ({
		role: msg.role,
		parts: [{ text: msg.content }],
	}));

	console.log('📤 Dữ liệu gửi lên backend:', convertedMessages);

	return axios({
		method: 'post',
		url: `http://127.0.0.1:5002/api/search`,
		data: convertedMessages,
	})
		.then((res) => {
			console.log('📥 Phản hồi từ backend:', res.data); // << 👈 Xem log này có in không
			return res.data;
		})
		.catch((err) => {
			console.error('❌ Lỗi khi gọi API:', err);
		});
}
