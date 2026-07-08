from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file=".env",
        extra="ignore",
        env_file_encoding='utf-8',
        # ✅ 关键：不读取系统环境变量，只读 .env 文件
        env_prefix="",
        case_sensitive=True,
    )
    SAP_HOST:str = "localhost"
    SAP_SYS_NR:str = "00"
    CLIENT:str = "400"
    USER:str = "XUWENQING"
    PASSWORD:str = "123456"
    SAP_LANG:str = "ZH"

    @property
    def conn_config(self) -> dict:
        return {
            "ashost": self.SAP_HOST,
            "sysnr": self.SAP_SYS_NR,
            "client": self.CLIENT,
            "user": self.USER,
            "passwd": self.PASSWORD,
            "lang": self.SAP_LANG,
        }

settings = Settings()
