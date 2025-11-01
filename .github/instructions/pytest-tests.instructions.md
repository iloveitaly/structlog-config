---
applyTo: "tests/**/*.py"
---
## Pytest Tests

- Look to tests/factories.py to generate any required database state
  - Here's an example of how to create + persist a factory `DistributionFactory.save()`
- Use the `faker` factory to generate emails, etc.
- Do not mock or patch unless I instruct you to. Test as much of the application stack as possible in each test.
- If you get lazy attribute errors, or need a database session to share across logic, use the `db_session` fixture to fix the issue.
  - Note that when writing route tests a `db_session` is not needed for the logic inside of the route.
- When testing Stripe, use the sandbox API. Never mock out Stripe interactions unless explicitly told to.
- Omit obvious docstrings and comments.
