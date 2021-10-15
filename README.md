JuiceFS Python SDK
===

[![Build](https://github.com/megvii-research/juicefs-python/actions/workflows/on-push.yaml/badge.svg?branch=main)](https://github.com/megvii-research/juicefs-python/actions/workflows/on-push.yaml)
[![Documents](https://github.com/megvii-research/juicefs-python/actions/workflows/publish-docs.yml/badge.svg)](https://github.com/megvii-research/juicefs-python/actions/workflows/publish-docs.yml)
[![Code Coverage](https://img.shields.io/codecov/c/gh/megvii-research/juicefs-python)](https://app.codecov.io/gh/megvii-research/juicefs-python/)
[![Latest version](https://img.shields.io/pypi/v/juicefs.svg)](https://pypi.org/project/juicefs/)
[![Support python versions](https://img.shields.io/pypi/pyversions/juicefs.svg)](https://pypi.org/project/juicefs/)
[![License](https://img.shields.io/pypi/l/juicefs.svg)](https://github.com/megvii-research/juicefs-python/blob/master/LICENSE)

- Docs: https://megvii-research.github.io/juicefs-python/

## What is this ?


[JuiceFS](https://github.com/juicedata/juicefs) is a high-performance POSIX file system released under GNU Affero General Public License v3.0.

`juicefs-python` is JuiceFS Python SDK, provides a majority of APIs in `os` module, complete APIs of `io.FileIO` and `io.open()`, based on JuiceFS APIs.

`juicefs-python` works on Linux, macOS and Windows, you can install it via PyPI, where the wheel package also includes `libjfs.so`.

## Installation

### PyPI

Use pip install JuiceFS Python SDK package:
```
pip install juicefs
```

### Build from Source

Clone the repository:

```
git clone git@github.com:megvii-research/juicefs-python.git
```

And then build `juicefs` and `libjfs.so` and install requirements:

```
cd juicefs-python
make build_juicefs
pip install -r requirements.txt
```

If you want to develop based on JuiceFS Python SDK package, you may want to `pip install -r requirements-dev.txt`.

## How to Contribute

* You can help to improve juicefs-python in many ways:
    * Write code.
    * Improve [documentation](https://github.com/megvii-research/juicefs-python/blob/main/docs).
    * Report or investigate [bugs and issues](https://github.com/megvii-research/juicefs-python/issues).
    * Review [pull requests](https://github.com/megvii-research/juicefs-python/pulls).
    * Star juicefs-python repo.
    * Recommend juicefs-python to your friends.
    * Any other form of contribution is welcomed.
* We are happy to see your contribution to juicefs-python. Before contributing to this project, you should follow these rules:
    * **Code format**: Use `make format` to format the code before pushing your code to repository.
    * **Test**:`pytest` is used to test the code in this project. You should use `make test` to do the test the code. This should be done before pushing your code, asuring bug-free code based on complete tests.
    * **Static check**:We use `pytype` to do the static check. `make static_check` can help finish static check.
    * **Others**: You can get more details in `Makefile` at the root path.

## Resources

- [JuiceFS](https://github.com/juicedata/juicefs)
- [JuiceFS Hadoop Java SDK](https://github.com/juicedata/juicefs/blob/main/docs/en/hadoop_java_sdk.md)
- [Build libjfs.so](https://github.com/megvii-research/juicefs-python/blob/main/BUILD.md)


## License

`juicefs-python` is open-sourced under GNU AGPL v3.0, see [LICENSE](https://github.com/megvii-research/juicefs-python/blob/main/LICENSE).
