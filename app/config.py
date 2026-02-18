from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "OpenStack VM Lifecycle API"
    app_version: str = "0.1.0"
    env: str = "development"
    debug: bool = False

    database_url: str = "sqlite+aiosqlite:///./intuitive.db"

    # OpenStack connection settings (used by RealOpenStackClient)
    openstack_auth_url: str = ""
    openstack_project_name: str = ""
    openstack_username: str = ""
    openstack_password: SecretStr = SecretStr("")
    openstack_region: str = "RegionOne"

    use_mock_openstack: bool = True


settings = Settings()
