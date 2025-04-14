# Changelog

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
