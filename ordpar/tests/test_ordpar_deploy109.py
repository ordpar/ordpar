"""Pins the change-list check of `deploy.py prepare` (site decisions 109, 2026-10-23), on a scratch
clone, a local bare repository standing in for GitHub and a scratch source repository (`--repo`) —
never the real clone, never the network:

* `ordpar/changes.md`, every deploy: prepare refuses, naming the file and the step, unless its last
  COMMIT is newer than the last published snapshot (the deploy log's newest push); an edit that is
  not committed does not count; with a newer commit it passes;
* `ordpar/library-changes.md`: prepare refuses when it is not in the repository (create it with a
  baseline entry); when the library's fingerprint (`out/build.json` `site_stats` + `change_notice`
  counts) differs from the last published snapshot's and the file has no newer commit; and when the
  last snapshot has no fingerprint recorded (every push before 109); it passes when the fingerprint
  is unchanged without a library entry, and when a newer library entry is committed;
* each push records the build's fingerprint in the deploy log, and a rollback carries the restored
  snapshot's; a rollback needs no list entry;
* `--skip-changes` needs a reason; with one, the snapshot is made and the override (the build, the
  reason, the checks skipped) appended to the override log;
* the checks run before the test gate: a missing entry refuses before any test file runs.

Shown to fail on the `deploy.py` before 109 (a copy outside the worktree): see the build's report.
Stdlib unittest; needs git."""

import io
import json
import os
import subprocess
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_ordpar_deploy103 as t103  # noqa: E402  (the scratch clone, repository and site)

deploy = t103.deploy


class Base(t103.Scratch):
    def setUp(self):
        super().setUp()
        self.deploy_log = os.path.join(self.clone, ".git", "ordpar-deploys.jsonl")

    def published(self):
        """One snapshot prepared and pushed, the lists committed an hour before."""
        r = self.run_deploy("prepare")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.run_deploy("push", "--no-verify").returncode, 0)

    def overrides(self):
        if not os.path.exists(self.log):
            return []
        with io.open(self.log, encoding="utf-8") as fh:
            return [json.loads(l) for l in fh if l.strip()]

    def pushes(self):
        with io.open(self.deploy_log, encoding="utf-8") as fh:
            return [e for e in (json.loads(l) for l in fh if l.strip()) if e.get("pushed")]

    def change_library(self, translated=1):
        """The library grows: a new build with `translated` more articles translated."""
        bj = os.path.join(self.out, "build.json")
        with io.open(bj, encoding="utf-8") as fh:
            b = json.load(fh)
        b["site_stats"] = json.loads(json.dumps(b["site_stats"]))
        b["site_stats"]["articles"]["translated"] += translated
        with io.open(bj, "w", encoding="utf-8") as fh:
            json.dump(b, fh)

    def assertRefused(self, r, *names):
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn("refused:", r.stderr)
        for n in names:
            self.assertIn(n, r.stderr)
        self.assertIn("commit it, and run prepare again", r.stderr)
        self.assertIn("--skip-changes", r.stderr)


class TestChanges(Base):
    def test_refuses_without_a_newer_changes_commit_and_names_it(self):
        self.published()
        head = self.git("rev-parse", "HEAD")
        r = self.run_deploy("prepare")
        self.assertRefused(r, "ordpar/changes.md has no commit since the last published snapshot")
        self.assertNotIn("library-changes.md", r.stderr)      # the library did not change
        self.assertEqual(self.git("rev-parse", "HEAD"), head)  # no new snapshot
        self.assertEqual(self.overrides(), [])

    def test_an_uncommitted_edit_does_not_count(self):
        self.published()
        with io.open(os.path.join(self.repo, "ordpar", "changes.md"), "a", encoding="utf-8") as fh:
            fh.write("\n## written, not committed\n")
        r = self.run_deploy("prepare")
        self.assertRefused(r, "ordpar/changes.md", "uncommitted edits")

    def test_passes_with_one(self):
        self.published()
        self.entry("changes.md")
        r = self.run_deploy("prepare")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("change lists:", r.stdout)
        self.assertIn("library unchanged", r.stdout)
        self.assertIn("snapshot:", r.stdout)

    def test_checks_run_before_the_gate(self):
        self.published()
        write = t103.write
        write(os.path.join(self.tests, "test_planted_fail.py"), t103.FAIL)
        r = self.run_deploy("prepare")
        self.assertRefused(r, "ordpar/changes.md")
        self.assertNotIn("gate:", r.stdout)
        self.assertNotIn("test_planted_fail.py", r.stderr)

    def test_a_rollback_needs_no_entry(self):
        self.published()
        t103._rm(self.out)
        t103.make_out(self.out, "2222222222222222", page="second")
        self.entry("changes.md")
        self.assertEqual(self.run_deploy("prepare").returncode, 0)
        self.assertEqual(self.run_deploy("push", "--no-verify").returncode, 0)
        r = self.run_deploy("rollback")                        # no new entry committed
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.run_deploy("push", "--no-verify").returncode, 0)
        log = self.pushes()
        self.assertEqual([e["kind"] for e in log], ["snapshot", "snapshot", "rollback"])
        self.assertEqual(log[2]["library"], log[0]["library"])  # the restored snapshot's fingerprint


class TestLibrary(Base):
    def test_push_records_the_fingerprint(self):
        self.published()
        fp, totals = deploy.library_fingerprint(os.path.join(self.out, "build.json"))
        self.assertRegex(fp, r"^[0-9a-f]{16}$")
        e = self.pushes()[-1]
        self.assertEqual(e["library"], fp)
        self.assertEqual(e["library_totals"], totals)

    def test_fingerprint_reads_site_stats_and_change_notice_counts(self):
        b = {"site_stats": t103.about.SAMPLE,
             "change_notice": {"articles": 2, "groups": {"typo": {"articles": 2, "corrections": 3}},
                               "notice": {"1": [["typo", 1]], "2": [["typo", 2]]}, "upstream": [{}]}}
        c = deploy.library_counts(b)
        self.assertEqual(c["change_notice"], {"articles": 2, "groups": b["change_notice"]["groups"],
                                              "notice": 2, "upstream": 1})
        self.assertEqual(c["site_stats"], t103.about.SAMPLE)

    def test_refuses_when_the_library_changed_without_an_entry(self):
        self.published()
        self.entry("changes.md")
        self.change_library()
        r = self.run_deploy("prepare")
        self.assertRefused(r, "the library changed since the last published snapshot",
                           "ordpar/library-changes.md has no commit since", "article totals")
        self.assertNotIn("ordpar/changes.md has no commit", r.stderr)
        self.entry("library-changes.md")
        r = self.run_deploy("prepare")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ordpar/library-changes.md committed", r.stdout)

    def test_refuses_when_the_file_is_missing(self):
        subprocess.run(["git", "-C", self.repo, "rm", "-q", "ordpar/library-changes.md"], check=True)
        self.commit_repo("no library list", time.time() - 1800)
        r = self.run_deploy("prepare")                         # even the first deploy
        self.assertRefused(r, "ordpar/library-changes.md is not in the repository",
                           "Create it with a baseline entry")
        t103.write(os.path.join(self.repo, "ordpar", "library-changes.md"), "# baseline\n")
        r = self.run_deploy("prepare")
        self.assertRefused(r, "exists but is not committed")
        self.commit_repo("baseline")
        r = self.run_deploy("prepare")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_passes_when_unchanged_without_a_library_entry(self):
        self.published()
        self.entry("changes.md")
        r = self.run_deploy("prepare")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("so no ordpar/library-changes.md entry needed", r.stdout)

    def test_a_snapshot_without_a_fingerprint_counts_as_changed(self):
        self.published()
        with io.open(self.deploy_log, encoding="utf-8") as fh:   # a push from before 109
            lines = [json.loads(l) for l in fh if l.strip()]
        for e in lines:
            e.pop("library", None)
            e.pop("library_totals", None)
        with io.open(self.deploy_log, "w", encoding="utf-8", newline="\n") as fh:
            fh.writelines(json.dumps(e) + "\n" for e in lines)
        self.entry("changes.md")
        r = self.run_deploy("prepare")
        self.assertRefused(r, "no fingerprint recorded", "ordpar/library-changes.md")
        self.entry("library-changes.md")
        self.assertEqual(self.run_deploy("prepare").returncode, 0)


class TestSkipChanges(Base):
    def test_needs_a_reason(self):
        for reason in ("", "   "):
            r = self.run_deploy("prepare", "--skip-changes", reason)
            self.assertEqual(r.returncode, 2)
            self.assertIn("--skip-changes needs a reason", r.stderr)
        r = self.run_deploy("rollback", "--skip-changes", "x")
        self.assertEqual(r.returncode, 2)
        self.assertIn("--skip-changes is for prepare", r.stderr)

    def test_is_logged(self):
        self.published()
        self.change_library()
        r = self.run_deploy("prepare", "--skip-changes", "re-deploy of the same build")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("OVERRIDE logged", r.stdout)
        self.assertIn("snapshot:", r.stdout)
        [e] = self.overrides()
        self.assertEqual(e["override"], "--skip-changes")
        self.assertEqual(e["reason"], "re-deploy of the same build")
        self.assertEqual(e["skipped"], ["changes", "library-changes"])
        self.assertEqual(e["build"]["offline_build"], "1111111111111111")
        self.assertIn("at", e)
        self.assertEqual(self.run_deploy("push", "--no-verify").returncode, 0)
        self.assertEqual(self.pushes()[-1]["skip_changes"], "re-deploy of the same build")

    def test_nothing_to_skip_is_not_logged(self):
        r = self.run_deploy("prepare", "--skip-changes", "habit")       # the first deploy: both pass
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("nothing to skip", r.stdout)
        self.assertEqual(self.overrides(), [])


if __name__ == "__main__":
    unittest.main()
