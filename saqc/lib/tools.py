#! /usr/bin/env python
# -*- coding: utf-8 -*-

import re
from typing import Sequence, Union, Any, Iterator

import numpy as np
import numba as nb
import pandas as pd

import dios
import inspect

# from saqc.flagger import BaseFlagger
from saqc.lib.types import T


def assertScalar(name, value, optional=False):
    if (not np.isscalar(value)) and (value is not None) and (optional is True):
        raise ValueError(f"'{name}' needs to be a scalar or 'None'")
    elif (not np.isscalar(value)) and optional is False:
        raise ValueError(f"'{name}' needs to be a scalar")


def toSequence(value: Union[T, Sequence[T]], default: Union[T, Sequence[T]] = None) -> Sequence[T]:
    if value is None:
        value = default
    if np.isscalar(value):
        value = [value]
    return value


@nb.jit(nopython=True, cache=True)
def findIndex(iterable, value, start):
    i = start
    while i < len(iterable):
        v = iterable[i]
        if v >= value:
            return i
        i = i + 1
    return -1


@nb.jit(nopython=True, cache=True)
def valueRange(iterable):
    minval = iterable[0]
    maxval = minval
    for v in iterable:
        if v < minval:
            minval = v
        elif v > maxval:
            maxval = v
    return maxval - minval


def slidingWindowIndices(dates, window_size, iter_delta=None):
    """
    this function is a building block of a custom implementation of
    the pandas 'rolling' method. A number of shortcomings in the
    'rolling' implementation might made this a worthwhil endavour,
    namly:
    + There is no way to provide a step size, i.e. to not start the
      next rolling window at the very next row in the DataFrame/Series
    + The inconsistent bahaviour with numerical vs frequency based
      window sizes. When winsz is an integer, all windows are equally
      large (winsz=5 -> windows contain 5 elements), but variable in
      size, when the winsz is a frequency string (winsz="2D" ->
      window grows from size 1 during the first iteration until it
      covers the given frequency). Especially the bahaviour with
      frequency strings is quite unfortunate when calling methods
      relying on the size of the window (sum, mean, median)
    """

    if not isinstance(dates, pd.DatetimeIndex):
        raise TypeError("Must pass pd.DatetimeIndex")

    # lets work on numpy data structures for performance reasons
    dates = np.array(dates, dtype=np.int64)

    if np.any(np.diff(dates) <= 0):
        raise ValueError("strictly monotonic index needed")

    window_size = pd.to_timedelta(window_size).to_timedelta64().astype(np.int64)
    if iter_delta:
        iter_delta = pd.to_timedelta(iter_delta).to_timedelta64().astype(np.int64)

    start_date = dates[0]
    last_date = dates[-1]
    start_idx = 0
    end_idx = start_idx

    while True:
        end_date = start_date + window_size
        if (end_date > last_date) or (start_idx == -1) or (end_idx == -1):
            break

        end_idx = findIndex(dates, end_date, end_idx)
        yield start_idx, end_idx

        if iter_delta:
            start_idx = findIndex(dates, start_date + iter_delta, start_idx)
        else:
            start_idx += 1

        start_date = dates[start_idx]


def inferFrequency(data: pd.Series) -> pd.DateOffset:
    return pd.tseries.frequencies.to_offset(pd.infer_freq(data.index))


def retrieveTrustworthyOriginal(
    data: dios.DictOfSeries, field: str, flagger=None, level: Any = None
) -> dios.DictOfSeries:
    """Columns of data passed to the saqc runner may not be sampled to its original sampling rate - thus
    differenciating between missng value - nans und fillvalue nans is impossible.

    This function:
    (1) if flagger is None:
        (a) estimates the sampling rate of the input dataseries by dropping all nans and then returns the series at the
            estimated samplng rate.

    (2) if "flagger" is not None but "level" is None:
        (a) all values are dropped, that are flagged worse then flagger.GOOD. (so unflagged values wont be dropped)
        (b) estimates the sampling rate of the input dataseries by dropping all nans and then returns the series at the
            estimated samplng rate.
    (3) if "flagger" is not None and "level" is not None:
        (a) all values are dropped, that are flagged worse then level. (so unflagged values wont be dropped)
        (b) estimates the sampling rate of the input dataseries by dropping all nans and then returns the series at the
            estimated samplng rate.

    Note, that the passed dataseries should be harmonized to an equidistant
        frequencie grid (maybe including blow up entries).

    :param data:        DataFrame. The Data frame holding the data containing 'field'.
    :param field:       String. Fieldname of the column in data, that you want to sample to original sampling rate.
                        It has to have a harmonic
    :param flagger:     None or a flagger object.
    :param level:       Lower bound of flags that are excepted for data. Must be a flag the flagger can handle.

    """
    dataseries = data[field]

    if flagger is not None:
        mask = flagger.isFlagged(field, flag=level or flagger.GOOD, comparator="<=")
        # drop all flags that are suspicious or worse
        dataseries = dataseries[mask]

    # drop the nan values that may result from any preceeding upsampling of the measurements:
    dataseries = dataseries.dropna()

    if dataseries.empty:
        return dataseries, np.nan

    # estimate original data sampling frequencie
    # (the original series sampling rate may not match data-input sample rate):
    seconds_rate = dataseries.index.to_series().diff().min().seconds
    data_rate = pd.tseries.frequencies.to_offset(str(seconds_rate) + "s")

    return dataseries.asfreq(data_rate), data_rate


def offset2seconds(offset):
    """Function returns total seconds upon "offset like input

    :param offset:  offset string or pandas offset object.
    """

    return pd.Timedelta.total_seconds(pd.Timedelta(offset))


def flagWindow(flagger_old, flagger_new, field, direction="fw", window=0, **kwargs) -> pd.Series:
    # NOTE: unused -> remove?
    if window == 0 or window == "":
        return flagger_new

    fw, bw = False, False
    mask = flagger_old.getFlags(field) != flagger_new.getFlags(field)
    f = flagger_new.isFlagged(field) & mask

    if not mask.any():
        # nothing was flagged, so nothing need to be flagged additional
        return flagger_new

    if isinstance(window, int):
        x = f.rolling(window=window + 1).sum()
        if direction in ["fw", "both"]:
            fw = x.fillna(method="bfill").astype(bool)
        if direction in ["bw", "both"]:
            bw = x.shift(-window).fillna(method="bfill").astype(bool)
    else:
        # time-based windows
        if direction in ["bw", "both"]:
            # todo: implement time-based backward rolling
            raise NotImplementedError
        fw = f.rolling(window=window, closed="both").sum().astype(bool)

    fmask = bw | fw
    return flagger_new.setFlags(field, fmask, **kwargs)


def seasonalMask(dtindex, season_start, season_end, include_bounds):
    """
    This function generates date-periodic/seasonal masks from an index passed.

    For example you could mask all the values of an index, that are sampled in winter, or between 6 and 9 o'clock.
    See the examples section for more details.

    Parameters
    ----------
    dtindex : pandas.DatetimeIndex
        The index according to wich you want to generate a mask.
        (=resulting mask will be indexed with 'dtindex')
    season_start : str
        String denoting starting point of every period. Formally, it has to be a truncated instance of "mm-ddTHH:MM:SS".
        Has to be of same length as `season_end` parameter.
        See examples section below for some examples.
    season_end : str
        String denoting starting point of every period. Formally, it has to be a truncated instance of "mm-ddTHH:MM:SS".
        Has to be of same length as `season_end` parameter.
        See examples section below for some examples.
    include_bounds : {"mask","season"}
        - "mask": the `season_start` and `season_end` keywords inclusivly frame the mask (INCLUDING INTERVAL BOUNDS)
        - "season": the `season_start` and `season_end` keywords inclusivly frame the season
        (INCLUDING INTERVAL BOUNDS)
        (Parameter mainly introduced to provide backwards compatibility. But, as a side effect, provides more control
        over what to do with samples at the exact turning points of date-defined masks and season.)

    Returns
    -------
    to_mask : pandas.Series[bool]
        A series, indexed with the input index and having value `True` for all the values that are to be masked.

    Examples
    --------
    The `season_start` and `season_end` parameters provide a conveniant way to generate seasonal / date-periodic masks.
    They have to be strings of the forms: "mm-ddTHH:MM:SS", "ddTHH:MM:SS" , "HH:MM:SS", "MM:SS" or "SS"
    (mm=month, dd=day, HH=hour, MM=minute, SS=second)
    Single digit specifications have to be given with leading zeros.
    `season_start` and `seas   on_end` strings have to be of same length (refer to the same periodicity)
    The highest date unit gives the period.
    For example:

    >>> season_start = "01T15:00:00"
    >>> season_end = "13T17:30:00"

    Will result in all values sampled between 15:00 at the first and  17:30 at the 13th of every month get masked

    >>> season_start = "01:00"
    >>> season_end = "04:00"

    All the values between the first and 4th minute of every hour get masked.

    >>> season_start = "01-01T00:00:00"
    >>> season_end = "01-03T00:00:00"

    Mask january and february of evcomprosed in theery year. masking is inclusive always, so in this case the mask will
    include 00:00:00 at the first of march. To exclude this one, pass:

    >>> season_start = "01-01T00:00:00"
    >>> season_end = "02-28T23:59:59"

    To mask intervals that lap over a seasons frame, like nights, or winter, exchange sequence of season start and
    season end. For example, to mask night hours between 22:00:00 in the evening and 06:00:00 in the morning, pass:

    >>> season_start = "22:00:00"
    >>> season_end = "06:00:00"

    When inclusive_selection="season", all above examples work the same way, only that you now
    determine wich values NOT TO mask (=wich values are to constitute the "seasons").
    """
    def _replaceBuilder(stamp):
        keys = ("second", "minute", "hour", "day", "month", "year")
        stamp_list = map(int, re.split(r"[-T:]", stamp)[::-1])
        stamp_kwargs = dict(zip(keys, stamp_list))

        def _replace(index):
            if "day" in stamp_kwargs:
                stamp_kwargs["day"] = min(stamp_kwargs["day"], index[0].daysinmonth)

            out = index[0].replace(**stamp_kwargs)
            return out.strftime("%Y-%m-%dT%H:%M:%S")

        return _replace

    selectors = {"mask": False, "season": True}
    if include_bounds not in selectors:
        raise ValueError(
            f"invalid value '{include_bounds}' was passed to "
            f"parameter 'inclusive_selection'. Please select from "
            f"{list(include_bounds.keys())}."
        )
    base_bool = selectors[include_bounds]
    mask = pd.Series(base_bool, index=dtindex)

    start_replacer = _replaceBuilder(season_start)
    end_replacer = _replaceBuilder(season_end)

    if pd.Timestamp(start_replacer(dtindex)) <= pd.Timestamp(end_replacer(dtindex)):
        def _selector(x, base_bool=base_bool):
            x[start_replacer(x.index):end_replacer(x.index)] = not base_bool
            return x
    else:
        def _selector(x, base_bool=base_bool):
            x[:end_replacer(x.index)] = not base_bool
            x[start_replacer(x.index):] = not base_bool
            return x

    freq = '1' + 'mmmhhhdddMMMYYY'[len(season_start)]
    return mask.groupby(pd.Grouper(freq=freq)).transform(_selector)


def assertDictOfSeries(df: Any, argname: str = "arg") -> None:
    if not isinstance(df, dios.DictOfSeries):
        raise TypeError(f"{argname} must be of type dios.DictOfSeries, {type(df)} was given")


def assertSeries(srs: Any, argname: str = "arg") -> None:
    if not isinstance(srs, pd.Series):
        raise TypeError(f"{argname} must be of type pd.Series, {type(srs)} was given")


@nb.jit(nopython=True, cache=True)
def otherIndex(values: np.ndarray, start: int = 0) -> int:
    """
    returns the index of the first non value not equal to values[0]
    -> values[start:i] are all identical
    """
    val = values[start]
    for i in range(start, len(values)):
        if values[i] != val:
            return i
    return -1


def groupConsecutives(series: pd.Series) -> Iterator[pd.Series]:
    """
    group consecutive values into distinct pd.Series
    """
    index = series.index
    values = series.values

    start = 0
    while True:
        stop = otherIndex(values, start)
        if stop == -1:
            break
        yield pd.Series(data=values[start:stop], index=index[start:stop])
        start = stop


def mergeDios(left, right, join="merge"):
    # use dios.merge() as soon as it implemented
    # see https://git.ufz.de/rdm/dios/issues/15

    merged = left.copy()
    shared_cols = left.columns.intersection(right.columns)
    for c in shared_cols:
        l, r = left[c], right[c]
        if join == "merge":
            # NOTE:
            # our merge behavior is nothing more than an
            # outer join, where the right join argument
            # overwrites the left at the shared indices,
            # while on a normal outer join common indices
            # hold the values from the left join argument
            r, l = l.align(r, join="outer")
        else:
            l, r = l.align(r, join=join)
        merged[c] = l.combine_first(r)

    newcols = right.columns.difference(merged.columns)
    for c in newcols:
        merged[c] = right[c].copy()

    return merged


def isQuoted(string):
    return bool(re.search(r"'.*'|\".*\"", string))


def dropper(field, to_drop, flagger, default):
    drop_mask = pd.Series(False, flagger.getFlags(field).index)
    if to_drop is None:
        to_drop = default
    to_drop = toSequence(to_drop)
    if len(to_drop) > 0:
        drop_mask |= flagger.isFlagged(field, flag=to_drop)
    return drop_mask


def mutateIndex(index, old_name, new_name):
    pos = index.get_loc(old_name)
    index = index.drop(index[pos])
    index = index.insert(pos, new_name)
    return index
