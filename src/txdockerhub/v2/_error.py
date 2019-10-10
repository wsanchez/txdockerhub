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

from enum import Enum, auto, unique
from typing import Any, Sequence

from attr import attrs


__all__ = ()



class AutoName(Enum):
    @staticmethod
    def _generate_next_value_(
        name: str, start: int, count: int, last_values: Sequence[str]
    ) -> str:
        return name



@unique
class ErrorCode(AutoName):
    """
    Error Code.
    """

    BLOB_UNKNOWN          = auto()
    BLOB_UPLOAD_INVALID   = auto()
    BLOB_UPLOAD_UNKNOWN   = auto()
    DIGEST_INVALID        = auto()
    MANIFEST_BLOB_UNKNOWN = auto()
    MANIFEST_INVALID      = auto()
    MANIFEST_UNKNOWN      = auto()
    MANIFEST_UNVERIFIED   = auto()
    NAME_INVALID          = auto()
    NAME_UNKNOWN          = auto()
    SIZE_INVALID          = auto()
    TAG_INVALID           = auto()
    UNAUTHORIZED          = auto()
    DENIED                = auto()
    UNSUPPORTED           = auto()



@attrs(frozen=True, auto_attribs=True, kw_only=True)
class Error(object):
    """
    Docker Hub API v2 Error.
    """

    code: ErrorCode
    message: str
    detail: Any
