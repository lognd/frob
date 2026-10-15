<!-- mdtest: rule=TOOL001 -->
# TOOL001 tool stage failed

The block is the shell script of a bound tool stage; a nonzero exit fails it.

## A stage that exits nonzero fires

```sh expect=fire
exit 3
```

## A stage that exits zero is clean

```sh expect=clean
exit 0
```
