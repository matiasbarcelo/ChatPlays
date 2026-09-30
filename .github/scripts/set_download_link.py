"""Point the homepage's "Download for Windows" button at the newest pre-release.

Run by .github/workflows/pages.yml on the assembled site, so the link is baked into
the page and visitors' browsers never have to call the (rate-limited) GitHub API.

Usage: GITHUB_TOKEN=... GITHUB_REPOSITORY=owner/repo python set_download_link.py site/index.html
"""
import json
import os
import re
import sys
import urllib.request

BUTTON = re.compile(r'(<a class="download-btn" href=")[^"]*(" id="download-windows">)')
VERSION = re.compile(r'(<span id="download-version">)[^<]*(</span>)')
INSTALLER = re.compile(r'\.(exe|msi)$', re.I)
PREFERRED = re.compile(r'x64|win|setup', re.I)


def newest_prerelease(repo, token):
    request = urllib.request.Request(
        f'https://api.github.com/repos/{repo}/releases?per_page=30',
        headers={
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {token}',
            'X-GitHub-Api-Version': '2022-11-28',
        },
    )
    with urllib.request.urlopen(request) as response:
        releases = json.load(response)
    # Newest first. The token can see drafts, which visitors can't download, so skip them.
    return next((r for r in releases if r['prerelease'] and not r['draft']), None)


def installer_url(release):
    installers = [a for a in release['assets'] if INSTALLER.search(a['name'])]
    best = next((a for a in installers if PREFERRED.search(a['name'])), None) or next(iter(installers), None)
    return best['browser_download_url'] if best else release['html_url']


def main(page_path):
    release = newest_prerelease(os.environ['GITHUB_REPOSITORY'], os.environ['GITHUB_TOKEN'])
    if not release:
        print('No published pre-release found; leaving the releases-page link in place.')
        return

    url = installer_url(release)
    version = re.sub(r'^v', '', release['tag_name'] or release['name'] or '', flags=re.I)

    with open(page_path, encoding='utf-8') as f:
        page = f.read()
    page, buttons = BUTTON.subn(lambda m: m.group(1) + url + m.group(2), page)
    page, versions = VERSION.subn(lambda m: m.group(1) + 'Version ' + version + m.group(2), page)
    if buttons != 1 or versions != 1:
        sys.exit(f'Expected one download button and one version label, found {buttons} and {versions}.')
    with open(page_path, 'w', encoding='utf-8') as f:
        f.write(page)
    print(f'Download button -> {url} (version {version})')


if __name__ == '__main__':
    main(sys.argv[1])
