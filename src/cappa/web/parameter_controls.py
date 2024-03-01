from __future__ import annotations
import typing

import functools
from functools import partial
from typing import Any, Callable, Iterable, TypeVar, Union, cast, Iterator

from cappa import Arg
from cappa.arg import ArgAction
from cappa.web.multiple_choice import MultipleChoice
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.widget import Widget
from textual.widgets import (
    Button,
    Checkbox,
    Input,
    Label,
    Select,
    Static,
)

ControlWidgetType: TypeVar = Union[Input, Checkbox, MultipleChoice, Select]


class ControlGroup(Vertical):
    pass


class ControlGroupsContainer(Vertical):
    pass


@functools.total_ordering
class ValueNotSupplied:
    def __eq__(self, other):
        return isinstance(other, ValueNotSupplied)

    def __lt__(self, other):
        return False

    def __bool__(self: Arg):
        is_text_type = argument_type in text_click_types or isinstance(
            argument_type, text_types
        )
        if is_text_type:
            return self.make_text_control
        elif argument_type == click.BOOL:
            return self.make_checkbox_control
        elif isinstance(argument_type, click.types.Choice):
            return partial(self.make_choice_control, choices=argument_type.choices)
        else:
            return self.make_text_control


class ParameterControls(Widget):
    def __init__(
        self,
        arg: Arg,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.arg = arg
        self.first_control: Widget | None = None

    def apply_filter(self, filter_query: str) -> bool:
        """Show or hide this ParameterControls depending on whether it matches the filter query or not.

        Args:
            filter_query: The string to filter on.

        Returns:
            True if the filter matched (and the widget is visible).
        """
        help_text = getattr(self.arg, "help", "") or ""
        if not filter_query:
            should_be_visible = True
            self.display = should_be_visible
        else:
            name = self.arg.name
            if isinstance(name, str):
                # Argument names are strings, there's only one name
                name_contains_query = filter_query in name.casefold()
                should_be_visible = name_contains_query
            else:
                # Option names are lists since they can have multiple names (e.g. -v and --verbose)
                name_contains_query = any(
                    filter_query in name.casefold() for name in self.arg.name
                )
                help_contains_query = filter_query in help_text.casefold()
                should_be_visible = name_contains_query or help_contains_query

            self.display = should_be_visible

        # Update the highlighting of the help text
        if help_text:
            try:
                help_label = self.query_one(".command-form-control-help-text", Static)
                new_help_text = Text(help_text)
                new_help_text.highlight_words(
                    filter_query.split(), "black on yellow", case_sensitive=False
                )
                help_label.update(new_help_text)
            except NoMatches:
                pass

        return should_be_visible

    def compose(self) -> ComposeResult:
        arg: Arg = self.arg
        name = arg.field_name
        required = typing.cast(bool, arg.required)
        help_text = getattr(arg, "help", "") or ""
        multiple = arg.action == ArgAction.append

        label = self._make_command_form_control_label(
            name, arg, required, multiple=multiple
        )

        # The widget that will be focused when the form is focused.
        first_focus_control: Widget | None = None

        # If there are N defaults, we render the "group" N times.
        # Each group will contain `nargs` widgets.
        with ControlGroupsContainer():
            if arg.action not in {ArgAction.store_true, ArgAction.store_false}:
                yield Label(label, classes="command-form-label")

            if arg.choices and arg.multiple:
                # Display a MultipleChoice widget
                # There's a special case where we have a Choice with multiple=True,
                # in this case, we can just render a single MultipleChoice widget
                # instead of multiple radio-sets.
                control_method = self.get_control_method(arg)
                multiple_choice_widget = control_method(
                    default=arg.default,
                    label=label,
                    multiple=True,
                    schema=arg,
                    control_id=arg.field_name,
                )
                yield from multiple_choice_widget
            # else:
            #     # For other widgets, we'll render as normal...
            #     # If required, we'll generate widgets containing the defaults
            #     for default_value_tuple in default.values:
            #         widget_group = list(self.make_widget_group())
            #         with ControlGroup() as control_group:
            #             if len(widget_group) == 1:
            #                 control_group.add_class("single-item")
            #
            #             # Parameter types can be of length 1, but there could still
            #             # be multiple defaults. We need to render a widget for each
            #             # of those defaults. Extend the widget group such that
            #             # there's a slot available for each default...
            #             for default_value, control_widget in zip(
            #                 default_value_tuple, widget_group
            #             ):
            #                 self._apply_default_value(control_widget, default_value)
            #                 yield control_widget
            #                 # Keep track of the first control we render, for easy focus
            #                 if first_focus_control is None:
            #                     first_focus_control = control_widget
            #
            #     # We always need to display the original group of controls,
            #     # regardless of whether there are defaults
            #     if multiple or not default.values:
            #         widget_group = list(self.make_widget_group())
            #         with ControlGroup() as control_group:
            #             if len(widget_group) == 1:
            #                 control_group.add_class("single-item")
            #
            #             # No need to apply defaults to this group
            #             for control_widget in widget_group:
            #                 yield control_widget
            #                 if first_focus_control is None:
            #                     first_focus_control = control_widget

        # Take note of the first form control, so we can easily focus it
        if self.first_control is None:
            self.first_control = first_focus_control

        # If it's a multiple, and it's a Choice parameter, then we display
        # our special case MultiChoice widget, and so there's no need for this
        # button.
        if multiple or arg.num_args == -1 and arg.choices:
            with Horizontal(classes="add-another-button-container"):
                yield Button("+ value", variant="success", classes="add-another-button")

        # Render the dim help text below the form controls
        if help_text:
            yield Static(help_text, classes="command-form-control-help-text")

    def make_widget_group(self) -> Iterable[Widget]:
        """For this option, yield a single set of widgets required to receive user input for it."""
        arg = self.arg
        default = arg.default
        parameter_type = arg.type
        multiple = arg.multiple
        assert arg.required is not None
        label = self._make_command_form_control_label(
            arg.value_name, arg, arg.required, multiple
        )

        # For each of the these parameters, render the corresponding widget for it.
        # At this point we don't care about filling in the default values.
        for _type in parameter_types:
            control_method = self.get_control_method(_type)
            control_widgets = control_method(
                default, label, multiple, arg, arg.field_name
            )
            yield from control_widgets

    @on(Button.Pressed, ".add-another-button")
    def add_another_widget_group(self, event: Button.Pressed) -> None:
        widget_group = list(self.make_widget_group())
        widget_group[0].focus()
        control_group = ControlGroup(*widget_group)
        if len(widget_group) <= 1:
            control_group.add_class("single-item")
        control_groups_container = self.query_one(ControlGroupsContainer)
        control_groups_container.mount(control_group)
        event.button.scroll_visible(animate=False)

    @staticmethod
    def _apply_default_value(
        control_widget: ControlWidgetType, default_value: Any
    ) -> None:
        """Set the default value of a parameter-handling widget."""
        if isinstance(control_widget, Input):
            control_widget.value = str(default_value)
            control_widget.placeholder = f"{default_value} (default)"
        elif isinstance(control_widget, Select):
            control_widget.value = str(default_value)
            control_widget.prompt = f"{default_value} (default)"

    @staticmethod
    def _get_form_control_value(control: ControlWidgetType) -> Any:
        if isinstance(control, MultipleChoice):
            return control.selected
        if isinstance(control, Select):
            if control.value is None:
                return ValueNotSupplied()
            return control.value
        if isinstance(control, Input):
            return (
                ValueNotSupplied() if control.value == "" else control.value
            )  # TODO: We should only return "" when user selects a checkbox - needs custom widget.
        if isinstance(control, Checkbox):
            return control.value

    def get_values(self) -> ...:
        # We can find all relevant control widgets by querying the parameter schema
        # key as a class.

        def list_to_tuples(
            lst: list[int | float | str], tuple_size: int
        ) -> list[tuple[int | float | str, ...]]:
            if tuple_size == 0:
                return [tuple()]
            elif tuple_size == -1:
                # Unspecified number of arguments as per Click docs.
                tuple_size = 1
            return [
                tuple(lst[i : i + tuple_size]) for i in range(0, len(lst), tuple_size)
            ]

        controls = list(self.query(f".{self.arg.field_name}"))

        if len(controls) == 1 and isinstance(controls[0], MultipleChoice):
            # Since MultipleChoice widgets are a special case that appear in
            # isolation, our logic to fetch the values out of them is slightly
            # modified from the nominal case presented in the other branch.
            # MultiChoice never appears for multi-value options, only for options
            # where multiple=True.
            control = cast(MultipleChoice, controls[0])
            control_values = self._get_form_control_value(control)
            # return MultiValueParamData.process_cli_option(control_values)
        else:
            # For each control widget for this parameter, capture the value(s) from them
            collected_values = []
            for control in list(controls):
                control_values = self._get_form_control_value(control)
                collected_values.append(control_values)

            # Since we fetched a flat list of widgets (and thus a flat list of values
            # from those widgets), we now need to group them into tuples based on nargs.
            # We can safely do this since widgets are added to the DOM in the same order
            # as the types specified in the click Option `type`. We convert a flat list
            # of widget values into a list of tuples, each tuple of length nargs.
            collected_values = list_to_tuples(collected_values, self.arg.num_args)
            # return MultiValueParamData.process_cli_option(collected_values)

    def get_control_method(self, arg: Arg):
        if arg.action in {ArgAction.store_true, ArgAction.store_false}:
            return self.make_checkbox_control

        if arg.choices:
            return self.make_choice_control

        return self.make_text_control

    @staticmethod
    def make_text_control(arg: Arg) -> Iterator[Widget]:
        control = Input(
            classes=f"command-form-input {arg.field_name}",
        )
        yield control
        return control

    @staticmethod
    def make_checkbox_control(arg: Arg) -> Iterator[Widget]:
        control = Checkbox(
            arg.value_name,
            button_first=True,
            classes=f"command-form-checkbox {arg.field_name}",
            value=arg.default or False,
        )
        yield control
        return control

    @staticmethod
    def make_choice_control(arg: Arg) -> Iterator[Widget]:
        assert arg.choices
        if arg.multiple:
            multi_choice = MultipleChoice(
                [Text(c) for c in arg.choices],
                classes=f"command-form-multiple-choice {arg.field_name}",
                defaults=arg.default,
            )
            yield multi_choice
            return multi_choice
        else:
            select = Select(
                [(choice, choice) for choice in arg.choices],
                classes=f"{arg.field_name} command-form-select",
            )
            yield select
            return select

    @staticmethod
    def _make_command_form_control_label(
        name: str | list[str],
        arg: Arg,
        is_required: bool,
        multiple: bool,
    ) -> Text:
        if isinstance(name, str):
            text = Text.from_markup(
                f"{name}[dim]{' multiple' if multiple else ''} {arg.parse}[/] {' [b red]*[/]required' if is_required else ''}"
            )
        else:
            names = Text(" / ", style="dim").join([Text(n) for n in name])
            text = Text.from_markup(
                f"{names}[dim]{' multiple' if multiple else ''} {arg.parse}[/] {' [b red]*[/]required' if is_required else ''}"
            )

        return text

    def focus(self, scroll_visible: bool = True):
        if self.first_control is not None:
            self.first_control.focus()
        return False
