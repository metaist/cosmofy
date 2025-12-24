# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog] and this project adheres to [Semantic Versioning].

Sections order is: `Fixed`, `Changed`, `Added`, `Deprecated`, `Removed`, `Security`.

[keep a changelog]: http://keepachangelog.com/en/1.0.0/
[semantic versioning]: http://semver.org/spec/v2.0.0.html

---

## [Unreleased]

[unreleased]: https://github.com/metaist/cosmofy/compare/prod...main

These are changes that are on `main` that are not yet in `prod`.

---

[#14]: https://github.com/metaist/cosmofy/issues/14
[#15]: https://github.com/metaist/cosmofy/issues/15
[#16]: https://github.com/metaist/cosmofy/issues/16
[#17]: https://github.com/metaist/cosmofy/issues/17
[#18]: https://github.com/metaist/cosmofy/issues/18
[#19]: https://github.com/metaist/cosmofy/issues/19
[#20]: https://github.com/metaist/cosmofy/issues/20
[#21]: https://github.com/metaist/cosmofy/issues/21
[#24]: https://github.com/metaist/cosmofy/issues/24
[#25]: https://github.com/metaist/cosmofy/issues/25
[#27]: https://github.com/metaist/cosmofy/issues/27
[#28]: https://github.com/metaist/cosmofy/issues/28
[#29]: https://github.com/metaist/cosmofy/issues/29
[#30]: https://github.com/metaist/cosmofy/issues/30
[#31]: https://github.com/metaist/cosmofy/issues/31
[#32]: https://github.com/metaist/cosmofy/issues/32
[#33]: https://github.com/metaist/cosmofy/issues/33
[#36]: https://github.com/metaist/cosmofy/issues/35
[#36]: https://github.com/metaist/cosmofy/issues/36
[#37]: https://github.com/metaist/cosmofy/issues/37
[#38]: https://github.com/metaist/cosmofy/issues/38
[#39]: https://github.com/metaist/cosmofy/issues/39
[#40]: https://github.com/metaist/cosmofy/issues/40
[#43]: https://github.com/metaist/cosmofy/issues/43
[#46]: https://github.com/metaist/cosmofy/issues/46
[#46]: https://github.com/metaist/cosmofy/issues/46
[#48]: https://github.com/metaist/cosmofy/issues/48
[#49]: https://github.com/metaist/cosmofy/issues/49
[#50]: https://github.com/metaist/cosmofy/issues/50
[#52]: https://github.com/metaist/cosmofy/issues/52
[#53]: https://github.com/metaist/cosmofy/issues/53
[#54]: https://github.com/metaist/cosmofy/issues/54
[#55]: https://github.com/metaist/cosmofy/issues/55
[#56]: https://github.com/metaist/cosmofy/issues/56
[#57]: https://github.com/metaist/cosmofy/issues/57
[#58]: https://github.com/metaist/cosmofy/issues/58
[#59]: https://github.com/metaist/cosmofy/issues/59
[#60]: https://github.com/metaist/cosmofy/issues/60
[#61]: https://github.com/metaist/cosmofy/issues/61
[#62]: https://github.com/metaist/cosmofy/issues/62
[#63]: https://github.com/metaist/cosmofy/issues/63
[#64]: https://github.com/metaist/cosmofy/issues/64
[#66]: https://github.com/metaist/cosmofy/issues/66
[#67]: https://github.com/metaist/cosmofy/issues/67
[#69]: https://github.com/metaist/cosmofy/issues/69
[#70]: https://github.com/metaist/cosmofy/issues/70
[#71]: https://github.com/metaist/cosmofy/issues/71
[#72]: https://github.com/metaist/cosmofy/issues/72
[#73]: https://github.com/metaist/cosmofy/issues/73
[#75]: https://github.com/metaist/cosmofy/issues/75
[#77]: https://github.com/metaist/cosmofy/issues/77
[#79]: https://github.com/metaist/cosmofy/issues/79
[#81]: https://github.com/metaist/cosmofy/issues/81
[#83]: https://github.com/metaist/cosmofy/issues/83
[#86]: https://github.com/metaist/cosmofy/issues/86
[#87]: https://github.com/metaist/cosmofy/issues/87
[#89]: https://github.com/metaist/cosmofy/issues/89
[#91]: https://github.com/metaist/cosmofy/issues/91
[#92]: https://github.com/metaist/cosmofy/issues/92
[0.2.0]: https://github.com/metaist/cosmofy/compare/0.1.0...0.2.0

## [0.2.0] - 2025-12-24T03:14:02Z

This release represents a very large shift from bundling individual python files to using `uv` to bundle entire `venv` directories. The behavior of the CLI is now much more similar to `uv` in form and function.

**Fixed**

- [#14] typo in `--help`
- [#43] exclude `uv` artifacts from the bundle
- [#46] `expand_globs` to follow all (most?) of the shell rules
- [#48] getting only the project's `console_scripts`
- [#50] `cosmofy bundle --script` assumes venv in output
- [#52] avoiding clobbering logging on import
- [#56] used context handlers to close temporary directories
- [#58] self update on Windows
- [#59] assumption that `Last-Modified` will be present in headers
- [#61] replaced `PathDistribution._path` with appropriate fallbacks
- [#62] replaced `assert` for validation with actual `raise` on error
- [#66] needless `pass` in parsing args
- [#67] command names in logging
- [#70] incorrect shebang in `bundle.py`
- [#71] used context handlers to close `ZipFile` objects
- [#72] download progress indicator shouldn't divide by zero
- [#73] missing newline in `bundle.py` error message
- [#75] explicit return of default when we can't get the version from a file
- [#77] `cosmofy fs cat` usage string
- [#79] `ZipFile2.now` should not be at module-level
- [#92] use public API for `SourceFileLoader`

**Changed**

- [#16] update examples, readme, usage (HT @Pugio)
- [#28] replaced `--debug` with `--quiet` + `--verbose`
- [#29] `DEFAULT_PYTHON_URL` is now Cosmopolitan Python
- [#31] replaced `--cache` with `--no-cache` + `--cache-dir`
- [#33] refactored `bundler.py` into subcommands
- [#55] switched to JSON parsing `uv version` output
- [#57] switched to using `os.replace` for atomic file moves
- [#64] replaced `removeprefix` with better cross-platform approach
- [#79] moved progress indicator to `stderr`
- [#87] marked `cosmofy updater` commands as experimental

**Added**

- [#18] progress when downloading (HT @Pugio)
- [#32] `cosmofy bundle --script`
- [#33] `cosmofy bundle`
- [#33] `cosmofy fs add`
- [#33] `cosmofy fs args`
- [#33] `cosmofy updater remove`
- [#33] dry run banner
- [#35] `cosmofy fs ls`
- [#36] `cosmofy fs cat`
- [#37] `cosmofy fs rm`
- [#38] `cosmofy fs add -f` to overwrite files that exist
- [#39] `--color` global option
- [#40] `cosmofy self update`
- [#40] `cosmofy self version`
- [#49] `--exact` to `uv sync` for better exact specs
- [#60] timeouts to network calls
- [#81] note that concurrent removals are not supported
- [#83] missing docstrings
- [#86] log message that only GitHub URLs are inferred
- [#89] warning when adding absolute paths
- [#91] note about handling weird file names

**Removed**

- [#15] `cosmo.yaml` workflow; added `gh` command
- [#17] default `.com` extension
- [#24] support for python <= 3.9
- [#27] `--clone` is no longer supported
- [#30] `--download` is no longer supported

**Security**

- [#53] added `validate_url` to avoid non-HTTPS URLs
- [#53] added security considerations note
- [#54] removed `shell=True` in places that don't need it
- [#63] added `sanitize_zip_path` to avoid bad entry names

---

[#1]: https://github.com/metaist/cosmofy/issues/1
[#2]: https://github.com/metaist/cosmofy/issues/2
[#3]: https://github.com/metaist/cosmofy/issues/3
[#4]: https://github.com/metaist/cosmofy/issues/4
[#5]: https://github.com/metaist/cosmofy/issues/5
[#6]: https://github.com/metaist/cosmofy/issues/6
[#7]: https://github.com/metaist/cosmofy/issues/7
[#8]: https://github.com/metaist/cosmofy/issues/8
[#9]: https://github.com/metaist/cosmofy/issues/9
[#10]: https://github.com/metaist/cosmofy/issues/10
[#11]: https://github.com/metaist/cosmofy/issues/11
[#12]: https://github.com/metaist/cosmofy/issues/12
[#13]: https://github.com/metaist/cosmofy/issues/13
[0.1.0]: https://github.com/metaist/cosmofy/commits/0.1.0

## [0.1.0] - 2024-09-18T18:55:19Z

Initial release.

**Added**

- [#1], [#4], [#12]: bootstrap cosmofy to build itself
- [#2], [#6], [#8], [#9], [#13]: JSON receipt and schema
- [#3], [#5]: `--receipt-url`, `--release-url`, `--release-version`
- [#7]: `--self-update`, `--self-update --help`, `--self-update --version`
- [#10]: release notes
- [#11]: auto-upload build artifacts to GitHub Release
