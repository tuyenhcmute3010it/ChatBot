import axios from 'axios';
import { AI_DEMOS_URI, HOST } from '@/constant';

export function postLangChainQuestionsApiCall(data: {
	dataToPost: {
		messages: IChat[];
	};
}) {
	const { dataToPost } = data;
	return axios({
		method: 'post',
		// url: `https://localhost:5001/chat`,
		url: `https://473b-34-138-247-133.ngrok-free.app/chat`,
		data: dataToPost,
	});
}
