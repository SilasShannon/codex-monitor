# Project learning guides

Project learning guides extend the existing Projects page without replacing its
monitoring analytics. Selecting **Learn how this project works** performs a
bounded, read-only structural inspection and explains:

- detected technologies and the filename evidence for each;
- major areas such as frontend, backend/API, tests, documentation, and storage;
- likely important files and their conventional responsibilities;
- core software-engineering concepts relevant to the visible stack;
- connections that the directory structure supports;
- a suggested sequence for learning the project.

## Inspection boundary

The initial guide intentionally inspects names and directory structure rather
than source contents. It scans at most four directory levels and 600 filenames,
prunes dependency, VCS, cache, and build directories before traversal, and skips
symbolic links. The project must already be associated with a normalized project
key in Codex Monitor's database; callers cannot supply an arbitrary filesystem
path through the API.

This boundary makes the guide fast and privacy-conscious, but limits certainty.
A filename such as `server.py` suggests a conventional responsibility; it does
not prove the file behaves that way. Exact control flow, domain behavior, and
runtime guarantees require source-level evidence. Unknown connections are
labeled instead of invented.

## Optional source outline

Set `project_guides.source_analysis = true` in Codex Monitor's own configuration
to add a bounded declaration outline. This opt-in reads at most 12 recognized
source files, 32 KiB per file and 256 KiB total. It reports top-level class,
function, and similar declaration names; it does not return source excerpts.
Files are decoded as UTF-8, symbolic links and oversized files are skipped, and
project code is never imported or executed.

All inspection and explanation remain local. Project files are read-only inputs,
no project code is executed, and no information is sent to an external AI or
analytics service.
