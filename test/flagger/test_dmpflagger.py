#! /usr/bin/env python
# -*- coding: utf-8 -*-

import json
import pandas as pd

from ..common import initData, initMeta, initMetaDict
from saqc.core.core import runner
from saqc.flagger.dmpflagger import DmpFlagger
from saqc.flagger.dmpflagger import FlagFields as F
from saqc.core.config import Fields


def test_basic():

    flagger = DmpFlagger()
    data = initData()
    var1, var2, *_ = data.columns
    var1mean = data[var1].mean()
    var2mean = data[var2].mean()

    metadata = [
        {Fields.VARNAME: var1,
         "test_1": f"generic(func=this < {var1mean}, flag='DOUBTFUL')",
         "test_2": f"range(min=10, max=20, comment='saqc')"},
        {Fields.VARNAME: var2,
         "test_1": f"generic(func=this > {var1mean}, cause='error')"}
    ]

    meta_file, _ = initMetaDict(metadata, data)

    pdata, pflags = runner(meta_file, flagger, data)

    col1 = pdata[var1]
    col2 = pdata[var2]

    pflags11 = pflags.loc[col1 < var1mean, (var1, F.FLAG)]
    pflags21 = pflags.loc[col2 > var2mean, (var2, F.CAUSE)]
    pflags12 = pflags.loc[((col1 < 10) | (col1 > 20)), (var1, F.COMMENT)]
    pflags12 = pd.io.json.json_normalize(pflags12.apply(json.loads))

    assert (pflags11 > flagger.GOOD).all()
    assert set(["comment", "commit", "test"]) == set(pflags12.columns)
    assert (pflags12["comment"] == "saqc").all()
    assert (pflags21 == "error").all()


def test_flagOrder():

    data = initData()
    var, *_ = data.columns
    flagger = DmpFlagger()

    metadata = [
        {Fields.VARNAME: var,
         "test": f"generic(func=this > mean(this), flag='{flagger.BAD}')"},
        {Fields.VARNAME: var,
         "test": f"generic(func=this >= min(this), flag='{flagger.GOOD}')"},
    ]

    meta_file, _ = initMetaDict(metadata, data)

    pdata, pflags = runner(meta_file, flagger, data)

    datacol = pdata[var]
    flagcol = pflags[(var, F.FLAG)]

    assert (flagcol[datacol > datacol.mean()] == flagger.BAD).all()
    assert (flagcol[datacol <= datacol.mean()] == flagger.GOOD).all()
