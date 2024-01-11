import os
import shutil
import getpass
from textual.app import App
from textual.widgets import (
    DirectoryTree,
    # ScrollView,
    Button,
    Placeholder,
)


class FileCopierApp(App):
    async def on_mount(self):
        self.username = ""
        self.password = ""

        # Left panel: Navigator Menu
        self.navigator = DirectoryTree(directory=os.getcwd())
        self.navigator.on_select(self.handle_tree_select)
        # self.add_widget(ScrollView(self.navigator))

        # Implement your authentication logic (e.g., modal dialog or input fields)

        # Footer: Copy Button
        self.copy_button = Button(name="copy", label="Copy Selected")
        self.copy_button.disabled = True  # Disable until authenticated
        self.copy_button.on_click(self.copy_selected)
        self.add_footer(self.copy_button)

    async def handle_tree_select(self, path: str):
        self.selected_path = path

    async def authenticate(self, username, password):
        if self.validate_credentials(
            username, password
        ):  # Implement your validation logic
            self.copy_button.disabled = False
        else:
            await self.show_message("Invalid credentials")

    async def copy_selected(self):
        dest_path = "/path/to/destination"
        if os.path.isdir(self.selected_path):
            shutil.copytree(
                self.selected_path,
                f"{dest_path}/{os.path.basename(self.selected_path)}",
            )
        elif os.path.isfile(self.selected_path):
            shutil.copy2(self.selected_path, dest_path)

    async def on_load(self, event):
        await self.navigator.load()

    # Implement other helper methods like validate_credentials()


if __name__ == "__main__":
    FileCopierApp.run(title="File Copier")
