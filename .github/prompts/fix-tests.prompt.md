---
mode: 'agent'
description: ''
---
## Fix Tests

Focus on all unit + command tests. Make sure they pass and fix errors. If you run into anything very odd stop, and let me know. Mutate test code first and let me know if you think you should update application code.

Then, focus on integration tests in tests/integration. If an integration test fails, run it again just to be sure it wasn't a flakey test (integration tests are not deterministic). If it fails because of a visual error, check the 'tmp/test-results/playwright/' directory for a screenshot relating to the failing test that you can inspect.

For additional debugging help, view the development version of the site at `$PYTHON_TEST_SERVER_HOST` using a browser.

If you get stuck or seem to be in a loop, give me a short summary of exactly where you are running into trouble, let me know, and stop working.
