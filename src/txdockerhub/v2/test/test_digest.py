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
Tests for L{txdockerhub.v2._digest}.
"""

from typing import Callable

from hypothesis import given
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.strategies import (
    characters,
    composite,
    integers,
    sampled_from,
    text,
)

from twisted.trial.unittest import SynchronousTestCase

from .._digest import Digest, DigestAlgorithm, InvalidDigestError, hexDigits


__all__ = ()


asHex = hex

#
# Strategies
#


def algorithms() -> SearchStrategy:  # DigestAlgorithm
    """
    Strategy that generates digest algorithms.
    """
    return sampled_from(DigestAlgorithm)


def hexes() -> SearchStrategy:  # str
    """
    Strategy that generates digest hex data.
    """
    return text(min_size=1, alphabet=hexDigits)


def notHexes() -> SearchStrategy:  # str
    """
    Strategy that generates digest non-hex data.
    """
    return text(min_size=1).filter(
        lambda s: not any((c in hexDigits) for c in s)
    )


@composite
def digests(draw: Callable) -> Digest:
    """
    Strategy that generates digests.
    """
    return Digest(
        algorithm=draw(algorithms()), hex=draw(integers(min_value=0)),
    )


class StrategyTests(SynchronousTestCase):
    """
    Tests for test strategies.
    """

    @given(algorithms())
    def test_algorithms(self, algorithm: DigestAlgorithm) -> None:
        """
        Generated algorithms are in the DigestAlgorithm enumeration.
        """
        self.assertIn(algorithm, DigestAlgorithm)

    @given(hexes())
    def test_hexes(self, hex: str) -> None:
        """
        Generated hex data are valid.
        """
        self.assertTrue(any((c in hexDigits) for c in hex))

    @given(notHexes())
    def test_notHexes(self, notHex: str) -> None:
        """
        Generated non-hex data are not hex data.
        """
        self.assertFalse(any((c in hexDigits) for c in notHex))

    @given(digests())
    def test_digests(self, digest: Digest) -> None:
        """
        Generated digests are valid.
        """
        self.assertIsInstance(digest, Digest)


#
# Tests
#


class DigestTests(SynchronousTestCase):
    """
    Tests for Digest.
    """

    @given(algorithms(), hexes())
    def test_fromText(self, algorithm: DigestAlgorithm, hex: str) -> None:
        """
        Digest.fromText() returns a digest from a text representation.
        """
        digest = Digest.fromText(f"{algorithm.name}:{hex}")
        self.assertEqual(digest.algorithm, algorithm)
        self.assertEqual(digest.hex, int(hex, 16))

    @given(text(alphabet=characters(blacklist_characters=":")))
    def test_fromText_noColon(self, text: str) -> None:
        """
        Digest.fromText() raises InvalidDigestError if given a string with no
        ":" character.
        """
        e = self.assertRaises(InvalidDigestError, Digest.fromText, text)
        self.assertEqual(str(e), f"digest must include separator: {text!r}")

    @given(algorithms(), notHexes())
    def test_fromText_badHex(
        self, algorithm: DigestAlgorithm, notHex: str
    ) -> None:
        """
        Digest.fromText() raises InvalidDigestError if given a string with
        invalid hexadecimal data.
        """
        text = f"{algorithm.value}:{notHex}"
        e = self.assertRaises(InvalidDigestError, Digest.fromText, text)
        self.assertEqual(
            str(e), f"invalid hexadecimal data {notHex!r} in digest {text!r}"
        )

    @given(
        text(alphabet=characters(blacklist_characters=":")).filter(
            lambda a: a not in DigestAlgorithm.__members__.values()
        ),
        hexes(),
    )
    def test_fromText_badAlgorithm(self, algorithm: str, hex: str) -> None:
        """
        Digest.fromText() raises InvalidDigestError if given a string with an
        unknown algorithm.
        """
        text = f"{algorithm}:{hex}"
        e = self.assertRaises(InvalidDigestError, Digest.fromText, text)
        self.assertEqual(
            str(e),
            f"unknown digest algorithm {algorithm!r} in digest {text!r}",
        )

    @given(algorithms(), integers())
    def test_init(self, algorithm: DigestAlgorithm, hex: int) -> None:
        """
        Digest() captures the given algorithm and hex data.
        """
        digest = Digest(algorithm=algorithm, hex=hex)
        self.assertEqual(digest.algorithm, algorithm)
        self.assertEqual(digest.hex, hex)

    @given(algorithms(), integers())
    def test_asText(self, algorithm: DigestAlgorithm, hex: int) -> None:
        digestOut = Digest(algorithm=algorithm, hex=hex)
        self.assertEqual(
            digestOut.asText(), f"{algorithm.value}:{asHex(hex)[2:]}"
        )
