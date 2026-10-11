# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

- First release.
- `Deadline`: a monotonic time budget with `remaining`, `expired`, `sleep` (never
  oversleeps past the deadline) and `raise_if_expired`.
- `DeadlineExpired`: the default error raised when a deadline has passed.
