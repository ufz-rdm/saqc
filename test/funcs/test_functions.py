#! /usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
import numpy as np
import pandas as pd

from saqc.flagger.baseflagger import BaseFlagger
from saqc.flagger.dmpflagger import DmpFlagger
from saqc.flagger.simpleflagger import SimpleFlagger

from saqc.funcs.functions import flagRange, flagSesonalRange, forceFlags, clearFlags

TESTFLAGGERS = [
    BaseFlagger(['NIL', 'GOOD', 'BAD']),
    DmpFlagger(),
    SimpleFlagger()]
from test.common import initData, TESTFLAGGER


@pytest.fixture
def data():
    return initData(cols=1, start_date="2016-01-01", end_date="2018-12-31", freq="1D")


@pytest.fixture
def field(data):
    return data.columns[0]

    flags = flagger.initFlags(data)
    # test
    data, flags = flagRange(data, flags, field, flagger, min=10, max=90)
    flagged = flagger.isFlagged(flags[field])
    assert len(flags[flagged]) == 10 + 10


@pytest.mark.parametrize('flagger', TESTFLAGGERS)
def test_flagSesonalRange(flagger):
    # prepare
    field = 'testdata'
    index = pd.date_range(start='2011-01-01', end='2014-12-31', freq='1d')
    d = [(x % 2) * 50 for x in range(index.size)]
    data = pd.DataFrame(data={field: d}, index=index)
    flags = flagger.initFlags(data)

    # test
    kwargs = dict(min=1, max=100, startmonth=7, startday=1, endmonth=8, endday=31)
    data, flags = flagSesonalRange(data, flags, field, flagger, **kwargs)
    flagged = flagger.isFlagged(flags[field])
    assert len(flags[flagged]) == (31 + 31) * 4 / 2

    flags = flagger.initFlags(data)
    kwargs = dict(min=1, max=100, startmonth=12, startday=16, endmonth=1, endday=15)
    _, flags = flagSesonalRange(data, flags, field, flagger, **kwargs)
    flagged = flagger.isFlagged(flags[field])
    assert len(flags[flagged]) == 31 * 4 / 2


@pytest.mark.parametrize('flagger', TESTFLAGGER)
def test_clearFlags(data, field, flagger):
    orig = flagger.initFlags(data)
    flags = flagger.setFlags(orig.copy(), field, flag=flagger.BAD)
    _, cleared = clearFlags(data, flags, field, flagger)
    assert np.all(orig != flags)
    assert np.all(orig == cleared)


@pytest.mark.parametrize('flagger', TESTFLAGGER)
def test_forceFlags(data, flagger):
    field, *_ = data.columns
    flags = flagger.setFlags(flagger.initFlags(data), field)
    orig = flags.copy()
    _, forced = forceFlags(data, flags, field, flagger, flag=flagger.GOOD)
    assert np.all(flagger.getFlags(orig) != flagger.getFlags(forced))
