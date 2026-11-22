## AutoSE pull request for #4

Closes #4

**Summary:** Allow string document IDs convertible to int in `remove(doc_ids=...)` and `update(..., doc_ids=...)`, and ensure returned document IDs are integers matching `document_id_class`.

| Artifact | |
|---|---|
| Spec (stage 1) | `.autose/issue-4/spec.md` |
| Design (stage 2) | `.autose/issue-4/design.md` |
| Patch (stage 3) | `.autose/issue-4/diff.patch` |
| Test report (stage 4) | `.autose/issue-4/test_report.md` |
| CI (stage 5) | pending: (pending) |
| Run | https://github.com/RishabhDev01/tinydb/actions/runs/44992783565 |

### Stage history
| Round | Stage | Result |
|---|---|---|
| r1 | guard | pass |
| r1 | spec | pass |
| r1 | design | STOPPED |
| r1 | design | pass |
| r1 | implement+test | fail |
| r1 | implement+test | fail |
| r1 | implement+test | fail |
| r1 | implement+test | back-to-design |
| r1 | design | pass |
| r1 | implement+test | fail |
| r1 | implement+test | fail |
| r1 | implement+test | fail |
| r1 | test | STOPPED |
| r1 | design | pass |
| r1 | implement+test | fail |
| r1 | implement+test | fail |
| r1 | implement+test | fail |
| r1 | implement+test | back-to-design |
| r1 | design | pass |
| r1 | implement+test | fail |
| r1 | implement+test | fail |
| r1 | implement+test | fail |
| r1 | test | STOPPED |
| r1 | design | pass |
| r1 | implement+test | pass |

An independent reviewer agent (different model, read-only, no access to the spec or design) will post its review below. **This PR is never merged automatically. A maintainer decides.**

The `.autose/` folder holds the audit trail and can be deleted before merging.
