from pathlib import Path
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
    webhook_url: str | None

class Config(msgspec.Struct):
    signature: SignatureConfig
    repos: dict[str, RepoConfig]

parser = argparse.ArgumentParser()

_ = parser.add_argument('--config', default='./config.toml')
args = parser.parse_args()

with open(args.config) as f: # pyright: ignore[reportAny]
    def dec_hook(type_, obj): # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
        if type_ is Path:
            return Path(obj)  # pyright: ignore[reportUnknownArgumentType]
        raise NotImplementedError

    config = msgspec.toml.decode(f.read(), type=Config, dec_hook=dec_hook)  # pyright: ignore[reportUnknownArgumentType]

SIGNATURE = pygit2.Signature(config.signature.name, config.signature.email, int(time.time()), 0)

logger = logging.getLogger(__name__)

for name, repo_config in config.repos.items():
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

    for spec_path in repo_config.dir.glob('*.spec'):
        spec = Spec(spec_path.read_text())

        latest_version = spec.forge.latest_version()

        if spec.version >= latest_version: continue

        spec.version = latest_version
        spec.release = 0

        _ = spec_path.write_text(spec.text())

        repo.index.add(spec_path)
        repo.index.write()

        commit_message = f'auto: Bump {spec_path.name} to version {spec.version}'

        logger.info(f'{repo.path}: Create commit | {commit_message}')
        _ = repo.create_commit(
            repo.head.name,
            SIGNATURE,
            SIGNATURE,
            commit_message,
            repo.index.write_tree(),
            [repo.head.target]
        )

        tag_name = f'{spec.name}-{spec.version}-{spec.release}'

        logger.info(f'{repo.path}: Create tag | {tag_name}')
        _ = repo.create_tag(tag_name, repo.head.target, pygit2.enums.ObjectType.COMMIT, SIGNATURE, '')

        remote.push([repo.head.name], callbacks=pygit2.RemoteCallbacks(credentials))

        if repo_config.webhook_url:
            requests.post(f'{repo_config.webhook_url}{spec.name}/').raise_for_status()
