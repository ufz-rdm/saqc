#! /usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd

from .reader import readConfig, prepareConfig, checkConfig
from .config import Fields
from .evaluator import evalExpression
from ..lib.plotting import plot_hook, plotall_hook
from ..flagger import BaseFlagger, CategoricalBaseFlagger, SimpleFlagger, DmpFlagger


def collectVariables(meta, data):
    """
    find every relevant variable
    """
    # NOTE: get to know every variable from meta
    flags = [] #data.columns.tolist()
    for idx, configrow in meta.iterrows():
        varname = configrow[Fields.VARNAME]
        assign = configrow[Fields.ASSIGN]
        if varname in data:
            flags.append(varname)
        elif varname not in flags and assign is True:
            flags.append(varname)
    return flags


def _check_input(data, flagger, flags):
    if not isinstance(data, pd.DataFrame):
        raise TypeError('data must be of type pd.DataFrame')

    if isinstance(data.index, pd.MultiIndex):
        raise TypeError('the index of data is not allowed to be a multiindex')

    if isinstance(data.columns, pd.MultiIndex):
        raise TypeError('the columns of data is not allowed to be a multiindex')

    if not isinstance(flagger, BaseFlagger):
        flaggerlist = [CategoricalBaseFlagger, SimpleFlagger, DmpFlagger]
        raise TypeError(f'flagger must be of type {flaggerlist} or any inherit class from {BaseFlagger}')

    if flags is None:
        return

    if not isinstance(flags, pd.DataFrame):
        raise TypeError('flags must be of type pd.DataFrame')

    if isinstance(data.index, pd.MultiIndex):
        raise TypeError('the index of data is not allowed to be a multiindex')

    if len(data) != len(flags):
        raise ValueError('the index of flags and data has not the same length')

    # do not test columns as they not necessarily must be the same


def _setup():
    pd.set_option('mode.chained_assignment', 'warn')


def runner(metafname, flagger, data, flags=None, nodata=np.nan):
    _setup()
    _check_input(data, flagger, flags)
    config = prepareConfig(readConfig(metafname), data)

    # split config into the test and some 'meta' data
    tests = config.filter(regex=Fields.TESTS)
    meta = config[config.columns.difference(tests.columns)]

    # # prepapre the flags
    # varnames = collectVariables(meta, data)
    # fresh = flagger.initFlags(pd.DataFrame(index=data.index, columns=varnames))
    # flags = fresh if flags is None else flags.join(fresh)
    if flags is None:
        flag_cols = collectVariables(meta, data)
        flagger = flagger.initFlags(pd.DataFrame(index=data.index, columns=flag_cols))
    else:
        flagger = flagger.initFromFlags(flags)


    # this checks comes late, but the compiling of the user-test need fully prepared flags
    checkConfig(config, data, flagger, nodata)

    # the outer loop runs over the flag tests, the inner one over the
    # variables. Switching the loop order would complicate the
    # reference to flags from other variables within the dataset
    for _, testcol in tests.iteritems():

        # NOTE: just an optimization
        if testcol.dropna().empty:
            continue

        for idx, configrow in meta.iterrows():
            varname = configrow[Fields.VARNAME]
            start_date = configrow[Fields.START]
            end_date = configrow[Fields.END]

            flag_test = testcol[idx]
            if pd.isnull(flag_test):
                continue

            if varname not in data and varname not in flagger.getFlags().columns:
                continue

            dchunk = data.loc[start_date:end_date]
            if dchunk.empty:
                continue

            flagger_chunk = flagger.getFlagger(loc=dchunk.index)

            dchunk, flagger_chunk_result = evalExpression(
                flag_test,
                data=dchunk, field=varname,
                flagger=flagger_chunk, nodata=nodata)

            data.loc[start_date:end_date] = dchunk
            flagger = flagger.setFlagger(flagger_chunk_result)
            # plot_hook(dchunk, fchunk, ffchunk.getFlags(), varname, configrow[Fields.PLOT], flag_test, flagger)

    # plotall_hook(data, flagger.getFlags(), flagger)

    return data, flagger
