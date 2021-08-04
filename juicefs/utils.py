import os
from typing import Optional


def create_os_error(
    code: int, filename: Optional[str] = None, filename2: Optional[str] = None
):
    args = [code, os.strerror(code)]
    if filename is not None:
        args.append(filename)
    if filename2 is not None:
        args.append(None)
        args.append(filename2)
    return OSError(*args)


def check_juicefs_error(
    code: int, filename: Optional[str] = None, filename2: Optional[str] = None
):
    if code < 0:
        # juicefs 返回的错误码是负数
        raise create_os_error(-code, filename, filename2)
