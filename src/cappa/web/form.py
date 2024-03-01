from __future__ import annotations

import dataclasses

from cappa import Arg, Command
from cappa.subcommand import Subcommand
from cappa.web.data import UserArgData, UserCommandData
from cappa.web.parameter_controls import ParameterControls
from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Label


@dataclasses.dataclass
class FormControlMeta:
    widget: Widget
    meta: Arg


class CommandForm(Widget):
    DEFAULT_CSS = """    
    .command-form-heading {
        padding: 1 0 0 1;
        text-style: u;
        color: $text;
    }
    .command-form-input {        
        border: tall transparent;
    }
    .command-form-label {
        padding: 1 0 0 1;
    }
    .command-form-checkbox {
        background: $boost;
        margin: 1 0 0 0;
        padding-left: 1;
        border: tall transparent;
    }
    .command-form-checkbox:focus {
      border: tall $accent;      
    }
    .command-form-checkbox:focus > .toggle--label {
        text-style: none;
    }
    .command-form-command-group {
        
        margin: 1 2;
        padding: 0 1;
        height: auto;
        background: $foreground 3%;
        border: panel $background;
        border-title-color: $text 80%;
        border-title-style: bold;
        border-subtitle-color: $text 30%;
        padding-bottom: 1;
    }
    .command-form-command-group:focus-within {
        border: panel $primary;
    }
    .command-form-control-help-text {        
        height: auto;
        color: $text 40%;
        padding-top: 0;
        padding-left: 1;
    }
    """

    class Changed(Message):
        def __init__(self, command_data: UserCommandData):
            super().__init__()
            self.command_data = command_data
            """The new data taken from the form to be converted into a CLI invocation."""

    def __init__(
        self,
        command: Command,
        command_schemas: dict[str, Command] | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ):
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.command = command
        self.command_schemas = command_schemas
        self.first_control: ParameterControls | None = None

    def compose(self) -> ComposeResult:
        path_from_root = iter(reversed([self.command]))  # self.command.path_from_root))
        command_node = next(path_from_root)
        with VerticalScroll() as vs:
            # vs.can_focus = False

            # yield Input(
            #     placeholder="Search...",
            #     classes="command-form-filter-input",
            #     id="search",
            # )

            while command_node is not None:
                arguments = command_node.arguments
                if arguments:
                    with Vertical(
                        classes="command-form-command-group",
                        id=command_node.real_name(),
                    ) as v:
                        is_inherited = command_node is not self.command
                        v.border_title = (
                            f"{'↪ ' if is_inherited else ''}{command_node.name}"
                        )
                        if is_inherited:
                            v.border_title += " [dim not bold](inherited)"

                        yield Label("Arguments", classes="command-form-heading")
                        for argument in arguments:
                            if isinstance(argument, Subcommand):
                                continue

                            controls = ParameterControls(
                                argument, id=argument.field_name
                            )
                            if self.first_control is None:
                                self.first_control = controls
                            yield controls

                command_node = next(path_from_root, None)

                # XXX: Nope
                break

    # def on_mount(self) -> None:
    #     self._form_changed()

    # def on_input_changed(self) -> None:
    #     self._form_changed()
    #
    # def on_select_changed(self) -> None:
    #     self._form_changed()
    #
    # def on_checkbox_changed(self) -> None:
    #     self._form_changed()
    #
    # def on_multiple_choice_changed(self) -> None:
    #     self._form_changed()

    def _form_changed(self) -> None:
        """Take the current state of the form and build a UserCommandData from it,
        then post a FormChanged message
        """
        path_from_root = [self.command]  #  or command_schema.path_from_root

        # Sentinel root value to make constructing the tree a little easier.
        parent_command_data = UserCommandData(name="_", arguments=[])

        root_command_data = parent_command_data
        for command in path_from_root:
            arg_data = []
            # For each of the options in the schema for this command,
            # lets grab the values the user has supplied for them in the form.
            for arg in command.arguments:
                parameter_control = self.query_one(
                    f"#{arg.field_name}", ParameterControls
                )
                value = parameter_control.get_values()
                for v in value.values:
                    assert isinstance(v, tuple)
                    option_data = UserArgData(arg.field_name, v, arg)
                    arg_data.append(option_data)

            assert all(isinstance(option.value, tuple) for option in arg_data)
            command_data = UserCommandData(
                name=command.name,
                arguments=argument_datas,
                parent=parent_command_data,
                command_schema=command,
            )
            parent_command_data.subcommand = command_data
            parent_command_data = command_data

        # Trim the sentinel
        root_command_data = root_command_data.subcommand
        root_command_data.parent = None
        self.post_message(self.Changed(root_command_data))

    def focus(self, scroll_visible: bool = True):
        if self.first_control is not None:
            return self.first_control.focus()

    @on(Input.Changed, ".command-form-filter-input")
    def apply_filter(self, event: Input.Changed) -> None:
        filter_query = event.value
        all_controls = self.query(ParameterControls)
        for control in all_controls:
            filter_query = filter_query.casefold()
            control.apply_filter(filter_query)
