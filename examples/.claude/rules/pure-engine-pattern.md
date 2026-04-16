# Pure Engine Pattern

## The Contract

```ts
class SomeEngine {
  static evaluate(input: EvaluationInput): Result[] {
    // zero DB access — all data is in `input`
    // zero network calls
    // zero time-dependence (referenceDate injected)
  }
}
```

- No database reads inside `evaluate()`.
- No network calls inside `evaluate()`.
- No `new Date()` — pass `referenceDate` in input.
- Returns a plain array of results.
