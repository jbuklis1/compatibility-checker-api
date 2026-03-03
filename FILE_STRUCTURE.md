# Cross-Platform Compatibility Checker — File Structure

Document representing the file structure of the compatibility checker project (API + rule-based checker library). Generated paths are relative to the project root `compatibility-checker-api/`.

```
compatibility-checker-api/
│
├── README.md
├── requirements.txt
├── setup_and_run.sh
├── setup_and_run.bat
├── .env.example
├── .env                    # Local env (gitignored)
├── deps.py                 # Centralized imports (FastAPI, Path, etc.)
├── FILE_STRUCTURE.md       # This document
├── file structure.txt      # Legacy structure outline
│
├── app/                    # FastAPI application
│   ├── __init__.py
│   ├── main.py             # App entry point, route registration
│   ├── config.py           # Env/config, checker import path
│   ├── startup.py          # Startup validation
│   ├── ai_status.py        # AI availability (TOGETHER_API_KEY) for banner
│   ├── schemas.py          # Pydantic request/response models (IssueOut, etc.)
│   ├── utils.py            # run_check() helper
│   ├── report_formatter.py # Text report formatting (single & multi-file)
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── root.py         # GET / (home page)
│   │   └── review.py       # GET/POST /review, upload, multi-file, downloads
│   │
│   ├── services/
│   │   ├── ai.py           # Together.ai: suggest_fixes, generate_tests,
│   │   │                   #   analyze_group_relationships, suggest_group_fixes
│   │   ├── checker.py      # Wrapper around cross_platform_checker
│   │   ├── file_extractor.py   # Extract sources from folder/zip/UploadFile
│   │   └── relationship_detector.py  # build_dependency_graph, imports
│   │
│   └── templates/
│       ├── __init__.py     # render_review_form, render_review_results,
│       │                   #   render_review_multi_results
│       ├── base.html
│       ├── root.html       # Home page
│       ├── review_form.html
│       ├── review_results.html    # Single-file results
│       ├── review_multi_results.html
│       └── styles.css
│
└── cross_platform_checker/ # Rule-based checker library
    ├── __init__.py
    ├── README.md
    ├── issue.py            # Issue, Candidate, Severity
    ├── checker_base.py     # BaseChecker (_add_issue, _add_candidate, check)
    ├── main_checker.py     # CrossPlatformChecker: check_file, check_files,
    │                       #   language dispatch, candidates + context pruner
    ├── context_pruner.py   # Two-phase: promote/drop candidates (exec_call, etc.)
    ├── utils.py            # detect_language, path/context helpers
    ├── reporter.py         # Issue reporting
    │
    └── checkers/
        ├── __init__.py     # All checker classes exported
        │
        │   # General (all languages)
        ├── path_checker.py   # Path handling (os.path, pathlib, hardcoded paths)
        ├── file_checker.py   # File I/O, encoding, locking
        ├── env_checker.py    # Env vars (%VAR%, TEMP, getenv) — candidates
        ├── api_checker.py    # Platform-specific APIs (win32/unix/macos), exec→candidate
        ├── system_checker.py # system(), popen(), exec() — exec→candidate for C/C++
        │
        │   # Language-specific
        ├── python_checker.py
        ├── javascript_checker.py   # JS/TS
        ├── cpp_checker.py          # C/C++
        ├── java_checker.py         # Java/Kotlin
        ├── go_checker.py
        ├── rust_checker.py
        ├── csharp_checker.py
        ├── lua_checker.py
        └── swift_checker.py
```

## Summary

| Area | Purpose |
|------|--------|
| **app/** | FastAPI API: routes (root, review/upload/multi/download), services (AI, checker, file extract, dependency graph), templates (HTML/CSS), config, schemas, report formatting. |
| **cross_platform_checker/** | Static analysis: main_checker (orchestrator, two-phase with candidates), context_pruner (promote/drop by context), issue/candidate models, and checkers (path, file, env, API, system + per-language). |

## Notable paths

- **Entry:** `app/main.py` → mounts routes from `app/routes/`.
- **Review flow:** `app/routes/review.py` → `CheckerService` (`app/services/checker.py`) → `CrossPlatformChecker` (`cross_platform_checker/main_checker.py`).
- **AI:** `app/services/ai.py` — all LLM prompts (fixes, tests, group insights, group fixes); uses dependency graph from `app/services/relationship_detector.py`.
- **Two-phase checks:** `main_checker` runs checkers with a shared `candidates` list, then `ContextPruner` in `context_pruner.py` prunes (e.g. Qt `exec_call` dropped, rest promoted to issues).
