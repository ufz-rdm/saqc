#! /usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
import numpy as np

from saqc.funcs.constants_detection import flagConstant_varianceBased

from test.common import TESTFLAGGER, initData


@pytest.fixture
def data():
    constants_data = initData(
        1, start_date="2011-01-01 00:00:00", end_date="2011-01-01 03:00:00", freq="5min"
    )
    constants_data.iloc[5:25] = 0
    return constants_data


@pytest.mark.parametrize("flagger", TESTFLAGGER)
def test_flagConstants_varianceBased(data, flagger):
    data.iloc[5:25] = 0
    expected = np.arange(5, 25)
    field, *_ = data.columns
    flagger = flagger.initFlags(data)
    data, flagger_result = flagConstant_varianceBased(
        data, field, flagger, plateau_window_min="1h"
    )
    flag_result = flagger_result.getFlags(field)
    test_sum = (flag_result[expected] == flagger.BAD).sum()
    assert test_sum == len(expected)
