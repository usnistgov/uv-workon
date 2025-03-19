from __future__ import annotations

from typing import TYPE_CHECKING

from uv_workon.utils import select_option

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_select_option(mocker: MockerFixture) -> None:
    mock_terminalmenu = mocker.patch("simple_term_menu.TerminalMenu", autospec=True)
    options = ["a", "b"]
    _ = select_option(options, usage=False)
    assert mock_terminalmenu.mock_calls == [
        mocker.call(options, title=None),
        mocker.call().show(),
        mocker.call().show().__index__(),
    ]
