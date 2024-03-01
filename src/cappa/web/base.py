from __future__ import annotations

from pathlib import Path
from typing import ClassVar, TypeVar
from webbrowser import open as open_url

import cappa
from cappa.web.command_info import CommandInfo
from cappa.web.about import AboutDialog
from cappa.web.command_tree import CommandTree
from cappa.web.form import CommandForm
from cappa.web.multiple_choice import NonFocusableVerticalScroll
from rich.highlighter import ReprHighlighter
from rich.text import Text
from textual import events, on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Label,
    Static,
    Tree,
)
from textual.widgets.tree import TreeNode

T = TypeVar("T")


def web(cls):
    command = cappa.collect(cls)
    app = Web(command)
    app.run()


class Web(App):
    CSS_PATH = Path(__file__).parent / "web.scss"

    def __init__(self, cls) -> None:
        super().__init__()

        self.command = cappa.collect(cls)
        self.app_name = self.command.real_name()

    def on_mount(self):
        self.push_screen(CommandBuilder(self.command, self.app_name))

    @on(Button.Pressed, "#home-exec-button")
    def on_button_pressed(self):
        self.exit()

    @on(CommandForm.Changed)
    def update_command_to_run(self, event: CommandForm.Changed):
        include_root_command = not self.command.subcommand
        self.post_run_command = event.command_data.to_cli_args(include_root_command)

    def action_focus_command_tree(self) -> None:
        try:
            command_tree = self.query_one(CommandTree)
        except NoMatches:
            return

        command_tree.focus()

    def action_show_command_info(self) -> None:
        command_builder = self.query_one(CommandBuilder)
        self.push_screen(CommandInfo(command_builder.selected_command))

    def action_visit(self, url: str) -> None:
        open_url(url)


class CommandBuilder(Screen):
    COMPONENT_CLASSES: ClassVar = {"version-string", "prompt", "command-name-syntax"}

    BINDINGS: ClassVar = [
        Binding(key="ctrl+r", action="close_and_run", description="Close & Run"),
        Binding(
            key="ctrl+t", action="focus_command_tree", description="Focus Command Tree"
        ),
        Binding(key="ctrl+o", action="show_command_info", description="Command Info"),
        Binding(key="f1", action="about", description="About"),
    ]

    def __init__(self, command: cappa.Command, command_name: str):
        super().__init__()
        self.command_data = None
        self.command = command
        self.is_grouped_cli = command.subcommand is not None
        self.command_name = command_name

        self.version = None  # get cappa version

        self.highlighter = ReprHighlighter()

    def compose(self) -> ComposeResult:
        tree = CommandTree("Commands", self.command, self.command_name)

        title_parts = [Text(self.command_name, style="b")]
        # if self.version:
        #     version_style = self.get_component_rich_style("version-string")
        #     title_parts.extend(["\n", (f"v{self.version}", version_style)])

        title = Text.assemble(*title_parts)

        sidebar = Vertical(
            Label(title, id="home-commands-label"),
            tree,
            id="home-sidebar",
        )
        if self.is_grouped_cli:
            # If the root of the click app is a Group instance, then
            #  we display the command tree to users and focus it.
            tree.focus()
        else:
            # If the click app is structured using a single command,
            #  there's no need for us to display the command tree.
            sidebar.display = False

        yield sidebar

        with Vertical(id="home-body"):
            with Horizontal(id="home-command-description-container") as vs:
                vs.can_focus = False
                yield Static(self.command_name or "", id="home-command-description")

            scrollable_body = VerticalScroll(
                Static(""),
                id="home-body-scroll",
            )
            scrollable_body.can_focus = False
            yield scrollable_body
            yield Horizontal(
                NonFocusableVerticalScroll(
                    Static("", id="home-exec-preview-static"),
                    id="home-exec-preview-container",
                ),
                # Vertical(
                #     Button.success("Close & Run", id="home-exec-button"),
                #     id="home-exec-preview-buttons",
                # ),
                id="home-exec-preview",
            )

        yield Footer()

    def action_close_and_run(self) -> None:
        self.app.exit()

    def action_about(self) -> None:
        self.app.push_screen(AboutDialog(self.command))

    async def on_mount(self, event: events.Mount) -> None:
        await self._refresh_command_form()

    async def _refresh_command_form(self, node: TreeNode[cappa.Command] | None = None):
        if node is None:
            try:
                command_tree = self.query_one(CommandTree)
                node = command_tree.cursor_node
            except NoMatches:
                return

        assert node
        self.selected_command = node.data
        assert self.selected_command

        self._update_command_description(node)
        self._update_execution_string_preview(self.selected_command, self.command_data)
        await self._update_form_body(node)

    @on(Tree.NodeHighlighted)
    async def selected_command_changed(
        self, event: Tree.NodeHighlighted[cappa.Command]
    ) -> None:
        await self._refresh_command_form(event.node)

    @on(CommandForm.Changed)
    def update_command_data(self, event: CommandForm.Changed) -> None:
        self.command_data = event.command_data
        self._update_execution_string_preview(self.selected_command, self.command_data)

    def _update_command_description(self, node: TreeNode[cappa.Command]) -> None:
        """Update the description of the command at the bottom of the sidebar
        based on the currently selected node in the command tree.
        """
        description_box = self.query_one("#home-command-description", Static)

        assert node.data
        description_text = node.data.help or ""
        description_text = description_text.lstrip()
        description_text = f"[b]{node.label if self.is_grouped_cli else self.command_name}[/]\n{description_text}"
        description_box.update(description_text)

    def _update_execution_string_preview(
        self, command: cappa.Command[T], command_data: T
    ) -> None:
        """Update the preview box showing the command string to be executed"""
        if self.command_data is not None:
            command_name_syntax_style = self.get_component_rich_style(
                "command-name-syntax"
            )
            prefix = Text(f"{self.command_name} ", command_name_syntax_style)
            new_value = command_data.to_cli_string(include_root_command=False)
            highlighted_new_value = Text.assemble(prefix, self.highlighter(new_value))
            prompt_style = self.get_component_rich_style("prompt")
            preview_string = Text.assemble(("$ ", prompt_style), highlighted_new_value)
            self.query_one("#home-exec-preview-static", Static).update(preview_string)

    async def _update_form_body(self, node: TreeNode[cappa.Command]) -> None:
        parent = self.query_one("#home-body-scroll", VerticalScroll)
        for child in parent.children:
            await child.remove()

        # Process the metadata for this command and mount corresponding widgets
        command = node.data
        assert command
        command_form = CommandForm(command=command)
        await parent.mount(command_form)
        if not self.is_grouped_cli:
            command_form.focus()
