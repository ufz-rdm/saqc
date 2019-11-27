#!/usr/bin/env python

from functools import partial
from inspect import signature


class Partial(partial):
    def __init__(self, func, *args, **kwargs):
        self._signature = signature(func)

    @property
    def signature(self):
        return tuple(self._signature.parameters.keys())


# NOTE: will be filled by calls to register
FUNC_MAP = {}


def register(name):
    def outer(func):
        func = Partial(func, func_name=name)
        FUNC_MAP[name] = func

        def inner(*args, **kwargs):
            return func(*args, **kwargs)

        return inner

    return outer
