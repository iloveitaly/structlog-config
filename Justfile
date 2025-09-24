# Set up the Python environment, done automatically for you when using direnv
setup:
    uv venv && uv sync
    @echo "activate: source ./.venv/bin/activate"

# Start docker services
up:
    docker compose up -d --wait

# Clean build artifacts and cache
clean:
    rm -rf *.egg-info .venv
    find . -type d -name "__pycache__" -prune -exec rm -rf {} \; 2>/dev/null || true

# Update copier template
update_copier:
    uv tool run --with jinja2_shell_extension \
        copier@latest update --vcs-ref=HEAD --trust --skip-tasks --skip-answered
