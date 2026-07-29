import os
from typing import TypedDict
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlsplit, urlunsplit


class RedisTlsParams(TypedDict):
    ssl: bool
    ssl_ca_certs: str
    ssl_cert_reqs: str


class RedisSecurityParams(RedisTlsParams, total=False):
    password: str


class DatastoreConfig:
    @property
    def INTERNAL_CA_CERT(self) -> str:
        return os.getenv("INTERNAL_CA_CERT", "/run/blacklist/ca.crt")

    @property
    def POSTGRES_HOST(self) -> str:
        return os.getenv("POSTGRES_HOST", "blacklist-postgres")

    @property
    def POSTGRES_PORT(self) -> int:
        return int(os.getenv("POSTGRES_PORT", "5432"))

    @property
    def POSTGRES_DB(self) -> str:
        return os.getenv("POSTGRES_DB", "blacklist")

    @property
    def POSTGRES_USER(self) -> str:
        return os.getenv("POSTGRES_USER", "postgres")

    @property
    def POSTGRES_PASSWORD(self) -> str:
        return os.getenv("POSTGRES_PASSWORD", "postgres")

    @property
    def POSTGRES_FALLBACK_HOSTS(self) -> list[str]:
        raw = os.getenv("POSTGRES_FALLBACK_HOSTS", "blacklist-postgres,postgres,localhost")
        return [host.strip() for host in raw.split(",") if host.strip()]

    @property
    def POSTGRES_URL(self) -> str | None:
        return os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")

    def _postgres_tls_params(self) -> dict[str, str]:
        return {"sslmode": "verify-full", "sslrootcert": self.INTERNAL_CA_CERT}

    def get_postgres_params(self) -> dict[str, int | str]:
        url = self.POSTGRES_URL
        if url:
            parsed = urlparse(url)
            return {
                "host": parsed.hostname or "localhost",
                "port": parsed.port or 5432,
                "database": parsed.path.lstrip("/") or "blacklist",
                "user": parsed.username or "postgres",
                "password": parsed.password or self.POSTGRES_PASSWORD,
                **self._postgres_tls_params(),
            }
        return {
            "host": self.POSTGRES_HOST,
            "port": self.POSTGRES_PORT,
            "database": self.POSTGRES_DB,
            "user": self.POSTGRES_USER,
            "password": self.POSTGRES_PASSWORD,
            **self._postgres_tls_params(),
        }

    def get_postgres_dsn(self) -> str:
        dsn = self.POSTGRES_URL or (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
        parsed = urlsplit(dsn)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query.update(self._postgres_tls_params())
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))

    @property
    def REDIS_HOST(self) -> str:
        return os.getenv("REDIS_HOST", "blacklist-redis")

    @property
    def REDIS_PORT(self) -> int:
        return int(os.getenv("REDIS_PORT", "6379"))

    @property
    def REDIS_PASSWORD(self) -> str:
        return os.getenv("REDIS_PASSWORD", "")

    @property
    def REDIS_URL(self) -> str:
        return self.get_redis_url()

    def get_redis_url(self, database: int | None = None) -> str:
        password = self.REDIS_PASSWORD
        query = urlencode({"ssl_ca_certs": self.INTERNAL_CA_CERT, "ssl_cert_reqs": "required"})
        path = "" if database is None else f"/{database}"
        credentials = f":{quote(password, safe='')}@" if password else ""
        return f"rediss://{credentials}{self.REDIS_HOST}:{self.REDIS_PORT}{path}?{query}"

    def get_redis_auth_params(self) -> RedisSecurityParams:
        params: RedisSecurityParams = {
            "ssl": True,
            "ssl_ca_certs": self.INTERNAL_CA_CERT,
            "ssl_cert_reqs": "required",
        }
        password = self.REDIS_PASSWORD
        if password:
            params["password"] = password
        return params

    def get_redis_params(self) -> dict[str, bool | int | str]:
        auth_params = self.get_redis_auth_params()
        params: dict[str, bool | int | str] = {
            "host": self.REDIS_HOST,
            "port": self.REDIS_PORT,
            "ssl": auth_params["ssl"],
            "ssl_ca_certs": auth_params["ssl_ca_certs"],
            "ssl_cert_reqs": auth_params["ssl_cert_reqs"],
        }
        password = auth_params.get("password")
        if password:
            params["password"] = password
        return params
