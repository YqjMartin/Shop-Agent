"""监控端点"""
import os
import psutil
from fastapi import APIRouter
from app.middleware.rate_limit import get_rate_limit_store, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW

router = APIRouter()


def _get_disk_usage() -> psutil.sdiskusage:
    """跨平台获取系统盘使用率"""
    if os.name == "nt":
        drive = os.path.splitdrive(os.getcwd())[0] or "C:\\"
        return psutil.disk_usage(drive)
    else:
        return psutil.disk_usage("/")


@router.get("/health")
async def health_check():
    """健康检查端点"""
    disk = _get_disk_usage()
    return {
        "status": "healthy",
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": disk.percent,
    }


@router.get("/stats")
async def get_stats():
    """获取API使用统计"""
    store = get_rate_limit_store()
    total_requests = sum(len(v) for v in store.values())
    active_ips = len(store)

    return {
        "total_requests": total_requests,
        "active_ips": active_ips,
        "rate_limit": {
            "max_requests_per_minute": RATE_LIMIT_REQUESTS,
            "window_seconds": RATE_LIMIT_WINDOW
        }
    }