# coding: utf-8
import hashlib
import os
import shutil
from fnmatch import fnmatch
from pathlib import Path


class RejectedPath(Exception):
    pass


def file_digests(path):
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    size = 0
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            md5.update(chunk)
            sha256.update(chunk)
    return size, md5.hexdigest(), sha256.hexdigest()


def _matches_any(value, patterns):
    return any(fnmatch(value, pattern) for pattern in patterns)


def is_excluded(name, relative_path, exclude_globs):
    return _matches_any(name, exclude_globs) or _matches_any(
        relative_path, exclude_globs
    )


def is_included(name, relative_path, include_globs):
    return _matches_any(name, include_globs) or _matches_any(
        relative_path, include_globs
    )


def is_eligible(relative_path, mtime, now, config, ignore_stability=False):
    name = Path(relative_path).name
    if is_excluded(name, relative_path, config.exclude_globs):
        return False
    if not is_included(name, relative_path, config.include_globs):
        return False
    if not ignore_stability and (now - mtime) < config.stable_seconds:
        return False
    return True


def relative_posix(source_dir, path):
    source = Path(source_dir).resolve()
    target = Path(path).resolve()
    try:
        relative = target.relative_to(source)
    except ValueError:
        raise RejectedPath("caminho fora do diretório de origem")
    if any(part in ("..", "") for part in relative.parts):
        raise RejectedPath("caminho fora do diretório de origem")
    return relative.as_posix()


def resolve_send_path(config, raw_path):
    source = Path(config.source_dir).resolve()
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = source / candidate
    if not candidate.exists():
        raise RejectedPath("arquivo inexistente")
    relative = relative_posix(source, candidate)
    name = Path(relative).name
    if is_excluded(name, relative, config.exclude_globs):
        raise RejectedPath("arquivo aberto ou temporário")
    if not is_included(name, relative, config.include_globs):
        raise RejectedPath("arquivo fora das regras de inclusão")
    if not candidate.resolve().is_file():
        raise RejectedPath("arquivo inexistente")
    return candidate.resolve(), relative


def iter_source_files(source_dir):
    source = Path(source_dir).resolve()
    if not source.is_dir():
        return
    for dirpath, dirnames, filenames in os.walk(source):
        dirnames.sort()
        for name in sorted(filenames):
            full = Path(dirpath) / name
            if not full.is_file():
                continue
            try:
                relative = full.resolve().relative_to(source).as_posix()
            except ValueError:
                continue
            yield full, relative


def stage_pending(source, pending_root, relative):
    """Copia ou cria hardlink na área de pendências. Não altera o arquivo de origem."""
    dest = Path(pending_root) / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    source = Path(source)
    if dest.exists():
        source_size, _, source_sha = file_digests(source)
        dest_size, _, dest_sha = file_digests(dest)
        if source_size == dest_size and source_sha == dest_sha:
            return dest
        dest.unlink()
    try:
        os.link(source, dest)
    except OSError:
        shutil.copy2(source, dest)
    return dest


def discard_pending(pending_root, relative):
    dest = Path(pending_root) / relative
    if dest.is_file():
        dest.unlink()
