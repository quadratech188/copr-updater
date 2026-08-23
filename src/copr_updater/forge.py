from typing import override
import logging
import re
import requests
import urllib.parse

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Forge:
    def latest_version(self) -> str:
        raise NotImplementedError

    @classmethod
    def get(cls, url: str):
        if 'github' in url:
            return Github(url)
        else:
            raise Exception('Unknown forge')

class Github(Forge):
    def __init__(self, url: str):
        parsed = urllib.parse.urlsplit(url)

        (account, repo) = parsed.path[1:].split('/')

        self.account: str = account
        self.repo: str = repo

    @override
    def latest_version(self) -> str:
        logger.debug(requests.get('https://api.github.com/rate_limit').content)

        url = f'https://api.github.com/repos/{self.account}/{self.repo}/releases/latest'
        response = requests.get(url)

        logger.debug(requests.get('https://api.github.com/rate_limit').content)

        if not response.ok:
            logger.debug(response.headers)

        response.raise_for_status()
        tag = str(response.json()['tag_name']) # pyright: ignore[reportAny]

        match = re.match('v(?P<v>[0-9.]+)$', tag)
        if match is None:
            raise Exception('Unknown tag format')
        return match.group('v')
