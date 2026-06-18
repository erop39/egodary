# Tag Studio Rollback Checklist

This checklist is used if Tag Studio category/subcategory migration causes regressions.

## Preconditions

- Stop write-heavy flows in UI (Add tag / Import + Merge).
- Create a backup copy of `egodary.db`.
- Record current application version and commit hash.

## Rollback Steps

1. Run rollback endpoint:
   - `POST /api/tag-studio/rollback/runtime-subcategory`
   - payload: `{"status":"active"}`
2. Verify that runtime items no longer require `subcategory_id` and still have legacy `subgroup`.
3. Switch clients to legacy-read path (keep reading `meta.subgroup` first).
4. Re-run smoke checks:
   - add runtime tag with subgroup;
   - import prompt with unknown token;
   - open category detail and verify chips visibility.

## Success Criteria

- Existing sessions and runtime overlay behave as before migration.
- No 409/400 spikes for category add-item from legacy clients.
- Prompt import and generate flows remain operational.

## Abort / Escalation

If rollback endpoint reports malformed `item_json` rows that cannot be converted:

- keep DB backup as source of truth;
- export `runtime_tag_items` for manual repair;
- block release until repaired rows are revalidated with migration tests.
