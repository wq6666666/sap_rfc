from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, List


class DynamicRFCRequest(BaseModel):
    rfc_name: str = Field(..., description="SAP RFC 函数模块名称")
    import_params: Dict[str, Any] = Field(default_factory=dict, description="IMPORTING 参数")
    changing_params: Dict[str, Any] = Field(default_factory=dict, description="CHANGING 参数")
    table_params: Dict[str, List[Dict]] = Field(default_factory=dict, description="TABLES 参数")


class DynamicRFCResponse(BaseModel):
    status: str
    export_params: Dict[str, Any]  # EXPORTING 参数
    changing_params: Dict[str, Any]  # 返回的 CHANGING 参数
    table_params: Dict[str, Any]  # 返回的 TABLES 参数