export type LogLevel = 'trace' | 'debug' | 'info' | 'warn' | 'error';

export interface Logger {
	trace(event: string, context?: Record<string, unknown>): void;
	debug(event: string, context?: Record<string, unknown>): void;
	info(event: string, context?: Record<string, unknown>): void;
	warn(event: string, context?: Record<string, unknown>): void;
	error(event: string, context?: Record<string, unknown>): void;
}
