"""数据层异常定义。"""


class FetchError(Exception):
    """数据拉取失败。"""


class LixingerAPIError(Exception):
    """理杏仁 API 调用失败。"""
