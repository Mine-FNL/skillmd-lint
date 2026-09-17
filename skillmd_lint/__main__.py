"""Entry point for ``python -m skillmd_lint``.

This module is exercised by ``python -m skillmd_lint`` invocations (and
the subprocess tests in tests/test_cli.py), not by in-process test
imports — calling ``main()`` here would raise SystemExit, which is the
intended runtime behavior. The actual CLI logic lives in
``skillmd_lint.cli.main`` and is fully covered by ``tests/test_cli.py``.
"""

from .cli import main  # pragma: no cover

raise SystemExit(main())  # pragma: no cover
