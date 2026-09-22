---
layout: landing
---

:::{container}
:name: home-head

<div class="title-with-logo">
   <div class="brand-text">Structlog Config</div>
</div>
:::

<p class="lead" style="text-align: center; font-size: 1.25rem; color: var(--sy-c-text-muted); margin-bottom: 2rem;">
Opinionated defaults for structlog. JSON in production, one formatter for every logger, and pytest output you can hand to an LLM.
</p>

:::{container} buttons wrap
<a href="getting-started.html" class="btn-no-wrap">Get Started</a>
:::

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} {octicon}`zap` JSON in production
orjson output with sorted keys, ISO timestamps, and structured exceptions.
:::

:::{grid-item-card} {octicon}`code` One formatter
Stdlib, warnings, and plugin loggers share the same structlog pipeline.
:::

:::{grid-item-card} {octicon}`beaker` Pytest capture
Failed tests write stdout, stderr, and tracebacks for later inspection.
:::

:::{grid-item-card} {octicon}`file` Scoped teeing
Capture the logs from one call or request without a special logger.
:::
::::

```{toctree}
:maxdepth: 2
:hidden:

Getting Started <getting-started>
Examples <examples>
API Reference <autoapi/index>
Changelog <changelog>
```
