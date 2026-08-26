import msgspec
import requests
import subprocess

from copr_updater.version import Version, make_version

class GithubRelease(msgspec.Struct, tag="github-release"):
    account: str
    repo: str
    uses_v: bool

    def latest_version(self):
        url = f'https://api.github.com/repos/{self.account}/{self.repo}/releases/latest'
        response = requests.get(url)
        response.raise_for_status()
        tag = str(response.json()['tag_name']) # pyright: ignore[reportAny]

        if self.uses_v:
            tag = tag.removeprefix('v')

        return make_version(tag)

class GitTag(msgspec.Struct, tag="git-tag"):
    remote: str
    uses_v: bool

    def latest_version(self):
        result = subprocess.run(
            ["git", "ls-remote", "--tags", "--refs", self.remote],
            check=True,
            capture_output=True,
            text=True,
        )

        def normalize(line: str):
            try:
                tag = line.split("\t", 1)[1].removeprefix("refs/tags/")
                if self.uses_v:
                    tag = tag.removeprefix('v')
                return make_version(tag)
            except Exception:
                return None

        versions: list[Version] = []

        for line in result.stdout.splitlines():
            x = normalize(line)
            if x is not None:
                versions.append(x)

        return max(versions)
        
VersionChecker = GithubRelease | GitTag
