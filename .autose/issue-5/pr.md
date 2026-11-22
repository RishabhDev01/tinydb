## AutoSE pull request for #5

Closes #5

**Summary:** Add a `pluck` method to tables to extract a list of values for a specified field across all documents, skipping documents where the field is absent.

| Artifact | |
|---|---|
| Spec (stage 1) | `.autose/issue-5/spec.md` |
| Design (stage 2) | `.autose/issue-5/design.md` |
| Patch (stage 3) | `.autose/issue-5/diff.patch` |
| Test report (stage 4) | `.autose/issue-5/test_report.md` |
| CI (stage 5) | pending: (pending) |
| Run | https://github.com/RishabhDev01/tinydb/actions/runs/45005311148 |

### Stage history
| Round | Stage | Result |
|---|---|---|
| r1 | guard | pass |
| r1 | spec | fail |
| r1 | spec | pass |
| r1 | design | pass |
| r1 | implement+test | fail |
| r1 | implement+test | pass |
| r1 | guard | pass |
| r1 | spec | pass |
| r1 | design | pass |
| r1 | implement+test | fail |
| r1 | implement+test | pass |

An independent reviewer agent (different model, read-only, no access to the spec or design) will post its review below. **This PR is never merged automatically. A maintainer decides.**

The `.autose/` folder holds the audit trail and can be deleted before merging.
