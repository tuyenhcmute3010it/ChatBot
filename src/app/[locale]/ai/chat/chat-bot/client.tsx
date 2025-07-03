'use client';

import React, { useRef, useState } from 'react';
import PageWrapper from '@/components/layouts/PageWrapper/PageWrapper';
import { useFormik } from 'formik';
import Container from '@/components/layouts/Container/Container';
import AIChatContainerCommon from '@/app/[locale]/ai/_common/AIChatContainer.common';
import AIChatItemContainerCommon from '@/app/[locale]/ai/_common/AIChatItemContainer.common';
import Button from '@/components/ui/Button';
import LoaderDotsCommon from '@/components/LoaderDots.common';
import AIChatInputContainerCommon from '@/app/[locale]/ai/_common/AIChatInputContainer.common';
import FieldWrap from '@/components/form/FieldWrap';
import Input from '@/components/form/Input';
import { ASSISTANT, CREATED, FAILED, PENDING, SUCCESSFUL, SYSTEM, USER } from '@/constant';
import { postQuestionsApiCall } from '@/apiCalls/ai-demos/postQuestionsApiCall';
import Subheader, { SubheaderRight } from '@/components/layouts/Subheader/Subheader';

const ChatBotClient = () => {
	const [listQuestions, setListQuestions] = useState([
		{
			role: SYSTEM,
			content: 'How would you like me to help you?',
		},
	] as IChat[]);
	const [askGptApiStatus, setAskGptApiStatus] = useState(CREATED);
	const stopGeneratingRef = useRef(false);

	const formik = useFormik({
		onSubmit(): void | Promise<never> {
			return undefined;
		},
		initialValues: {
			textField: '',
		},
	});

	const sendQuestionOnClick = async (question: string) => {
		try {
			stopGeneratingRef.current = false;

			if (!question) return;

			formik.resetForm();
			setAskGptApiStatus(PENDING);

			const newUserMessage: IChat = {
				role: USER,
				content: question,
			};

			const updatedList = [...listQuestions, newUserMessage];
			setListQuestions(updatedList);

			let streamedContent = ''; // Tích lũy phản hồi
			let newMessage: IChat = {
				role: ASSISTANT,
				content: '',
			};
			setListQuestions((prev) => [...prev, newMessage]);

			await postQuestionsApiCall({
				dataToPost: { messages: updatedList },
				onChunk: (chunk: string) => {
					if (stopGeneratingRef.current) return;
					streamedContent += chunk;
					newMessage.content = streamedContent;

					// Cập nhật realtime nội dung message cuối cùng
					setListQuestions((prev) => {
						const temp = [...prev];
						temp[temp.length - 1] = { ...newMessage };
						return temp;
					});
				},
			});

			setAskGptApiStatus(SUCCESSFUL);
		} catch (err) {
			console.error('❌ Error in sendQuestionOnClick:', err);
			setAskGptApiStatus(FAILED);
		}
	};

	// Function to send feedback to the backend
	const sendFeedback = async (message: string, feedback: 'like' | 'dislike') => {
		try {
			console.log('🟢 Sending feedback...');
			console.log('Message:', message);
			console.log('Feedback:', feedback);

			const response = await fetch('http://127.0.0.1:5002/api/feedback', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ message, feedback }),
			});

			console.log('🔵 Response status:', response.status);

			if (!response.ok) {
				const errorData = await response.text();
				console.error('❌ Failed to send feedback:', errorData);
				throw new Error('Failed to send feedback');
			}

			console.log(`✅ Feedback (${feedback}) sent successfully`);
		} catch (error) {
			console.error('❌ Error sending feedback:', error);
		}
	};

	const generateChat = (questions: IChat[]) => {
		let content = <div />;
		if (questions && questions?.length > 0) {
			content = (
				<AIChatContainerCommon>
					{questions?.map((question, index) => {
						return (
							<AIChatItemContainerCommon
								key={`${question?.content}-${index}`} // Ensure unique key
								content={question?.content}
								userName={question?.role === USER ? 'You' : 'AI'}
								isAnswer={
									question?.role === SYSTEM || question?.role === ASSISTANT
								}>
								{/* Add Like/Dislike buttons only for AI responses */}
								{(question?.role === ASSISTANT || question?.role === SYSTEM) && (
									<div className='mt-2 flex gap-2'>
										<Button
											icon='HeroThumbUp'
											size='sm'
											variant='outline'
											onClick={() => sendFeedback(question.content, 'like')}
											aria-label='Like this response'>
											Like
										</Button>
										<Button
											icon='HeroThumbDown'
											size='sm'
											variant='outline'
											onClick={() =>
												sendFeedback(question.content, 'dislike')
											}
											aria-label='Dislike this response'>
											Dislike
										</Button>
									</div>
								)}
							</AIChatItemContainerCommon>
						);
					})}
					{askGptApiStatus === PENDING && !stopGeneratingRef.current && (
						<AIChatItemContainerCommon isAnswer>
							<div className='grid grid-cols-12 items-center'>
								<div className='col-auto flex'>
									<LoaderDotsCommon />
								</div>
								<div className='col-auto flex'>
									<Button
										className='whitespace-nowrap !px-0'
										size='xs'
										color='red'
										onClick={() => {
											stopGeneratingRef.current = true;
											setAskGptApiStatus(FAILED);
										}}
										icon='HeroStop'
									/>
								</div>
							</div>
						</AIChatItemContainerCommon>
					)}
				</AIChatContainerCommon>
			);
		}
		return content;
	};

	const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
		if (e?.key === 'Enter' && !e?.shiftKey && formik.values?.textField) {
			sendQuestionOnClick(formik.values?.textField);
		}
	};

	return (
		<PageWrapper>
			<Subheader>
				<SubheaderRight>
					<Button
						variant='solid'
						onClick={() =>
							setListQuestions([
								{
									role: SYSTEM,
									content: 'How would you like me to help you?',
								},
							])
						}
						icon='HeroPlus'>
						New Chat
					</Button>
				</SubheaderRight>
			</Subheader>
			<Container
				className='flex shrink-0 grow basis-auto flex-col pb-0'
				style={{ fontSize: '16px', fontWeight: '500' }}>
				{generateChat(listQuestions)}
				<AIChatInputContainerCommon>
					<FieldWrap
						firstSuffix={
							<Button
								icon='HeroPlus'
								variant={formik.values.textField ? 'default' : 'solid'}
								rounded='rounded'
								className='me-2'
								aria-label='Upload file'
							/>
						}
						lastSuffix={
							formik.values?.textField ? (
								<Button
									className='ms-2'
									variant='solid'
									onClick={() => sendQuestionOnClick(formik.values?.textField)}
									rounded='rounded'
									icon='HeroPaperAirplane'>
									Send
								</Button>
							) : (
								<Button
									className='ms-2'
									icon='HeroMicrophone'
									aria-label='Speaking'
								/>
							)
						}>
						<Input
							id='textField'
							name='textField'
							dimension='xl'
							placeholder='Ask something'
							onChange={formik.handleChange}
							value={formik.values.textField}
							onKeyDown={handleKeyDown}
						/>
					</FieldWrap>
				</AIChatInputContainerCommon>
			</Container>
		</PageWrapper>
	);
};

export default ChatBotClient;
