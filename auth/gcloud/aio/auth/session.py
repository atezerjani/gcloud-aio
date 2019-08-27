import sys
import threading
from abc import ABC
from abc import abstractmethod
from io import IOBase
from typing import Dict  # pylint: disable=unused-import
from typing import List  # pylint: disable=unused-import
from typing import Optional  # pylint: disable=unused-import
from typing import Union  # pylint: disable=unused-import

import requests


class BaseSession(ABC):
    def __init__(self):
        self._session = None

    # @abstractmethod
    @property
    def session(self):
        return self._session

    @session.setter
    def session(self, session):
        self._session = session

    @abstractmethod
    def post(self, url: str, headers: Dict[str, str], data: str, timeout: int,
             params: Dict[str, str]):
        pass

    @abstractmethod
    def get(self, url: str, headers: Dict[str, str], timeout: int,
            params: Dict[str, str]):
        pass

    @abstractmethod
    def put(self, url: str, headers: Dict[str, str], data: IOBase,
            timeout: int):
        pass

    @abstractmethod
    def delete(self, url: str, headers: Dict[str, str], params: Dict[str, str],
               timeout: int):
        pass

if sys.version_info[0] >= 3:
    import aiohttp
    class AioSession(BaseSession):
        def __init__(self, conn_timeout: int = 10, read_timeout: int = 10):
            super().__init__()
            self.conn_timeout = conn_timeout
            self.read_timeout = read_timeout

        @property
        def session(self) -> aiohttp.ClientSession:
            self._session = self._session or aiohttp.ClientSession(
                conn_timeout=self.conn_timeout, read_timeout=self.read_timeout)
            return self._session

        @session.setter
        def session(self, session: aiohttp.ClientSession):
            self._session = session

        async def post(self, url: str, headers: Dict[str, str],
                       data: str = None, timeout: int = 10,
                       params: Dict[str, str] = None
                       ) -> aiohttp.ClientResponse:
            resp = await self.session.post(url, data=data, headers=headers,
                                           timeout=timeout, params=params)
            resp.raise_for_status()
            return resp

        async def get(self, url: str, headers: Dict[str, str] = None,
                      timeout: int = 10, params: Dict[str, str] = None
                      ) -> aiohttp.ClientResponse:
            resp = await self.session.get(url, headers=headers, timeout=timeout,
                                          params=params)
            resp.raise_for_status()
            return resp

        async def put(self, url: str, headers: Dict[str, str], data: IOBase,
                      timeout: int = 10) -> aiohttp.ClientResponse:
            resp = await self.session.put(url, data=data, headers=headers,
                                          timeout=timeout)
            resp.raise_for_status()
            return resp

        async def delete(self, url: str, headers: Dict[str, str],
                         params: Dict[str, str], timeout: int = 10
                         ) -> aiohttp.ClientResponse:
            resp = await self.session.delete(url, headers=headers,
                                             params=params, timeout=timeout)
            resp.raise_for_status()
            return resp


class SyncSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.google_api_lock = threading.RLock()

    @property
    def session(self) -> requests.Session:
        self._session = self._session or requests.Session()
        return self._session

    @session.setter
    def session(self, session: requests.Session):
        self._session = session

    def post(self, url: str, headers: Dict[str, str], data: str = None,
             timeout: int = 10, params: Dict[str, str] = None
             ) -> requests.Response:
        with self.google_api_lock:
            resp = self.session.post(url, data=data, headers=headers,
                                     timeout=timeout, params=params)
        resp.raise_for_status()
        return resp

    def get(self, url: str, headers: Dict[str, str] = None, timeout: int = 10,
            params: Dict[str, str] = None) -> requests.Response:
        with self.google_api_lock:
            resp = self.session.get(url, headers=headers, timeout=timeout,
                                    params=params)
        resp.raise_for_status()
        return resp

    def put(self, url: str, headers: Dict[str, str], data: IOBase,
            timeout: int = 10) -> requests.Response:
        with self.google_api_lock:
            resp = self.session.put(url, data=data, headers=headers,
                                    timeout=timeout)
        resp.raise_for_status()
        return resp

    def delete(self, url: str, headers: Dict[str, str], params: Dict[str, str],
               timeout: int = 10) -> requests.Response:
        with self.google_api_lock:
            resp = self.session.delete(url, params=params, headers=headers,
                                       timeout=timeout)
        resp.raise_for_status()
        return resp
