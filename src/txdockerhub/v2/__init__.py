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
Docker Hub API v2 Client

See: https://docs.docker.com/registry/spec/api/
"""

from ._client import Client
from ._digest import Digest, DigestAlgorithm, InvalidDigestError
from ._error import Error, ErrorCode
from ._repository import InvalidRepositoryNameError, Repository


__all__ = (
    "Client",
    "Digest",
    "DigestAlgorithm",
    "Error",
    "ErrorCode",
    "InvalidDigestError",
    "InvalidRepositoryNameError",
    "ProtocolError",
    "ProtocolNotSupportedError",
    "Repository",
)
