from typing import NewType, cast

Version = NewType('Version', list[int | str])

def make_version(data: str) -> Version:
    def int_if_possible(x: str):
        try:
            return int(x)
        except ValueError:
            return x

    return Version([int_if_possible(x) for x in data.split('.')])

def version_to_str(v: Version) -> str:
    return '.'.join(map(str, v))
