# CLAUDE.md - Guidelines for working with this codebase

## Build and Testing Commands
- Run Jekyll blog locally: `cd blog && bundle exec jekyll serve`
- Install Jekyll dependencies: `cd blog && bundle install`
- Update gems: `cd blog && bundle update`
- Preview site at: http://localhost:4000/

## Site Structure
- Root directory: Main site (HTML/CSS)
- `/blog`: Jekyll blog
- `/switch`, `/experiments`, `/cufp`, etc.: Project subfolders

## Code Style Guidelines
- HTML: Simple semantic markup, use terminal.css for styling
- Blog posts: Use Jekyll markdown with front matter
- Code blocks: Use Jekyll highlight tags `{% highlight language %}`
- File extensions: .html for HTML, .markdown for blog posts

## Content Guidelines
- Jekyll blog posts format: `YYYY-MM-DD-title.markdown`
- Blog post front matter includes title, layout, categories, etc.
- Keep site structure simple and minimalist