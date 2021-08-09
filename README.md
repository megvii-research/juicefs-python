JuiceFS Python SDK
===

[![build](https://github.com/megvii-research/juicefs-python/actions/workflows/on-push.yaml/badge.svg?branch=main)](https://github.com/megvii-research/juicefs-python/actions/workflows/on-push.yaml)
[![docs](https://github.com/megvii-research/juicefs-python/actions/workflows/publish-docs.yml/badge.svg)](https://github.com/megvii-research/juicefs-python/actions/workflows/publish-docs.yml)

- Docs: https://megvii-research.github.io/juicefs-python/

## What is this ?


[JuiceFS](https://github.com/juicedata/juicefs) is a high-performance POSIX file system released under GNU Affero General Public License v3.0.

`juicefs-python` is JuiceFS Python SDK, provides a majority of APIs in `os` module, complete APIs of `io.FileIO` and `io.open()`, based on JuiceFS APIs.

Currently `juicefs-python` only works on Linux, feel free to open an issue if you want to use it on other platforms.

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

And then build `juicefs` ans `libjfs.so`:

```
cd juicefs-python
make build_juicefs
make build_libjfs
```

finally, install requirements:

```
pip install -r requirements.txt
```

If you want to develop based on JuiceFS Python SDK package, you may want to `pip install -r requirements-dev.txt`.

## Quick Start

### Configure juicefs

Before using juicefs-python, you need make sure that juicefs works.

You can get `juicefs` from https://github.com/juicedata/juicefs/releases

Command below is to create a JuiceFS named `YOUR-VOLUME-NAME`, which uses a Bucket named `YOUR-BUCKET-NAME`. 

Use your AccessKey and SecretKey substitute `YOUR-ACCESS-KEY` and `YOUR-SECRET-KEY` respectively. 

`localhost` in the command refers to the redis service.

``` shell
$ juicefs format \
    --storage s3  \
    --bucket YOUR-BUCKET-NAME \
    --access-key YOUR-ACCESS-KEY \
    --secret-key YOUR-SECRET-KEY \
    localhost YOUR-VOLUME-NAME
```

For more information, see [Juicefs Quick Start Guide](https://github.com/juicedata/juicefs/blob/main/docs/en/quick_start_guide.md) and [Juicefs Command Reference](https://github.com/juicedata/juicefs/blob/main/docs/en/command_reference.md).

### Play with juicefs-python

⚠ Caution: "read-write" mode is not supported by juicefs. May not use it so as not to cause errors.

Here's a code snippet may help you get started quickly:

```python
from juicefs import JuiceFS

# all juicefs-python APIs need a JuiceFS object at first
# Param config tells JuiceFS how to init juicefs
# config["meta"] is used to determine the local database
# config["meta"] = "" means the database is redis://127.0.0.1:6379/0 as default 
jfs = JuiceFS(name="test")
# jfs = JuiceFS(name="test", config={"meta": "other.meta.server"})

for filename in jfs.listdir("/"):
    jfs.symlink(filename, "{}.link".format(filename))

filename = "/test.file"
if not jfs.path.exists(filename):
    jfs.create(filename, 0x777)

import os
from juicefs import open as jfs_open

with jfs_open(jfs, filename, 'wb') as f:
    f.write(b'hello world')
    f.seek(0, os.SEEK_SET)
    f.write(b'hey')

with jfs_open(jfs, filename, 'rb') as f:
    assert f.read(5) == b'heylo'
    f.seek(1, os.SEEK_CUR)
    assert f.read() == b'world'
```

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
