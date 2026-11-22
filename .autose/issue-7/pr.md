## AutoSE pull request for #7

Closes #7

**Summary:** Returning copies of cached query results prevents in-place mutation of returned documents from altering subsequent search results.

| Artifact | |
|---|---|
| Spec (stage 1) | `.autose/issue-7/spec.md` |
| Design (stage 2) | `.autose/issue-7/design.md` |
| Patch (stage 3) | `.autose/issue-7/diff.patch` |
| Test report (stage 4) | `.autose/issue-7/test_report.md` |
| CI (stage 5) | pending: (pending) |
| Run | https://github.com/RishabhDev01/tinydb/actions/runs/44994263819 |

### Stage history
| Round | Stage | Result |
|---|---|---|
| r1 | guard | pass |
| r1 | spec | pass |
| r1 | design | pass |
| r1 | implement+test | fail |
| r1 | implement+test | fail |
| r1 | implement+test | fail |
| r1 | implement+test | back-to-design |
| r1 | design | pass |
| r1 | implement+test | fail |
| r1 | implement+test | fail |
| r1 | implement+test | pass |

An independent reviewer agent (different model, read-only, no access to the spec or design) will post its review below. **This PR is never merged automatically. A maintainer decides.**

The `.autose/` folder holds the audit trail and can be deleted before merging.
