from __future__ import annotations

import cappa
from rich.style import Style
from rich.text import Text, TextType
from textual.widgets import Tree
from textual.widgets._tree import TreeDataType, TreeNode


class CommandTree(Tree[cappa.Command]):
    COMPONENT_CLASSES = {"group"}

    def __init__(
        self,
        label: TextType,
        command: cappa.Command,
        command_name: str,
    ):
        super().__init__(label)
        self.show_root = False
        self.guide_depth = 2
        self.show_guides = False
        self.command = command
        self.command_name = command_name

    def render_label(
        self, node: TreeNode[TreeDataType], base_style: Style, style: Style
    ) -> Text:
        label = node._label.copy()
        label.stylize(style)
        return label

    def on_mount(self):
        def build_tree(command: cappa.Command, node: TreeNode) -> TreeNode:
            node.add_leaf(command.real_name(), data=command)
            # subcommand = command.subcommand
            # for arg in command.arguments:
            #     if arg is subcommand:
            #         continue
            #
            #     node.add_leaf(arg.field_name, data=arg)

            # if subcommand:
            #     label = Text(subcommand.field_name)
            #
            #     group_style = self.get_component_rich_style("group")
            #     label.stylize(group_style)
            #     label.append(" ")
            #     label.append("group", "dim i")
            #
            #     for subcommand in subcommand.options.values():
            #         child = node.add(label, allow_expand=False, data=subcommand)
            #         build_tree(subcommand, child)
            return node

        build_tree(self.command, self.root)
        self.root.expand_all()
        self.select_node(self.root)
