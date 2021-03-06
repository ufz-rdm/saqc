# Generic Functions

## Generic Flagging Functions

Generic flagging functions provide a way to leverage cross-variable quality
constraints and to implement simple quality checks directly within the configuration.

### Why?
The underlying idea is, that in most real world datasets many errors
can be explained by the dataset itself. Think of a an active, fan-cooled
measurement device: no matter how precise the instrument may work, problems
are to be expected when the fan stops working or the power supply 
drops below a certain threshold. While these dependencies are easy to 
[formalize](#a-real-world-example) on a per dataset basis, it is quite
challenging to translate them into generic source code.

### Specification
Generic flagging functions are used in the same manner as their
[non-generic counterparts](docs/FunctionIndex.md). The basic 
signature looks like that:
```sh
flagGeneric(func=<expression>, flag=<flagging_constant>)
```
where `<expression>` is composed of the [supported constructs](#supported-constructs)
and `<flag_constant>` is one of the predefined
[flagging constants](ParameterDescriptions.md#flagging-constants) (default: `BAD`)
Generic flagging functions are expected to evaluate to a boolean value, i.e. only 
constructs returning `True` or `False` are accepted. All other expressions will
fail during the runtime of `SaQC`.


### Examples

#### Simple comparisons

##### Task
Flag all values of variable `x` when variable `y` falls below a certain threshold

##### Configuration file
```
varname ; test                    
#-------;------------------------
x       ; flagGeneric(func=y < 0) 
```

#### Calculations

##### Task
Flag all values of variable `x` that exceed 3 standard deviations of variable `y`

##### Configuration file
```
varname ; test
#-------;---------------------------------
x       ; flagGeneric(func=x > std(y) * 3)
```
#### Special functions

##### Task
Flag variable `x` where variable `y` is flagged and variable `x` has missing values

##### Configuration file
```
varname ; test
#-------;----------------------------------------------
x       ; flagGeneric(func=isflagged(y) & ismissing(z))
```

#### A real world example
Let's consider a dataset like the following:

| date             | meas | fan | volt |
|------------------|------|-----|------|
| 2018-06-01 12:00 | 3.56 |   1 | 12.1 |
| 2018-06-01 12:10 |  4.7 |   0 | 12.0 |
| 2018-06-01 12:20 |  0.1 |   1 | 11.5 |
| 2018-06-01 12:30 | 3.62 |   1 | 12.1 |
| ...              |      |     |      |

##### Task
Flag variable `meas` where variable `fan` equals 0 and variable `volt`
is lower than `12.0`.

##### Configuration file
We can directly implement the condition as follows:
```
varname ; test
#-------;-----------------------------------------------
meas    ; flagGeneric(func=(fan == 0) \|  (volt < 12.0))
```
But we could also quality check our independent variables first
and than leverage this information later on:
```
varname ; test
#-------;----------------------------------------------------
'.*'    ; flagMissing()
fan     ; flagGeneric(func=fan == 0)
volt    ; flagGeneric(func=volt < 12.0)
meas    ; flagGeneric(func=isflagged(fan) \| isflagged(volt))
```

## Generic Processing

Generic processing functions provide a way to evaluate mathmetical operations 
and functions on the variables of a given dataset.

### Why
In many real-world use cases, quality control is embedded into a larger data 
processing pipeline and it is not unusual to even have certain processing 
requirements as a part of the quality control itself. Generic processing 
functions make it easy to enrich a dataset through the evaluation of a
given expression.

### Specification
The basic signature looks like that:
```sh
procGeneric(func=<expression>)
```
where `<expression>` is composed of the [supported constructs](#supported-constructs).


## Variable References
All variables of the processed dataset are available within generic functions,
so arbitrary cross references are possible. The variable of interest 
is furthermore available with the special reference `this`, so the second 
[example](#calculations) could be rewritten as: 
```
varname ; test
#-------;------------------------------------
x       ; flagGeneric(func=this > std(y) * 3)
```

When referencing other variables, their flags will be respected during evaluation
of the generic expression. So, in the example above only values of `x` and `y`, that
are not already flagged with `BAD` will be used the avaluation of `x > std(y)*3`. 


## Supported constructs

### Operators

#### Comparison

The following comparison operators are available:

| Operator | Description                                                                                        |
|----------|----------------------------------------------------------------------------------------------------|
| `==`     | `True` if the values of the operands are equal                                                     |
| `!=`     | `True` if the values of the operands are not equal                                                 |
| `>`      | `True` if the values of the left operand are greater than the values of the right operand          |
| `<`      | `True` if the values of the left operand are smaller than the values of the right operand          |
| `>=`     | `True` if the values of the left operand are greater or equal than the values of the right operand |
| `<=`     | `True` if the values of the left operand are smaller or equal than the values of the right operand |

#### Arithmetics
The following arithmetic operators are supported:

| Operator | Description    |
|----------|----------------|
| `+`      | addition       |
| `-`      | subtraction    |
| `*`      | multiplication |
| `/`      | division       |
| `**`     | exponentiation |
| `%`      | modulus        |

#### Bitwise
The bitwise operators also act as logical operators in comparison chains

| Operator | Description       |
|----------|-------------------|
| `&`      | binary and        |
| `\|`     | binary or         |
| `^`      | binary xor        |
| `~`      | binary complement |

### Functions
All functions expect a [variable reference](#variable-references)
as the only non-keyword argument (see [here](#special-functions))

#### Mathematical Functions

| Name        | Description                       |
|-------------|-----------------------------------|
| `abs`       | absolute values of a variable     |
| `max`       | maximum value of a variable       |
| `min`       | minimum value of a variable       |
| `mean`      | mean value of a variable          |
| `sum`       | sum of a variable                 |
| `std`       | standard deviation of a variable  |
| `len`       | the number of values for variable |

#### Special Functions

| Name        | Description                       |
|-------------|-----------------------------------|
| `ismissing` | check for missing values          |
| `isflagged` | check for flags                   |

### Constants
Generic functions support the same constants as normal functions, a detailed 
list is available [here](ParameterDescriptions.md#constants).
