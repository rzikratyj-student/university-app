"""Local heuristic secret scan. Reports locations and categories, never values."""
import json
from pathlib import Path
import re
import sys
from urllib.parse import quote

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDERS = {'change-me', 'your-password', 'replace-with-your-password', 'example', 'placeholder'}
PATTERNS = {
    'private-key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'github-token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b'),
    'aws-access-key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'literal-secret': re.compile(r'''(?i)\b(?:password|passwd|secret_key|api_key|access_token)\s*[:=]\s*["']([^"'\r\n]{8,})["']'''),
}
URL_PASSWORD = re.compile(r'\b[a-z][a-z0-9+.-]*://[^\s/:]+:([^\s/@]+)@', re.I)


def source_paths():
    paths = set()
    for directory in ('app', 'tests', 'migrations', 'scripts'):
        for path in (ROOT / directory).rglob('*'):
            if '__pycache__' in path.parts or any(part.startswith('.') for part in path.relative_to(ROOT).parts):
                continue
            if path.is_file() and path.suffix.lower() in {'.py', '.ps1', '.html', '.css', '.js', '.md', '.txt', '.ini', '.mako', ''}:
                paths.add(path)
    paths.update(p for p in ROOT.iterdir() if p.is_file() and p.suffix in {'.py', '.md', '.txt', '.json'})
    paths.add(ROOT / '.env.example')
    for name in json.loads((ROOT / 'source-manifest.json').read_text(encoding='utf-8-sig')):
        path = ROOT / name
        if path.resolve().is_relative_to(ROOT.resolve()):
            paths.add(path)
        else:
            raise ValueError('Manifest path escapes project')
    return sorted(paths)


def main():
    known = []
    for value in dotenv_values(ROOT / '.env').values():
        if value and '://' in value:
            try:
                password = make_url(value).password
                if password:
                    known.extend([password, quote(password, safe='')])
            except Exception:
                pass
    old_password = ROOT / '.local' / 'db-password'
    if old_password.is_file():
        known.append(old_password.read_text(encoding='utf-8').strip())
    findings = []
    paths = source_paths()
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()):
            findings.append((str(path.relative_to(ROOT)), 0, 'unsafe-path'))
            continue
        contents = path.read_text(encoding='utf-8-sig')
        for number, line in enumerate(contents.splitlines(), 1):
            kinds = set()
            if any(value and len(value) >= 8 and value in line for value in known):
                kinds.add('known-local-credential')
            for kind, pattern in PATTERNS.items():
                for match in pattern.finditer(line):
                    if kind != 'literal-secret' or match.group(1) not in PLACEHOLDERS:
                        kinds.add(kind)
            for match in URL_PASSWORD.finditer(line):
                if match.group(1) not in PLACEHOLDERS and not any(c in match.group(1) for c in '{}<>'):
                    kinds.add('connection-string-password')
            findings.extend((str(path.relative_to(ROOT)), number, kind) for kind in sorted(kinds))
    for path, line, kind in findings:
        print(f'{path}:{line}: {kind} [value hidden]')
    print(f'Scanned {len(paths)} source files; findings: {len(findings)}. Heuristic scan, not a guarantee.')
    return 1 if findings else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print(f'Secret scan failed: {type(error).__name__}; details suppressed.')
        sys.exit(2)
