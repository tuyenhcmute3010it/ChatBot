import axios from 'axios';
import { HOST } from '@/constant';

export function postRAGQuestionsApiCall(data: { dataToPost: [] }) {
	const { dataToPost } = data;
	return axios({
		method: 'post',
		url: `http://127.0.0.1:5002/ask`,
		data: dataToPost,
	});
}
