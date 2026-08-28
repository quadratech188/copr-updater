from pathlib import Path

from copr_updater.version import version_to_str

from .version_checker import VersionChecker
from .spec import Spec
import argparse
import logging
import msgspec
import pygit2
import requests
import time

class SignatureConfig(msgspec.Struct):
    name: str
    email: str

class RepoConfig(msgspec.Struct):
    dir: Path
    git_username: str
    git_password: str
    version_checker: VersionChecker
    webhook_url: str | None = None

class Config(msgspec.Struct):
    signature: SignatureConfig
    repos: dict[str, RepoConfig]

parser = argparse.ArgumentParser()

_ = parser.add_argument('--config', default='./config.toml')
_ = parser.add_argument('--local-only', action='store_true')


args = parser.parse_args()

LOCAL_ONLY: bool = args.local_only  # pyright: ignore[reportAny]

with open(args.config) as f: # pyright: ignore[reportAny]
    def dec_hook(type_, obj): # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
        if type_ is Path:
            return Path(obj)  # pyright: ignore[reportUnknownArgumentType]
        raise NotImplementedError

    config = msgspec.toml.decode(f.read(), type=Config, dec_hook=dec_hook)  # pyright: ignore[reportUnknownArgumentType]

SIGNATURE = pygit2.Signature(config.signature.name, config.signature.email, int(time.time()), 0)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

for name, repo_config in config.repos.items():
    repo_config.dir = repo_config.dir.absolute()

    repo = pygit2.Repository(repo_config.dir)
    credentials = pygit2.UserPass(repo_config.git_username, repo_config.git_password)

    if len(repo.remotes) != 1:
        raise Exception('Repository has more than one remote')

    remote = repo.remotes[0]

    logger.info(f'{repo.path}: Fetch {remote.url}')
    _ = remote.fetch(callbacks=pygit2.RemoteCallbacks(credentials), prune=pygit2.enums.FetchPrune.PRUNE)

    branch = repo.lookup_branch(repo.head.shorthand)

    logger.info(f'{repo.path}: Reset to {branch.upstream.shorthand}')
    repo.reset(branch.upstream.target, pygit2.enums.ResetMode.HARD)

    specs = list(repo_config.dir.glob('*.spec'))
    if len(specs) != 1:
        raise Exception('Repository doesn\'t have exactly 1 spec file')

    spec_path = specs[0]

    spec = Spec(spec_path.read_text())
    latest_version = repo_config.version_checker.latest_version()

    logger.info(f'{spec_path}: {spec.version} -> {latest_version}')

    if spec.version >= latest_version:
        continue

    spec.version = latest_version
    if spec.release != '%autorelease':
        spec.release = 1

    _ = spec_path.write_text(spec.text())

    repo.index.add(spec_path.relative_to(repo.workdir))
    repo.index.write()

    commit_message = f'auto: Bump {spec_path.name} to version {version_to_str(spec.version)}'

    logger.info(f'{repo.path}: Create commit | {commit_message}')
    _ = repo.create_commit(
        repo.head.name,
        SIGNATURE,
        SIGNATURE,
        commit_message,
        repo.index.write_tree(),
        [repo.head.target]
    )

    if LOCAL_ONLY: continue

    remote.push([repo.head.name], callbacks=pygit2.RemoteCallbacks(credentials))

    if repo_config.webhook_url:
        webhook_url = f'{repo_config.webhook_url}{spec.name}/'
        logger.info(f'{repo.path}: Run webhook')
        requests.post(webhook_url).raise_for_status()
