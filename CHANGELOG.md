# Changelog

## [0.6.0](https://github.com/iloveitaly/structlog-config/compare/v0.5.0...v0.6.0) (2025-11-01)


### Features

* **pytest_plugin:** support persistent logs dir and test coverage ([1212de9](https://github.com/iloveitaly/structlog-config/commit/1212de9132a6ed6c089b5ba7c5af2b63c515ca97))
* **pytest-plugin:** add per-test log capture and print on failure ([7315e0e](https://github.com/iloveitaly/structlog-config/commit/7315e0e561ff169c89c00ab1379579f3742717a6))


### Bug Fixes

* use fastapi-ipware for client IP extraction in logger ([137896f](https://github.com/iloveitaly/structlog-config/commit/137896fa3b213e67493f294dd201b0559cead731))


### Documentation

* add new coding rules, prompts, and instructions for dev workflow ([f233418](https://github.com/iloveitaly/structlog-config/commit/f233418f836ce2ea664b567b4df2f62aeed3e81b))
* **pytest_plugin:** expand usage docs and clarify plugin behavior ([ff5db76](https://github.com/iloveitaly/structlog-config/commit/ff5db7649d88c61573a5421608b693afc35f1676))

## [0.5.0](https://github.com/iloveitaly/structlog-config/compare/v0.4.2...v0.5.0) (2025-10-31)


### Features

* **levels:** add is_debug_level and improve level comparison ([e19c196](https://github.com/iloveitaly/structlog-config/commit/e19c1961fbef71791d7560fb07d4e20a2637ccb6))

## [0.4.2](https://github.com/iloveitaly/structlog-config/compare/v0.4.1...v0.4.2) (2025-09-26)


### Bug Fixes

* do not require fastapi in order to use this package ([3d5cb8f](https://github.com/iloveitaly/structlog-config/commit/3d5cb8f9de2907f89fce7cf8ac72773983ce933f))

## [0.4.1](https://github.com/iloveitaly/structlog-config/compare/v0.4.0...v0.4.1) (2025-09-24)


### Bug Fixes

* expose client_ip_from_request function in main package ([#47](https://github.com/iloveitaly/structlog-config/issues/47)) ([78cc727](https://github.com/iloveitaly/structlog-config/commit/78cc727099bea5682c445f42b034fe4b22b57ed4))
* remove unused get_client_addr function from fastapi_access_logger ([#46](https://github.com/iloveitaly/structlog-config/issues/46)) ([29060a2](https://github.com/iloveitaly/structlog-config/commit/29060a2983b06d35100744ca738df02647434e78))


### Documentation

* Add concise "JSON Logging for Production" documentation ([#45](https://github.com/iloveitaly/structlog-config/issues/45)) ([03cae6d](https://github.com/iloveitaly/structlog-config/commit/03cae6d40884f3040e531121e5653f4b36d257f2))

## [0.4.0](https://github.com/iloveitaly/structlog-config/compare/v0.3.0...v0.4.0) (2025-09-24)


### Features

* improved client IP extraction with ipware for FastAPI access logger ([#39](https://github.com/iloveitaly/structlog-config/issues/39)) ([facdd36](https://github.com/iloveitaly/structlog-config/commit/facdd360d591e66156c530b287cefc6c90a913be))

## [0.3.0](https://github.com/iloveitaly/structlog-config/compare/v0.2.0...v0.3.0) (2025-09-08)


### Features

* suppress noisy stripe info logs in stdlib config ([163ac57](https://github.com/iloveitaly/structlog-config/commit/163ac57a02b05d6c3fc07b58dbe0756809ff55b2))


### Bug Fixes

* improve static asset detection for image and icon files ([421d2e3](https://github.com/iloveitaly/structlog-config/commit/421d2e303aa174b5aa4a9f92c066e8b05fd89ad8))


### Documentation

* better usage docs ([ccc585e](https://github.com/iloveitaly/structlog-config/commit/ccc585e7e31187700892489e33a7edc7535aefb6))
* explain custom TRACE logging level and usage ([aa8afb3](https://github.com/iloveitaly/structlog-config/commit/aa8afb33e14d808db75c74a7c8f982f6ca670558))
* readme typo ([806256d](https://github.com/iloveitaly/structlog-config/commit/806256d1ee92cce870e1f8669686d05683a1dfb4))

## [0.2.0](https://github.com/iloveitaly/structlog-config/compare/v0.1.0...v0.2.0) (2025-08-05)


### Features

* add custom TRACE log level and logger extension ([73e0551](https://github.com/iloveitaly/structlog-config/commit/73e05513c24e8ffe986105753a9a8d4ae5f5f496))
* call setup_trace in configure_logger to enable tracing ([85ee622](https://github.com/iloveitaly/structlog-config/commit/85ee622ad5647c7a97032f79cb12cee9ab6bcac1))
* global level override always set on std loggers, override static overrides if lower ([a7b66ea](https://github.com/iloveitaly/structlog-config/commit/a7b66ea626829b36a46ad4f73a4f1eb5bd12ca86))
* patch structlog to support custom trace log level ([35c1dca](https://github.com/iloveitaly/structlog-config/commit/35c1dca852b1d746d3538d5082d7f5a25bedc056))


### Bug Fixes

* ensure TRACE log level is properly registered and utilized in logger ([87dc788](https://github.com/iloveitaly/structlog-config/commit/87dc788c661bff5daa7d6ed5416cdc0a98322278))
* include .js.map in static asset request detection ([ff9bb4a](https://github.com/iloveitaly/structlog-config/commit/ff9bb4a6c9cd8bde1e9989399eeb2b4efc7d334a))


### Documentation

* clarify description of PYTHONASYNCIODEBUG constant ([2e2e0e9](https://github.com/iloveitaly/structlog-config/commit/2e2e0e9c07bfe80a0ba3e3d8b7278b76619cefa4))
* ipython logging adjustment ([1990a7c](https://github.com/iloveitaly/structlog-config/commit/1990a7cc130c4e30256a19caf8079a1697d137b8))
* update README with detailed logging setup instructions ([746fb8f](https://github.com/iloveitaly/structlog-config/commit/746fb8f64b542c74041141d787b62ff084b10805))

## 0.1.0 (2025-04-14)


### Features

* add PathPrettifier for structlog path formatting ([b54bc58](https://github.com/iloveitaly/structlog-config/commit/b54bc58ef5d896675a69d809704829b3976763b7))
* add RenameField processor for log key renaming ([a07bf36](https://github.com/iloveitaly/structlog-config/commit/a07bf363aa97631978c141c7385932f76ac30398))
* add structured access logging for FastAPI requests ([37d506d](https://github.com/iloveitaly/structlog-config/commit/37d506dec89fc9c0de6a548371724c2342c0bafc))
* allow loggers to be configured from environment variables ([417acf1](https://github.com/iloveitaly/structlog-config/commit/417acf1b9f5c0219191486c26ccdf6959956f329))
* configure loggers via env variables in env_config.py ([2b920c4](https://github.com/iloveitaly/structlog-config/commit/2b920c4b0c373aabcb6b7d31503205268308ed83))
* debug log static asset requests in FastAPI logger ([d8e5ee0](https://github.com/iloveitaly/structlog-config/commit/d8e5ee01af6b4ad5027010bf459fddf55263c8fc))
* determine which optional packages are installed ([7e062e2](https://github.com/iloveitaly/structlog-config/commit/7e062e2a50902ce53295730d8ad69faa387b1997))
* improve CI workflow and project setup ([2338dd0](https://github.com/iloveitaly/structlog-config/commit/2338dd06ed1c044123a11f5cc08278130da31d21))
* update logger config for testing and add is_pytest function ([fe579ca](https://github.com/iloveitaly/structlog-config/commit/fe579ca8c0210934ca7d85294b6d3b5a1d567c68))


### Bug Fixes

* dynamically pull the LOG_LEVEL from env for testing ([0cceb7c](https://github.com/iloveitaly/structlog-config/commit/0cceb7c541bd3f2d03ccf71392ee56ba5ae7f0bd))
* ensure copier uses current HEAD for updates ([20b9f9d](https://github.com/iloveitaly/structlog-config/commit/20b9f9d64f7c09d22d149162af332954cad5d070))


### Documentation

* add comments to middleware and formatter functions ([bf43006](https://github.com/iloveitaly/structlog-config/commit/bf43006ad538aa9e369c9a9fa251161feee0ea77))
* add FastAPI access logger section to README.md ([93c6d98](https://github.com/iloveitaly/structlog-config/commit/93c6d98e5441f6f4c5e69dc9c618dfcfb556e7f4))
* elaborate on FastAPI Access Logger usage and benefits ([aa4223e](https://github.com/iloveitaly/structlog-config/commit/aa4223e9db3726d5c12e699116ab84063103765b))
* update project description and keywords in pyproject.toml ([6424d8a](https://github.com/iloveitaly/structlog-config/commit/6424d8a440d474a8feb4c8ddff322b2e17241126))
