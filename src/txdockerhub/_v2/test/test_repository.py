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
Tests for L{txdockerhub._v2._repository}.
"""

from re import compile as regexCompile
from typing import Any, Callable, Optional, Sequence

from hypothesis import assume, given, note
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.strategies import (
    characters, composite, data, integers, just, lists,
    one_of, sampled_from, text, tuples,
)

from twisted.trial.unittest import SynchronousTestCase

from .._repository import InvalidRepositoryNameError, Repository

# FIXME: Not publicly available from hypothesis
DataStrategy = Any


__all__ = ()


componentRegexText = "[a-z0-9]+(?:[._-][a-z0-9]+)*"
componentRegex = regexCompile(f"^{componentRegexText}$")

repositoryNameRegexText = f"{componentRegexText}(?:{componentRegexText})*"
repositoryNameRegex = regexCompile(f"^{repositoryNameRegexText}$")


#
# Strategies
#

def componentText(
    min_size: int = 1, max_size: Optional[int] = None
) -> SearchStrategy:  # str
    """
    Strategy that generates repository name path components without separators.
    """
    return text(
        alphabet=Repository.componentCharacters,
        min_size=min_size, max_size=max_size,
    )


def componentSeparators() -> SearchStrategy:  # str
    """
    Strategy that generates repository name path component separators.
    """
    return sampled_from(Repository.componentSeparators)


@composite
def components(
    draw: Callable, max_size: int = Repository.maxComponentLength
) -> str:
    """
    Strategy that generates repository name path components.
    """
    # Must start with one or more characters
    component: str = draw(componentText(max_size=max_size))

    # Add a separator and one or more characters up to max_size
    while True:
        maxLength = max_size - len(component) - 1
        if maxLength < 1:
            # No room left
            break

        rest: str = draw(
            one_of(
                just(""),  # Opportunity to stop before max_size
                tuples(
                    componentSeparators(),
                    componentText(max_size=maxLength),
                ),
            )
        )
        if not rest:
            break

        component += "".join(rest)

    return component


@composite
def repositoryNames(
    draw: Callable, max_size: int = Repository.maxRepositoryNameLength
) -> str:
    """
    Strategy that generates repository names.
    """
    name: str = draw(components())

    # Add a separator and one or more characters up to max_size
    while True:
        maxLength = min(
            Repository.maxComponentLength,
            max_size - len(name) - 1,
        )
        if maxLength < 1:
            # No room left
            break

        component: str = draw(
            one_of(
                just(""),  # Opportunity to stop before max_size
                components(max_size=maxLength),
            )
        )
        if not component:
            break

        name += f"{Repository.repositoryNameSeparator}{component}"

    return name



class StrategyTests(SynchronousTestCase):
    """
    Tests for test strategies.
    """

    @given(data())
    def test_components_length(self, data: DataStrategy) -> None:
        """
        Generated repository name path components may not exceed the allowed
        size bounds.
        """
        max_size = data.draw(integers(min_value=1), label="max_size")
        component = data.draw(components(max_size=max_size), label="component")

        self.assertGreaterEqual(len(component), 1)
        self.assertLessEqual(len(component), max_size)


    @given(components())
    def test_components_regex(self, component: str) -> None:
        """
        Generated repository name path components match the required regular
        expression.
        """
        self.assertRegex(component, componentRegex)


    @given(data())
    def test_repositoryNames_maxLength(self, data: DataStrategy) -> None:
        """
        Generated repository name may not exceed the allowed size bounds.
        """
        max_size = data.draw(integers(min_value=1), label="max_size")
        name = data.draw(repositoryNames(max_size=max_size), label="name")

        self.assertGreater(len(name), 0)
        self.assertLessEqual(len(name), Repository.maxRepositoryNameLength)


    @given(repositoryNames())
    def test_repositoryNames_validComponents(self, name: str) -> None:
        """
        Generated repository names are composed of valid components.
        """
        for component in name.split(Repository.repositoryNameSeparator):
            try:
                Repository.validateRepositoryNameComponent(component)
            except InvalidRepositoryNameError as e:  # pragma: no cover
                self.fail(
                    f"Invalid path component {component!r} "
                    f"in repository name {name!r}: {e}"
                )



#
# Tests
#

class RepositoryTests(SynchronousTestCase):
    """
    Tests for Repository.
    """

    @given(lists(components(), min_size=1))
    def test_repositoryNameComponents(
        self, componentsIn: Sequence[str]
    ) -> None:
        """
        Repository.repositoryNameComponents() properly splits a repository name
        into its path components.
        """
        name = Repository.repositoryNameSeparator.join(componentsIn)
        componentsOut = Repository.repositoryNameComponents(name)
        self.assertSequenceEqual(componentsIn, componentsOut)


    def test_repositoryNameComponents_empty(self) -> None:
        """
        Repository.repositoryNameComponents() raises InvalidRepositoryNameError
        if given an empty repository name.
        """
        e = self.assertRaises(
            InvalidRepositoryNameError,
            Repository.repositoryNameComponents, "",
        )
        self.assertEqual(str(e), "repository name may not be empty")


    @given(components())
    def test_validateRepositoryNameComponent(self, component: str) -> None:
        """
        Repository.validateRepositoryNameComponent() does not raise
        InvalidRepositoryNameError for valid repository name path components.
        """
        try:
            Repository.validateRepositoryNameComponent(component)
        except InvalidRepositoryNameError as e:  # pragma: no cover
            self.fail(f"Unexpected InvalidRepositoryNameError: {e}")


    def test_validateRepositoryNameComponent_empty(self) -> None:
        """
        Repository.validateRepositoryNameComponent() raises
        InvalidRepositoryNameError if given an empty repository name path
        component.
        """
        e = self.assertRaises(
            InvalidRepositoryNameError,
            Repository.validateRepositoryNameComponent, "",
        )
        self.assertEqual(
            str(e), "repository name path component may not be empty"
        )


    @given(
        sampled_from(Repository.componentCharacters),
        text(
            alphabet=Repository.componentAlphabet,
            min_size=(Repository.maxComponentLength - 1),
            max_size=(Repository.maxComponentLength + 1),
        ),
        sampled_from(Repository.componentCharacters),
    )
    def test_validateRepositoryNameComponent_maxLength(
        self, first: str, middle: str, last: str
    ) -> None:
        """
        Repository.validateRepositoryNameComponent() raises
        InvalidRepositoryNameError if given a repository name path component
        exceeds the allowed maximum size.
        """
        component = f"{first}{middle}{last}"

        e = self.assertRaises(
            InvalidRepositoryNameError,
            Repository.validateRepositoryNameComponent, component,
        )
        self.assertEqual(
            str(e), (
                f"repository name path component may not exceed "
                f"{Repository.maxComponentLength} characters"
            ),
        )


    @given(
        text(
            alphabet=characters(
                blacklist_characters=Repository.componentCharacters
            ),
            min_size=1, max_size=1,
        ),
        one_of(
            just(""), components(max_size=(Repository.maxComponentLength - 1))
        ),
    )
    def test_validateRepositoryNameComponent_leading(
        self, prefix: str, suffix: str
    ) -> None:
        """
        Repository.validateRepositoryNameComponent() raises
        InvalidRepositoryNameError if given an empty repository name path
        component beginning with a character that is not a lowercase
        alphanumeric character.
        """
        component = f"{prefix}{suffix}"
        note(f"Component is {component!r}")

        e = self.assertRaises(
            InvalidRepositoryNameError,
            Repository.validateRepositoryNameComponent, component,
        )
        self.assertEqual(
            str(e), (
                f"repository name path component must start with a "
                f"lowercase alphanumeric character: {component!r}"
            )
        )


    @given(
        componentText(),
        text(
            alphabet=characters(
                blacklist_characters=Repository.componentAlphabet
            ),
            min_size=1,
        ),
        sampled_from(Repository.componentCharacters),
    )
    def test_validateRepositoryNameComponent_rest(
        self, prefix: str, junk: str, last: str
    ) -> None:
        """
        Repository.validateRepositoryNameComponent() raises
        InvalidRepositoryNameError if given an empty repository name path
        component containing invalid characters.
        """
        component = f"{prefix}{junk}{last}"
        assume(len(component) < Repository.maxComponentLength)
        note(f"Component is {component!r}")

        e = self.assertRaises(
            InvalidRepositoryNameError,
            Repository.validateRepositoryNameComponent, component,
        )
        self.assertEqual(
            str(e), (
                f"repository name path component may only contain lowercase "
                f"alphanumeric characters and '.-_': {component!r}"
            )
        )


    @given(
        componentText(max_size=(Repository.maxComponentLength - 1)),
        componentSeparators(),
    )
    def test_validateRepositoryNameComponent_trailingSeparator(
        self, prefix: str, last: str
    ) -> None:
        """
        Repository.validateRepositoryNameComponent() raises
        InvalidRepositoryNameError if given an empty repository name path
        component ending with a character that is not a lowercase alphanumeric
        character.
        """
        component = f"{prefix}{last}"
        note(f"Component is {component!r}")

        e = self.assertRaises(
            InvalidRepositoryNameError,
            Repository.validateRepositoryNameComponent, component,
        )
        self.assertEqual(
            str(e), (
                f"repository name path component must end with a "
                f"lowercase alphanumeric character: {component!r}"
            )
        )


    @given(
        sampled_from(Repository.componentCharacters),
        text(alphabet=Repository.componentAlphabet),
        text(alphabet=Repository.componentSeparators, min_size=2),
        text(alphabet=Repository.componentAlphabet),
        sampled_from(Repository.componentCharacters),
    )
    def test_validateRepositoryNameComponent_separatorRun(
        self, first: str, prefix: str, separators: str, suffix: str, last: str
    ) -> None:
        """
        Repository.validateRepositoryNameComponent() raises
        InvalidRepositoryNameError if given an empty repository name path
        component containing a run of more than one component separator
        character.
        """
        component = f"{first}{prefix}{separators}{suffix}{last}"
        assume(len(component) < Repository.maxComponentLength)
        note(f"Component is {component!r}")

        e = self.assertRaises(
            InvalidRepositoryNameError,
            Repository.validateRepositoryNameComponent, component,
        )
        self.assertEqual(
            str(e), (
                f"repository name path component may not contain more than "
                f"one component separator characters "
                f"({Repository.componentSeparators}) in a row: {component!r}"
            )
        )


    @given(text(min_size=1))
    def test_validateRepositoryNameComponent_regex(
        self, component: str
    ) -> None:
        """
        Repository.validateRepositoryNameComponent() raises
        InvalidRepositoryNameError if given a repository name path component
        that does not match the required regular expression.
        """
        # This is a simpler test than the above component tests and should
        # cover them all, but without testing specific error messages.
        # Conversely, the others should catch anything this catches, but the
        # simpler expression here may catch additional cases.
        try:
            Repository.validateRepositoryNameComponent(component)
        except InvalidRepositoryNameError as e:
            self.assertNotRegex(
                component, componentRegex, (
                    f"{component!r} matches {componentRegex!r} but raised"
                    f"InvalidRepositoryNameError: {e}"
                )
            )
        else:
            self.assertRegex(component, componentRegex)


    def test_validateRepositoryName_empty(self) -> None:
        """
        Repository.validateRepositoryName() raises InvalidRepositoryNameError
        if given an empty repository name.
        """
        e = self.assertRaises(
            InvalidRepositoryNameError,
            Repository.validateRepositoryName, "",
        )
        self.assertEqual(str(e), "repository name may not be empty")


    @given(
        sampled_from(Repository.componentCharacters),
        text(
            alphabet=Repository.componentAlphabet,
            min_size=(Repository.maxRepositoryNameLength - 1),
            max_size=(Repository.maxRepositoryNameLength + 1),
        ),
        sampled_from(Repository.componentCharacters),
    )
    def test_validateRepositoryName_maxLength(
        self, first: str, middle: str, last: str
    ) -> None:
        """
        Repository.validateRepositoryName() raises InvalidRepositoryNameError
        if given a repository name exceeds the allowed maximum size.
        """
        name = f"{first}{middle}{last}"

        e = self.assertRaises(
            InvalidRepositoryNameError,
            Repository.validateRepositoryName, name,
        )
        self.assertEqual(
            str(e), (
                f"repository name may not exceed "
                f"{Repository.maxRepositoryNameLength} characters"
            ),
        )


    @given(text(min_size=1))
    def test_validateRepositoryName_regex(self, name: str) -> None:
        """
        Repository.validateRepositoryName() raises InvalidRepositoryNameError
        if given a repository name that does not match the required regular
        expression.
        """
        try:
            Repository.validateRepositoryName(name)
        except InvalidRepositoryNameError as e:
            self.assertNotRegex(
                name, componentRegex, (
                    f"{name!r} matches {repositoryNameRegex!r} but raised"
                    f"InvalidRepositoryNameError: {e}"
                )
            )
        else:
            self.assertRegex(name, repositoryNameRegex)
