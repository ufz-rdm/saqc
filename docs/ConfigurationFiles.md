# Configuration Files
The behaviour of SaQC is completely controlled by a text based configuration file.

## Format
SaQC expects its configuration files to be semicolon-separated text files with a
fixed header. Each row of the configuration file lists
one variable and one or several test functions, which will be evaluated to
procduce a result for the given variable.


### Header names

The header names are basically fixed, but if you really insist in custom
configuration headers have a look [here](saqc/core/config.py).

| Name    | Data Type                                    | Description            | Optional |
|---------|----------------------------------------------|------------------------|----------|
| varname | string                                       | name of a variable     | no       |
| test    | [function notation](#test-function-notation) | test function          | no       |
| plot    | boolean (`True`/`False`)                     | plot the test's result | yes      |


### Test function notation
The notation of test functions follows the function call notation of Python and
many other programming languages and looks like this:
```
flagRange(min=0, max=100)
```
Here the function `flagRange` is called and the values `0` and `100` are passed
to the parameters `min` and `max` respectively. As we (currently) value readablity
of the configuration more than conciseness of the extrension language, only
keyword arguments are supported. That means that the notation `flagRange(0, 100)`
is not a valid replacement for the above example.

## Examples
### Single Test
Every row lists one test per variable, if you want to call multiple tests on
a specific variable (and you probably want to), list them in separate rows
```
varname | test
#-------|----------------------------------
x       | flagMissing()
x       | flagRange(min=0, max=100)
x       | constants_flagBasic(window="3h")
y       | flagRange(min=-10, max=40)
```

### Multiple Tests
A row lists multiple tests for a specific variable in separate columns. All test
columns need to share the common prefix `test`.

```
varname ; test_1                     ; test_2                    ; test_3
#-------;----------------------------;---------------------------;---------------------------------
x       ; flagMissing()              ; flagRange(min=0, max=100) ; constants_flagBasic(window="3h")
y       ; flagRange(min=-10, max=40) ;                           ;
```
The evaluation of such a configuration is in columns-major order, so the given
example is identical to the following:

```
varname ; test_1                     
#-------;---------------------------------
x       ; flagMissing()
y       ; flagRange(min=-10, max=40)
x       ; flagRange(min=0, max=100)
x       ; constants_flagBasic(window="3h")

```

### Plotting
As the process of finding a good quality check setup is somewhat experimental, SaQC
provides a possibility to plot the results of the test functions. In
order to opt-into this feture add the optional columns `plot` and set it
to `True` whenever you want to see the result of the evaluation. These plots are
meant to provide a quick and easy visual evaluation of the test setup and not to
yield 'publication-ready' results
```
varname ; test                             ; plot
#-------;----------------------------------;-----
x       ; flagMissing()                    ;
x       ; flagRange(min=0, max=100)        ; False
x       ; constants_flagBasic(window="3h") ; True
y       ; flagRange(min=-10, max=40)`      ;
```

### Regular Expressions
Some of the most basic tests (e.g. checks for missing values or range tests) but
also the more elaborated functions available (e.g. aggregation or interpolation
functions) are very likely to be used on all or at least several variables of
the processed dataset. As it becomes quite cumbersome to list all these
variables seperately, only to call the same functions with the same
parameters over and over again, SaQC supports regular expressions
within the `varname` column. Please not that a `varname` needs to be quoted 
(with `'` or `"`) in order to be interpreted as a regular expression.

```
varname    ; test
#----------;------------------------------
'.*'       ; harm_shift2Grid(freq="15Min")
'(x \| y)' ; flagMissing()
```