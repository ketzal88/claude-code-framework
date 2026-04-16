# Cron Security

Every route under `/api/cron/**` is security-sensitive.

```ts
export const POST = withErrorReporting('cron-name', async (req) => {
  const auth = await validateCronSecret(req);
  if (!auth.valid) return auth.response;
  // handler
});
```

- Never accept unauthenticated POSTs.
- Always wrap with `withErrorReporting()`.
- Always export `maxDuration` explicitly.
