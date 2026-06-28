from __future__ import annotations

import enum
from pathlib import Path

from pydantic import BaseModel
from typani import Err, ErrorSet, Ok
from typani.result import Result


class CtxError(ErrorSet):
    SymbolNotFound = "Symbol not found in file"
    UnsupportedFile = "Only Python and C/C++ files are supported"
    ParseFailed = "Could not parse the file"


class CtxTier(str, enum.Enum):
    stub = "stub"  # signature only -- function is simple
    bundle = "bundle"  # function + import signatures -- standard
    full = "full"  # bundle + xref callers + relevant docs -- complex


class CtxResult(BaseModel):
    model_config = {}

    path: str
    symbol: str
    tier: CtxTier
    tier_reason: str
    content: str

    def as_text(self) -> str:
        header = (
            f"# frob ctx: {self.symbol}  [tier={self.tier.value}]\n"
            f"# reason: {self.tier_reason}\n\n"
        )
        return header + self.content


def adaptive_context(
    path: Path,
    target: str,
    *,
    root: Path | None = None,
    bundle_depth: int = 1,
    xref_caller_threshold: int = 5,
) -> Result[CtxResult, CtxError]:
    """
    Adaptively choose how much context to gather for `target` in `path`.

    Tier selection rules (evaluated in order):
      stub   -- function body < 12 lines AND no complex imports
      bundle -- default for most functions
      full   -- function body >= 40 lines, OR caller count >= xref_caller_threshold,
                OR bundle section count > 4 (many dependencies)
    """
    ext = path.suffix.lower()
    if ext not in {".py", ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hxx"}:
        return Err(CtxError.UnsupportedFile)

    # Step 1: outline to find function line count
    fn_lines = _estimate_fn_lines(path, target)

    # Step 2: decide initial tier from line count alone (fast path)
    if fn_lines is not None and fn_lines < 12:
        tier = CtxTier.stub
        reason = f"function body is {fn_lines} lines (< 12)"
    elif fn_lines is not None and fn_lines >= 40:
        tier = CtxTier.full
        reason = f"function body is {fn_lines} lines (>= 40)"
    else:
        tier = CtxTier.bundle
        reason = (
            f"function body is {fn_lines} lines" if fn_lines else "line count unknown"
        )

    # Step 3: for stub/bundle tiers, check bundle dep count to possibly upgrade
    if tier in (CtxTier.stub, CtxTier.bundle):
        from frob.bundle import build_bundle

        bundle_result = build_bundle(path, target, depth=bundle_depth)
        if bundle_result.is_err:
            err = bundle_result.danger_err
            from frob.bundle import BundleError

            if err == BundleError.TargetNotFound:
                return Err(CtxError.SymbolNotFound)
            return Err(CtxError.ParseFailed)

        bundle = bundle_result.danger_ok
        dep_sections = [s for s in bundle.sections if s.role == "import"]

        if tier == CtxTier.stub and len(dep_sections) > 2:
            tier = CtxTier.bundle
            reason = (
                f"function is small but has {len(dep_sections)} import dependencies"
            )

        if tier == CtxTier.bundle and len(dep_sections) > 4:
            tier = CtxTier.full
            reason = f"function has {len(dep_sections)} import dependencies (> 4)"

        if tier in (CtxTier.stub, CtxTier.bundle):
            content = (
                bundle.as_text()
                if tier == CtxTier.bundle
                else _stub_content(path, target)
            )
            return Ok(
                CtxResult(
                    path=str(path),
                    symbol=target,
                    tier=tier,
                    tier_reason=reason,
                    content=content,
                )
            )

        # tier upgraded to full -- fall through with bundle content
        bundle_text = bundle.as_text()
    else:
        # Already full tier from line count
        from frob.bundle import build_bundle

        bundle_result = build_bundle(path, target, depth=bundle_depth)
        if bundle_result.is_err:
            from frob.bundle import BundleError

            err = bundle_result.danger_err
            if err == BundleError.TargetNotFound:
                return Err(CtxError.SymbolNotFound)
            return Err(CtxError.ParseFailed)
        bundle_text = bundle_result.danger_ok.as_text()

    # Step 4: full tier -- add xref callers and docs
    scan_root = root or path.parent
    extra_parts: list[str] = [bundle_text]

    xref_text = _get_xref(target, scan_root)
    if xref_text:
        extra_parts.append(f"\n## Callers (xref)\n\n{xref_text}")

    # Only check docs if not bundled from --depth already
    if tier == CtxTier.full:
        docs_text = _get_docs(path, target)
        if docs_text:
            extra_parts.append(f"\n## Docstring\n\n{docs_text}")

    return Ok(
        CtxResult(
            path=str(path),
            symbol=target,
            tier=tier,
            tier_reason=reason,
            content="\n".join(extra_parts),
        )
    )


def _estimate_fn_lines(path: Path, target: str) -> int | None:
    """Estimate function line count via the edit isolate fast path."""
    try:
        from frob.edit import isolate

        result = isolate(path, target)
        if result.is_ok:
            iso = result.danger_ok
            return iso.end_line - iso.start_line + 1
    except Exception:
        pass
    return None


def _stub_content(path: Path, target: str) -> str:
    from frob.stub import stub_file

    result = stub_file(path, target)
    if result.is_ok:
        return result.danger_ok
    return ""


def _get_xref(symbol: str, root: Path) -> str:
    try:
        from frob.xref import xref

        result = xref(symbol, root)
        if result.is_ok:
            xr = result.danger_ok
            if xr.usages:
                return xr.as_text()
    except Exception:
        pass
    return ""


def _get_docs(path: Path, target: str) -> str:
    try:
        from frob.docs import (
            extract_docs,  # type: ignore[import,attr-defined]  # ty: ignore[unresolved-import]
        )

        result = extract_docs(path, symbol=target)
        if result.is_ok:
            return result.danger_ok
    except Exception:
        pass
    return ""
