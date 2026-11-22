## AutoSE pull request for #6

Closes #6

**Summary:** Provide an `append(field, val)` operation function in `tinydb.operations` to append a value to a list field or initialise a single-item list if the field does not exist.

| Artifact | |
|---|---|
| Spec (stage 1) | `.autose/issue-6/spec.md` |
| Design (stage 2) | `.autose/issue-6/design.md` |
| Patch (stage 3) | `.autose/issue-6/diff.patch` |
| Test report (stage 4) | `.autose/issue-6/test_report.md` |
| CI (stage 5) | pending: (pending) |
| Run | https://github.com/RishabhDev01/tinydb/actions/runs/45005712745 |

### Stage history
| Round | Stage | Result |
|---|---|---|
| r1 | guard | pass |
| r1 | spec | pass |
| r1 | design | pass |
| r1 | implement | STOPPED |
| r1 | design | pass |
| r1 | implement+test | pass |
| r1 | guard | pass |
| r1 | spec | pass |
| r1 | design | pass |
| r1 | implement+test | pass |

An independent reviewer agent (different model, read-only, no access to the spec or design) will post its review below. **This PR is never merged automatically. A maintainer decides.**

The `.autose/` folder holds the audit trail and can be deleted before merging.
