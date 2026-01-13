from __future__ import annotations

from datetime import datetime
from enum import StrEnum, unique
from urllib.parse import urlparse

from bson import ObjectId
from mm_base6 import BaseDb
from mm_mongo import AsyncMongoCollection, MongoModel
from mm_std import utc_delta, utc_now
from pydantic import BaseModel, Field, field_validator


@unique
class Protocol(StrEnum):
    HTTP = "http"
    SOCKS5 = "socks5"


class Source(MongoModel[str]):
    class Default(BaseModel):
        protocol: Protocol
        username: str
        password: str
        port: int

        def url(self, ip: str, port: int | None = None) -> str:
            schema = "socks5" if self.protocol == Protocol.SOCKS5 else "http"
            actual_port = port if port is not None else self.port
            return f"{schema}://{self.username}:{self.password}@{ip}:{actual_port}"

    __collection__ = "source"
    __indexes__ = ["created_at", "checked_at"]

    default: Default | None = None
    link: str | None = None
    items: list[str] = Field(default_factory=list)  # list of proxy urls or hosts
    created_at: datetime = Field(default_factory=utc_now)
    checked_at: datetime | None = None

    @field_validator("link", mode="after")
    def link_validator(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v


@unique
class Status(StrEnum):
    UNKNOWN = "UNKNOWN"
    OK = "OK"
    DOWN = "DOWN"


class Proxy(MongoModel[ObjectId]):
    __collection__ = "proxy"
    __indexes__ = ["!url", "proxy_ip", "source", "protocol", "status", "created_at", "checked_at", "last_ok_at"]

    source: str  # source ID that provided this proxy
    url: str  # full proxy URL (e.g., socks5://user:pass@host:port)
    proxy_ip: str | None = None  # detected IP from check (may differ from hostname for gateway)
    status: Status = Status.UNKNOWN
    protocol: Protocol
    created_at: datetime = Field(default_factory=utc_now)
    checked_at: datetime | None = None
    last_ok_at: datetime | None = None
    check_history: list[bool] = Field(default_factory=list)  # keep last 100 check results; ok=true, down=false

    @property
    def history_ok_count(self) -> int:
        return len([x for x in self.check_history if x is True])

    @property
    def history_down_count(self) -> int:
        return len([x for x in self.check_history if x is False])

    @property
    def endpoint(self) -> str:
        parsed = urlparse(self.url)
        return f"{parsed.hostname}:{parsed.port}"

    @property
    def gateway(self) -> bool | None:
        """True=gateway, False=direct, None=unknown."""
        if self.proxy_ip is None:
            return None
        return self.proxy_ip != urlparse(self.url).hostname

    def is_time_to_delete(self) -> bool:
        # delete me if it was ok last time 1 hour ago
        if self.last_ok_at and self.last_ok_at < utc_delta(hours=-1):
            return True
        # delete me if it was never ok for 1 hour
        return bool(self.last_ok_at is None and self.created_at < utc_delta(hours=-1))

    @classmethod
    def new(cls, source: str, url: str) -> Proxy:
        if not urlparse(url).hostname:
            raise ValueError(f"Invalid proxy URL (no hostname): {url}")
        protocol = Protocol.HTTP if url.startswith("http") else Protocol.SOCKS5
        return Proxy(id=ObjectId(), source=source, url=url, protocol=protocol)


class Db(BaseDb):
    source: AsyncMongoCollection[str, Source]
    proxy: AsyncMongoCollection[ObjectId, Proxy]
