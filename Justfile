# Set up the Python environment, done automatically for you when using direnv
setup:
    uv venv && uv sync
    @echo "activate: source ./.venv/bin/activate"

# Start docker services
up:
    docker compose up -d --wait

# Run tests
test:
    uv run pytest -v

# python linting checks
[script]
lint FILES=".":
    set +e
    exit_code=0

    if [ -n "${CI:-}" ]; then
        # CI mode: GitHub-friendly output
        uv run ruff check --output-format=github {{FILES}} || exit_code=$?
        uv run ruff format --check {{FILES}} || exit_code=$?

        uv run pyright {{FILES}} --outputjson > pyright_report.json || exit_code=$?
        jq -r \
            --arg root "$GITHUB_WORKSPACE/" \
            '
                .generalDiagnostics[] |
                .file as $file |
                ($file | sub("^\\Q\($root)\\E"; "")) as $rel_file |
                "::\(.severity) file=\($rel_file),line=\(.range.start.line),endLine=\(.range.end.line),col=\(.range.start.character),endColumn=\(.range.end.character)::\($rel_file):\(.range.start.line): \(.message)"
            ' < pyright_report.json
        rm pyright_report.json
    else
        # Local mode: regular output
        uv run ruff check {{FILES}} || exit_code=$?
        uv run ruff format --check {{FILES}} || exit_code=$?
        uv run pyright {{FILES}} || exit_code=$?
    fi

    if [ $exit_code -ne 0 ]; then
        echo "One or more linting checks failed"
        exit 1
    fi

# Automatically fix linting errors
lint-fix:
    uv run ruff check . --fix
    uv run ruff format .

# Clean build artifacts and cache
clean:
    rm -rf *.egg-info .venv || true
    find . -type f -name "*.pyc" -delete
    find . -type d -name "__pycache__" -delete || true

# Update copier template
update_copier:
    uv tool run --with jinja2_shell_extension \
        copier@latest update --vcs-ref=HEAD --trust --skip-tasks --skip-answered

GITHUB_PROTECT_MASTER_RULESET := """
{
	"name": "Protect master from force pushes",
	"target": "branch",
	"enforcement": "active",
	"conditions": {
		"ref_name": {
			"include": ["refs/heads/master"],
			"exclude": []
		}
	},
	"rules": [
		{
			"type": "non_fast_forward"
		}
	]
}
"""

_github_repo:
	gh repo view --json nameWithOwner -q .nameWithOwner

# TODO this only supports deleting the single ruleset specified above
github_ruleset_protect_master_delete:
	repo=$(just _github_repo) && \
	  ruleset_name=$(echo '{{GITHUB_PROTECT_MASTER_RULESET}}' | jq -r .name) && \
		ruleset_id=$(gh api repos/$repo/rulesets --jq ".[] | select(.name == \"$ruleset_name\") | .id") && \
		(([ -n "${ruleset_id}" ] || (echo "No ruleset found" && exit 0)) || gh api --method DELETE repos/$repo/rulesets/$ruleset_id)

# adds github ruleset to prevent --force and other destructive actions on the github main branch
github_ruleset_protect_master_create: github_ruleset_protect_master_delete
	gh api --method POST repos/$(just _github_repo)/rulesets --input - <<< '{{GITHUB_PROTECT_MASTER_RULESET}}'
