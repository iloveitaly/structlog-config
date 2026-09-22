from datetime import UTC, datetime

# 1. Basic Project Info
project = "Structlog Config"
copyright = f"{datetime.now(UTC).year}, Michael Bianco"
author = "Michael Bianco"

# 2. Extensions
# AutoAPI generates the reference from the AST, so optional extras are not imported.
# Napoleon parses the Google-style sections already used in this package's docstrings.
extensions = [
    "myst_parser",  # Enable Markdown
    "sphinx_design",  # UI Components (Grids/Cards)
    "sphinx_copybutton",  # Code copy button
    "sphinx.ext.viewcode",  # View source code
    "sphinx.ext.intersphinx",  # Link to external docs
    # Google-style Args/Returns/Examples in this package. Not an API generator.
    "sphinx.ext.napoleon",
    "autoapi.extension",  # Auto-generate API reference
    "sphinx_llm.txt",  # LLM-friendly documentation (llms.txt / llms-full.txt)
]

# Configure AutoAPI
autoapi_dirs = ["../structlog_config"]
autoapi_type = "python"
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
]
autoapi_keep_files = False

# sphinx-llm writes Markdown next to the HTML output under docs/_build.
# Sphinx 9 does not exclude _build by default, so a second build would treat
# those files as source pages and the LLM artifact step would fail.
exclude_patterns = ["_build"]

# Intersphinx configuration
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "structlog": ("https://www.structlog.org/en/stable/", None),
    "fastapi": ("https://fastapi.tiangolo.com/", None),
}
intersphinx_timeout = 10

# sphinx-llm runs a nested markdown build; keep it sequential for clearer errors
llms_txt_build_parallel = False

# 3. Markdown Support Configuration
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

myst_enable_extensions = [
    "colon_fence",  # Use ::: for directives (much cleaner MD)
    "deflist",  # Support for definition lists
    "substitution",  # Use {{ variables }} in Markdown
    "tasklist",  # Enable GitHub-style checkboxes
    "attrs_block",  # CSS classes directly in markdown
    "attrs_inline",  # CSS classes inline
    "smartquotes",  # Typographic curly quotes
]

# Support heading anchors in MyST for README includes
myst_heading_anchors = 3

# 4. Theme & Appearance (Shibuya)
html_theme = "shibuya"
html_baseurl = "https://iloveitaly.github.io/structlog-config/"
html_static_path = ["_static"]
html_extra_path = [".nojekyll"]
html_css_files = ["custom.css"]

html_theme_options = {
    "accent_color": "blue",
    "github_url": "https://github.com/iloveitaly/structlog-config",
    "nav_links": [
        {"title": "Getting Started", "url": "getting-started"},
        {"title": "Examples", "url": "examples"},
        {"title": "API Reference", "url": "autoapi/index"},
        {"title": "Changelog", "url": "changelog"},
    ],
}

# 5. sphinx-llm: publish machine-readable docs alongside HTML
llms_txt_enabled = True
llms_txt_full_build = True
llms_txt_description = (
    "structlog-config: opinionated structlog defaults for development and production. "
    "JSON logging, stdlib redirection, context and teeing, pytest failure capture, "
    "and optional FastAPI access logs."
)
