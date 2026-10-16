"""Generated and explicitly requested Page names are preserved."""
import asyncio
from unittest import mock

import pytest

import client_app
from facebook import page_creator


@pytest.fixture
def fixed_person_name():
    with mock.patch.object(page_creator, "HO_VIET", ["Hoàng"]), \
         mock.patch.object(page_creator, "DEM_VIET", ["Gia"]), \
         mock.patch.object(page_creator, "TEN_VIET", ["Hùng"]), \
         mock.patch.object(page_creator.random, "choice", side_effect=lambda values: values[-1]):
        yield "Hoàng Gia Hùng"


@pytest.mark.parametrize("generator", [page_creator.generate_random_person_name,
                                       client_app.generate_random_person_name])
def test_generated_name_has_no_suffix(generator, fixed_person_name):
    assert generator() == fixed_person_name


@pytest.mark.parametrize("count", [1, 4])
def test_generated_page_plans_do_not_append_labels_or_numbers(count, fixed_person_name):
    plans = client_app.build_create_page_plans([], count)
    assert len(plans) == count
    assert [page_creator.parse_page_plan(plan)["name"] for plan in plans] == [fixed_person_name] * count


@pytest.mark.parametrize("plan,category", [("", "Blog cá nhân"), ("|Spa", "Spa")])
def test_missing_name_uses_only_person_name(plan, category, fixed_person_name):
    assert page_creator.parse_page_plan(plan) == {"name": fixed_person_name, "category": category}


@pytest.mark.parametrize("plan,category", [("Hoàng Gia Hùng", "Blog cá nhân"),
                                           ("Hoàng Gia Hùng|Spa", "Spa")])
def test_explicit_person_name_and_category_are_preserved(plan, category):
    assert page_creator.parse_page_plan(plan) == {"name": "Hoàng Gia Hùng", "category": category}


@pytest.mark.parametrize("alert_text,name_invalid", [
    ("Please choose a category", False),
    ("Suggested categories", False),
    ("Hạng mục không hợp lệ", False),
    ("Invalid Page name", True),
])
def test_create_flow_never_renames_page_from_alert(alert_text, name_invalid):
    from test_targeted_runtime import make_app

    app = make_app()
    app.is_running = True
    app.publish_create_page_result = mock.Mock(return_value=True)
    app.human_type = mock.AsyncMock()
    app.human_clear = mock.AsyncMock()
    app.select_page_category = mock.AsyncMock(return_value=(False, "CATEGORY_NOT_FOUND"))
    name = mock.Mock(
        wait_for=mock.AsyncMock(), scroll_into_view_if_needed=mock.AsyncMock(),
        click=mock.AsyncMock(), focus=mock.AsyncMock(), fill=mock.AsyncMock(),
        get_attribute=mock.AsyncMock(return_value="true" if name_invalid else None),
    )
    category = mock.Mock(
        scroll_into_view_if_needed=mock.AsyncMock(), click=mock.AsyncMock(),
        focus=mock.AsyncMock(), get_attribute=mock.AsyncMock(return_value=None),
        is_visible=mock.AsyncMock(return_value=True),
    )
    alert = mock.Mock(is_visible=mock.AsyncMock(return_value=True),
                      inner_text=mock.AsyncMock(return_value=alert_text))
    alerts = mock.Mock(first=alert, count=mock.AsyncMock(return_value=1))
    names = mock.Mock(first=name, count=mock.AsyncMock(return_value=1))
    categories = mock.Mock(count=mock.AsyncMock(return_value=1))
    categories.nth.return_value = category
    empty = mock.Mock(count=mock.AsyncMock(return_value=0))

    def locate(selector):
        if 'role="alert"' in selector or "đề xuất" in selector:
            return alerts
        if "Page name" in selector:
            return names
        if "Category" in selector:
            return categories
        return empty

    page = mock.Mock(url="https://www.facebook.com/pages/creation/", frames=[],
                     goto=mock.AsyncMock(), title=mock.AsyncMock(return_value="Create a Page"))
    page.locator.side_effect = locate
    requested = "Hoàng Gia Hùng"
    with mock.patch.object(page_creator.asyncio, "sleep", new=mock.AsyncMock()), \
         mock.patch.object(page_creator, "generate_random_person_name") as generate_name:
        records = asyncio.run(app.run_create_page(
            page, mock.Mock(), "111111", 1, targets=[f"{requested}|Spa"], max_pages=1,
        ))

    assert len(records) == 1
    assert records[0]["page_name"] == requested
    assert records[0]["status"] == "FAILED"
    assert records[0]["reason"] == ("PAGE_NAME_INVALID" if name_invalid else "CATEGORY_NOT_FOUND")
    app.human_type.assert_any_await(page, name, requested)
    assert [call.args[2] for call in app.human_type.await_args_list if call.args[1] is name] == [requested]
    app.human_clear.assert_not_awaited()
    name.fill.assert_not_awaited()
    generate_name.assert_not_called()
    page.get_by_role.assert_not_called()
    assert app.select_page_category.await_count == int(not name_invalid)
