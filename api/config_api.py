"""
Config API - get/update runtime configuration
"""

from fastapi import APIRouter
from pydantic import BaseModel

from config.defaults import get_defaults, update_defaults
from config.settings import get_settings

router = APIRouter(prefix="/config")


@router.get("/")
async def get_config():
    settings = get_settings()
    defaults = get_defaults()
    return {
        "llm": {
            "api_url": settings.llm_api_url,
            "model": settings.llm_model,
            "max_tokens": settings.llm_max_tokens,
            "temperature": settings.llm_temperature,
        },
        "server": {
            "host": settings.host,
            "port": settings.port,
        },
        "defaults": defaults,
    }


class ConfigUpdate(BaseModel):
    key: str
    value: dict


@router.post("/update")
async def update_config(update: ConfigUpdate):
    update_defaults(update.value)
    return {"status": "updated", "key": update.key}


class WechatRegionsUpdate(BaseModel):
    taskbarRegion: list[int] | None = None
    chatListRegion: list[int] | None = None
    chatContentRegion: list[int] | None = None
    inputBoxRegion: list[int] | None = None


@router.post("/wechat-regions")
async def save_wechat_regions(regions: WechatRegionsUpdate):
    defaults = get_defaults()
    wechat = defaults.setdefault("wechat", {})

    mapping = {
        "taskbarRegion": "taskbar_region",
        "chatListRegion": "chat_list_region",
        "chatContentRegion": "chat_content_region",
        "inputBoxRegion": "input_box_region",
    }

    for field, key in mapping.items():
        value = getattr(regions, field)
        if value is not None:
            wechat[key] = value

    update_defaults(defaults)
    return {"status": "updated"}
