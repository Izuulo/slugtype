# slugtype

A terminal typing test in the style of Monkeytype.

## Install (dev)

```bash
pip install -e .[dev]
```

## Run

```bash
slugtype                # 60-second english-200 test
slugtype --time 30      # 30-second test
slugtype --words 25     # 25-word test
```

## Stats

- **wpm**: `(correct word chars + correct spaces between fully-correct words) * 60 / test_seconds / 5`
- **acc**: `100 * correct_chars / (correct_chars + incorrect_chars)`

History persistence and the result graph land in v0.3.
