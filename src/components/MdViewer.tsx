'use client';

import React, { FC, useState } from 'react';
import { Prism } from 'react-syntax-highlighter';
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import ReactMarkdown, { Options } from 'react-markdown';
import classNames from 'classnames';
import Mounted from '@/components/Mounted';
import useDarkMode from '../hooks/useDarkMode';
import Button from './ui/Button';

interface IMdViewerProps extends Partial<Options> {
	mdFile: string;
	className?: string;
}
const MdViewer: FC<IMdViewerProps> = (props) => {
	const { mdFile, className: classes } = props;

	const content = mdFile;

	const { isDarkTheme } = useDarkMode();

	const [copyOk, setCopyOk] = useState(false);
	const handleClick = () => {
		navigator.clipboard
			// eslint-disable-next-line @typescript-eslint/no-unsafe-argument,@typescript-eslint/no-unsafe-member-access,react/prop-types
			.writeText(String(content).replace(/```[^]*?\n/g, ''))
			.then(() => {})
			.catch(() => {});
		setCopyOk(true);
		setTimeout(() => {
			setCopyOk(false);
		}, 1000);
	};

	return (
		<>
			<Mounted>
				<style>{`pre>code, pre>code>span {background: transparent !important} pre>pre {margin: 0 !important; padding: 0 !important}`}</style>
			</Mounted>
			<pre className='group relative'>
				<Button
					color={copyOk ? 'emerald' : 'blue'}
					variant={copyOk ? 'solid' : 'outline'}
					icon={copyOk ? 'HeroClipboardDocumentCheck' : 'HeroClipboardDocument'}
					className='absolute right-0 scale-0 opacity-0 group-hover:scale-100 group-hover:opacity-100'
					onClick={handleClick}
				/>
				<ReactMarkdown
					className={classes}
					components={{
						code({ node, className, children, ...rest }) {
							const match = /language-(\w+)/.exec(className || '');
							return match ? (
								<Prism
									children={String(children).replace(/\n$/, '')}
									style={isDarkTheme ? oneDark : oneLight}
									customStyle={{ background: 'transparent' }}
									language={match[1]}
									{...rest}
								/>
							) : (
								<code
									className={classNames(
										'rounded bg-gray-100 px-1 py-0.5',
										className,
									)}
									{...rest}>
									{children}
								</code>
							);
						},
						h3: ({ children }) => (
							<h3 className='mb-2 mt-4 text-lg font-semibold'>{children}</h3>
						),
						ul: ({ children }) => (
							<ul className='list-inside list-disc space-y-1'>{children}</ul>
						),
						li: ({ children }) => (
							<li className='text-sm leading-relaxed'>{children}</li>
						),
						a: ({ href, children }) => (
							<a
								href={href}
								target='_blank'
								rel='noopener noreferrer'
								className='text-blue-600 underline hover:text-blue-800'>
								{children}
							</a>
						),
					}}>
					{content}
				</ReactMarkdown>
			</pre>
		</>
	);
};

export default MdViewer;
