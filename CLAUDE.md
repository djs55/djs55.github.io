# CLAUDE.md - Guidelines for working with this codebase

## Build and Testing Commands
- The site is fully static, no build commands are required
- To preview the site locally, you can use any static file server:
  - Python: `python -m http.server 8000`
  - Node.js: `npx serve`

## Site Structure
- Root directory: Main site (HTML/CSS)
- `/blogs`: Blog posts as static HTML files
- `/switch`, `/experiments`, `/cufp`, etc.: Project subfolders

## Code Style Guidelines
- HTML: Simple semantic markup, use terminal.css for styling
- Blog posts: Create HTML pages in the `/blogs` directory
- Code blocks: Use `<pre><code>` tags with proper styling
- File extensions: .html for all pages

## Content Guidelines
- Name blog posts with descriptive slugs: `topic-name.html`
- Keep URLs consistent and descriptive
- Link blog posts from blog.html
- Keep site structure simple and minimalist
- Add proper metadata (title, description, etc.) to all pages