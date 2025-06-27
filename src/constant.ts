export const PROTONX_LOGO = {
	DARK: 'https://digitalbiz.com.vn/wp-content/uploads/2023/07/dbiz-logo-512x512-1.png',
	LIGHT: 'https://digitalbiz.com.vn/wp-content/uploads/2023/07/dbiz-logo-512x512-1.png',
};

export const getHOST = () => {
	return process.env.REACT_APP_STAGE === 'production'
		? 'http://localhost:5001'
		: 'http://localhost:5001';
};

export const HOST = getHOST();

export const AI_DEMOS_URI = '/ai-demos';
export const SYSTEM = 'system';
export const ASSISTANT = 'assistant';
export const USER = 'user';

export const CREATED = 'CREATED';
export const PENDING = 'PENDING';
export const FAILED = 'FAILED';
export const SUCCESSFUL = 'SUCCESSFUL';
