##
# See the file COPYRIGHT for copyright information.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##

"""
Docker Hub API v2 Error
"""

from enum import Enum, unique
from typing import Any, Dict

from attr import attrs


__all__ = ()



@unique
class ErrorCode(Enum):
    """
    Error Code.
    """

    UNKNOWN = "unknown error"

    BLOB_UNKNOWN          = "blob unknown to registry"
    BLOB_UPLOAD_INVALID   = "blob upload invalid"
    BLOB_UPLOAD_UNKNOWN   = "blob upload unknown to registry"
    DIGEST_INVALID        = "provided digest did not match uploaded content"
    MANIFEST_BLOB_UNKNOWN = "manifest blob unknown to registry"
    MANIFEST_INVALID      = "manifest invalid"
    MANIFEST_UNKNOWN      = "manifest unknown"
    MANIFEST_UNVERIFIED   = "manifest failed signature verification"
    NAME_INVALID          = "invalid repository name"
    NAME_UNKNOWN          = "repository name not known to registry"
    SIZE_INVALID          = "provided length did not match content length"
    TAG_INVALID           = "manifest tag did not match URI"
    UNAUTHORIZED          = "authentication required"
    DENIED                = "requested access to the resource is denied"
    UNSUPPORTED           = "operation is unsupported"



@attrs(frozen=True, auto_attribs=True, kw_only=True)
class Error(object):
    """
    Docker Hub API v2 Error.
    """

    @classmethod
    def fromJSON(cls, json: Dict[str, Any]) -> "Error":
        codeName = json.get("code", "UNKNOWN")
        message = json.get("message", "")
        detail = json.get("detail", None)

        code = ErrorCode[codeName]

        return Error(code=code, message=message, detail=detail)


    code: ErrorCode
    message: str
    detail: Any
