<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Editor } from '@tiptap/core';
	import StarterKit from '@tiptap/starter-kit';

	/** HTML string — use bind:content from the parent */
	export let content = '';
	export let disabled = false;
	export let invalid = false;

	let editorEl: HTMLDivElement;
	let editor: Editor | undefined;
	let activeFormats = new Set<string>();

	onMount(() => {
		editor = new Editor({
			element: editorEl,
			extensions: [StarterKit],
			content,
			editable: !disabled,
			onUpdate({ editor: e }) {
				content = e.getHTML();
			},
			onTransaction({ editor: e }) {
				const next = new Set<string>();
				if (e.isActive('bold')) next.add('bold');
				if (e.isActive('italic')) next.add('italic');
				if (e.isActive('heading', { level: 2 })) next.add('h2');
				if (e.isActive('heading', { level: 3 })) next.add('h3');
				if (e.isActive('bulletList')) next.add('bulletList');
				if (e.isActive('orderedList')) next.add('orderedList');
				activeFormats = next;
			},
		});
	});

	onDestroy(() => editor?.destroy());

	$: if (editor) editor.setEditable(!disabled);

	/** Use mousedown so the editor doesn't lose focus before the command fires */
	function tool(action: () => void) {
		return (e: MouseEvent) => {
			e.preventDefault();
			if (!disabled) action();
		};
	}
</script>

<div class="editor-wrap" class:invalid class:disabled>
	<div class="toolbar" role="toolbar" aria-label="Text formatting">
		<button
			type="button"
			class="tool-btn"
			class:active={activeFormats.has('bold')}
			on:mousedown={tool(() => editor?.chain().focus().toggleBold().run())}
			title="Bold"
			{disabled}
		><strong>B</strong></button>

		<button
			type="button"
			class="tool-btn italic-btn"
			class:active={activeFormats.has('italic')}
			on:mousedown={tool(() => editor?.chain().focus().toggleItalic().run())}
			title="Italic"
			{disabled}
		><em>I</em></button>

		<div class="sep"></div>

		<button
			type="button"
			class="tool-btn"
			class:active={activeFormats.has('h2')}
			on:mousedown={tool(() => editor?.chain().focus().toggleHeading({ level: 2 }).run())}
			title="Heading 2"
			{disabled}
		>H2</button>

		<button
			type="button"
			class="tool-btn"
			class:active={activeFormats.has('h3')}
			on:mousedown={tool(() => editor?.chain().focus().toggleHeading({ level: 3 }).run())}
			title="Heading 3"
			{disabled}
		>H3</button>

		<div class="sep"></div>

		<button
			type="button"
			class="tool-btn"
			class:active={activeFormats.has('bulletList')}
			on:mousedown={tool(() => editor?.chain().focus().toggleBulletList().run())}
			title="Bullet list"
			{disabled}
		>• List</button>

		<button
			type="button"
			class="tool-btn"
			class:active={activeFormats.has('orderedList')}
			on:mousedown={tool(() => editor?.chain().focus().toggleOrderedList().run())}
			title="Numbered list"
			{disabled}
		>1. List</button>

		<div class="sep"></div>

		<button
			type="button"
			class="tool-btn"
			on:mousedown={tool(() => editor?.chain().focus().setHorizontalRule().run())}
			title="Horizontal rule"
			{disabled}
		>—</button>
	</div>

	<div bind:this={editorEl} class="editor-body"></div>
</div>

<style>
	.editor-wrap {
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		background: white;
		overflow: hidden;
		transition: border-color 0.15s;
	}

	.editor-wrap:focus-within {
		border-color: var(--color-primary);
	}

	.editor-wrap.invalid {
		border-color: var(--color-danger);
	}

	.editor-wrap.disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	/* Toolbar */
	.toolbar {
		display: flex;
		align-items: center;
		gap: 0.1rem;
		padding: 0.4rem 0.5rem;
		border-bottom: 1px solid var(--color-border);
		background: var(--color-surface);
		flex-wrap: wrap;
	}

	.tool-btn {
		padding: 0.25rem 0.55rem;
		border: 1px solid transparent;
		border-radius: calc(var(--radius) - 2px);
		background: none;
		font-size: 0.85rem;
		color: var(--color-text);
		cursor: pointer;
		transition: background 0.1s, border-color 0.1s;
		line-height: 1.4;
		font-family: inherit;
	}

	.tool-btn:hover:not(:disabled) {
		background: var(--color-bg);
		border-color: var(--color-border);
	}

	.tool-btn.active {
		background: #e8f0fe;
		border-color: #c7d9fb;
		color: var(--color-primary);
	}

	.tool-btn:disabled {
		cursor: not-allowed;
	}

	.italic-btn {
		font-style: italic;
	}

	.sep {
		width: 1px;
		height: 1.2rem;
		background: var(--color-border);
		margin: 0 0.25rem;
		flex-shrink: 0;
	}

	/* Editor area — TipTap renders inside .editor-body */
	.editor-body :global(.ProseMirror) {
		padding: 0.75rem;
		min-height: 220px;
		outline: none;
		font-size: 0.95rem;
		line-height: 1.7;
		color: var(--color-text);
	}

	.editor-body :global(.ProseMirror p) {
		margin: 0 0 0.75rem;
	}

	.editor-body :global(.ProseMirror p:last-child) {
		margin-bottom: 0;
	}

	.editor-body :global(.ProseMirror h2) {
		font-size: 1.1rem;
		font-weight: 600;
		margin: 1.25rem 0 0.4rem;
	}

	.editor-body :global(.ProseMirror h3) {
		font-size: 1rem;
		font-weight: 600;
		margin: 1rem 0 0.3rem;
	}

	.editor-body :global(.ProseMirror ul),
	.editor-body :global(.ProseMirror ol) {
		padding-left: 1.5rem;
		margin: 0 0 0.75rem;
	}

	.editor-body :global(.ProseMirror li) {
		margin-bottom: 0.2rem;
	}

	.editor-body :global(.ProseMirror strong) {
		font-weight: 600;
	}

	.editor-body :global(.ProseMirror hr) {
		border: none;
		border-top: 1px solid var(--color-border);
		margin: 1rem 0;
	}

	.editor-body :global(.ProseMirror p.is-editor-empty:first-child::before) {
		content: attr(data-placeholder);
		color: #a0aec0;
		pointer-events: none;
		float: left;
		height: 0;
	}
</style>
