#!/usr/bin/env python3
"""Lightweight accessibility regression checks for static HTML pages."""

from __future__ import annotations

import sys
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
HTML_FILES = [ROOT / 'index.html'] + sorted((ROOT / 'pages').glob('**/*.html'))


def element_text(el) -> str:
    return ' '.join(el.stripped_strings)


def has_accessible_name(el: BeautifulSoup) -> bool:
    if el.get('aria-label') or el.get('aria-labelledby') or el.get('title'):
        return True
    if el.name == 'input':
        t = (el.get('type') or 'text').lower()
        if t in {'hidden', 'submit', 'button', 'reset'}:
            return bool(el.get('value') or el.get('aria-label') or el.get('title'))
        if el.get('id'):
            soup = el.find_parent('html')
            if soup and soup.select_one(f'label[for="{el.get("id")}"]'):
                return True
        if el.find_parent('label'):
            return True
        return False
    return bool(element_text(el))


def check_file(path: Path) -> list[str]:
    soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
    errors: list[str] = []

    # Landmarks
    if len(soup.find_all('main')) != 1:
        errors.append('must have exactly one <main> landmark')
    if not soup.find('nav'):
        errors.append('must include a <nav> landmark')
    if not soup.find('footer'):
        errors.append('must include a <footer> landmark')

    skip = soup.select_one('a.skip-link')
    if not skip:
        errors.append('must include a .skip-link link for keyboard users')
    elif not skip.get('href', '').startswith('#'):
        errors.append('skip link must target an in-page anchor')

    # Heading order
    last_level = 0
    h1_count = 0
    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        level = int(heading.name[1])
        if level == 1:
            h1_count += 1
        if last_level and level > last_level + 1:
            errors.append(
                f'heading level jumps from h{last_level} to h{level} near "{element_text(heading)[:60]}"'
            )
        last_level = level
    if h1_count != 1:
        errors.append(f'must include exactly one h1 (found {h1_count})')

    # Interactive controls need accessible names
    for control in soup.select('button, input, select, textarea'):
        if control.get('disabled') is not None:
            continue
        if not has_accessible_name(control):
            css_class = ' '.join(control.get('class', []))
            errors.append(f'interactive <{control.name}> lacks accessible name (class="{css_class}")')

    for link in soup.select('a[href]'):
        if not has_accessible_name(link):
            errors.append(f'link "{link.get("href")}" lacks accessible text/name')

    # Menu and theme specific checks
    menu = soup.select_one('.menu-toggle')
    if menu:
        if not menu.get('aria-controls'):
            errors.append('.menu-toggle missing aria-controls')
        if menu.get('aria-expanded') not in {'true', 'false'}:
            errors.append('.menu-toggle must expose aria-expanded')

    theme = soup.select_one('.theme-toggle')
    if theme:
        if not theme.get('aria-label'):
            errors.append('.theme-toggle missing aria-label')
        if theme.get('aria-pressed') not in {'true', 'false'}:
            errors.append('.theme-toggle must expose aria-pressed state')

    # Potential keyboard trap anti-pattern
    for el in soup.select('[tabindex]'):
        try:
            if int(el['tabindex']) > 0:
                errors.append('positive tabindex found; may create keyboard trap/order issues')
                break
        except ValueError:
            errors.append('invalid tabindex value')
            break

    return errors


def main() -> int:
    all_errors: list[tuple[Path, str]] = []
    for html_file in HTML_FILES:
        for err in check_file(html_file):
            all_errors.append((html_file.relative_to(ROOT), err))

    if all_errors:
        print('Accessibility regression checks failed:')
        for file_path, msg in all_errors:
            print(f' - {file_path}: {msg}')
        return 1

    print(f'Accessibility regression checks passed for {len(HTML_FILES)} HTML files.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
