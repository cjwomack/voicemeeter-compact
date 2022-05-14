import tkinter as tk
from tkinter import ttk, messagebox
from functools import partial
import webbrowser
import sv_ttk
import vbancmd

from .data import (
    get_configuration,
    _base_values,
    _configuration,
    kind_get,
)


class Menus(tk.Menu):
    def __init__(self, parent, vmr):
        super().__init__()
        self.parent = parent
        self.vmr = vmr
        self.vban_config = get_configuration("vban")
        self.app_config = get_configuration("app")
        self._is_topmost = tk.BooleanVar()
        self._lock = tk.BooleanVar()
        self._unlock = tk.BooleanVar()
        self._selected_bus = list(tk.BooleanVar() for _ in range(8))

        # voicemeeter menu
        self.menu_voicemeeter = tk.Menu(self, tearoff=0)
        self.add_cascade(menu=self.menu_voicemeeter, label="Voicemeeter")
        self.menu_voicemeeter.add_checkbutton(
            label="Always On Top",
            onvalue=1,
            offvalue=0,
            variable=self._is_topmost,
            command=self.always_on_top,
        )
        self.menu_voicemeeter.add_separator()
        self.menu_voicemeeter.add_command(
            label="Show",
            underline=0,
            command=partial(self.action_invoke_voicemeeter, "show"),
        )
        self.menu_voicemeeter.add_command(
            label="Hide",
            underline=0,
            command=partial(self.action_invoke_voicemeeter, "hide"),
        )
        self.menu_voicemeeter.add_command(
            label="Restart",
            underline=0,
            command=partial(self.action_invoke_voicemeeter, "restart"),
        )
        self.menu_voicemeeter.add_command(
            label="Shutdown",
            underline=0,
            command=partial(self.action_invoke_voicemeeter, "shutdown"),
        )
        self.menu_voicemeeter.add_separator()
        self.menu_lock = tk.Menu(self.menu_voicemeeter, tearoff=0)
        self.menu_voicemeeter.add_cascade(
            menu=self.menu_lock, label="GUI Lock", underline=0
        )
        self.menu_lock.add_checkbutton(
            label="Lock",
            onvalue=1,
            offvalue=0,
            variable=self._lock,
            command=partial(self.action_set_voicemeeter, "lock"),
        )
        self.menu_lock.add_checkbutton(
            label="Unlock",
            onvalue=1,
            offvalue=0,
            variable=self._unlock,
            command=partial(self.action_set_voicemeeter, "lock", False),
        )

        # profiles menu
        menu_profiles = tk.Menu(self, tearoff=0)
        self.add_cascade(menu=menu_profiles, label="Profiles")
        self.menu_profiles_load = tk.Menu(menu_profiles, tearoff=0)
        menu_profiles.add_cascade(menu=self.menu_profiles_load, label="Load profile")
        defaults = {"base", "blank"}
        if len(self.target.profiles) > len(defaults) and all(
            key in self.target.profiles for key in defaults
        ):
            [
                self.menu_profiles_load.add_command(
                    label=profile, command=partial(self.load_profile, profile)
                )
                for profile in self.target.profiles.keys()
                if profile not in defaults
            ]
        else:
            menu_profiles.entryconfig(0, state="disabled")
        menu_profiles.add_command(label="Reset to defaults", command=self.load_defaults)

        # layout menu
        self.menu_layout = tk.Menu(self, tearoff=0)
        self.add_cascade(menu=self.menu_layout, label="Layout")
        # layout/submixes
        # here we build menu regardless of kind but disable if not Potato
        buses = tuple(f"A{i+1}" for i in range(5)) + tuple(f"B{i+1}" for i in range(3))
        self.menu_submixes = tk.Menu(self.menu_layout, tearoff=0)
        self.menu_layout.add_cascade(menu=self.menu_submixes, label="Submixes")
        [
            self.menu_submixes.add_checkbutton(
                label=f"Bus {buses[i]}",
                underline=0,
                onvalue=1,
                offvalue=0,
                variable=self._selected_bus[i],
                command=partial(self.set_submix, i),
            )
            for i in range(8)
        ]
        self._selected_bus[_base_values.submixes].set(True)
        if self.parent.kind.name != "Potato":
            self.menu_layout.entryconfig(0, state="disabled")
        # layout/extends
        self.menu_extends = tk.Menu(self.menu_layout, tearoff=0)
        self.menu_layout.add_cascade(
            menu=self.menu_extends, label="Extends", underline=0
        )
        self.menu_extends.add_command(
            label="horizontal",
            underline=0,
            command=partial(self.switch_orientation, extends_horizontal=True),
        )
        self.menu_extends.add_command(
            label="vertical",
            underline=0,
            command=partial(self.switch_orientation, extends_horizontal=False),
        )
        self.menu_extends.entryconfig(
            0 if _configuration.extends_horizontal else 1, state="disabled"
        )
        # layout/themes
        self.menu_themes = tk.Menu(self.menu_layout, tearoff=0)
        self.menu_layout.add_cascade(menu=self.menu_themes, label="Themes")
        self.menu_themes.add_command(
            label="light", command=partial(self.load_theme, "light")
        )
        self.menu_themes.add_command(
            label="dark", command=partial(self.load_theme, "dark")
        )
        self.menu_themes.entryconfig(
            0 if self.app_config["theme"]["mode"] == "light" else 1,
            state="disabled",
        )
        if not _configuration.themes_enabled:
            self.menu_layout.entryconfig(2, state="disabled")

        # vban connect menu
        self.menu_vban = tk.Menu(self, tearoff=0)
        self.add_cascade(menu=self.menu_vban, label="VBAN")
        if self.vban_config:
            for i, _ in enumerate(self.vban_config):
                setattr(self, f"menu_vban_{i+1}", tk.Menu(self.menu_vban, tearoff=0))
                target_menu = getattr(self, f"menu_vban_{i+1}")
                self.menu_vban.add_cascade(
                    menu=target_menu,
                    label=f"{self.vban_config[f'connection-{i+1}']['streamname']}",
                    underline=0,
                )
                target_menu.add_command(
                    label="Connect", command=partial(self.vban_connect, i)
                )
                target_menu.add_command(
                    label="Disconnect", command=partial(self.vban_disconnect, i)
                )
                target_menu.entryconfig(1, state="disabled")
        else:
            self.entryconfig(4, state="disabled")

        # Help menu
        self.menu_help = tk.Menu(self, tearoff=0)
        self.add_cascade(menu=self.menu_help, label="Help")
        self.menu_help.add_command(
            label="Voicemeeter Site",
            command=self.documentation,
        )
        self.menu_help.add_command(
            label="Source Code",
            command=self.github,
        )
        self.menu_help.add_command(
            label="App Creator",
            command=self.onyxandiris,
        )

    @property
    def target(self):
        """use the correct interface"""
        return self.parent.target

    def enable_vban_menus(self):
        [
            self.menu_vban.entryconfig(j, state="normal")
            for j, _ in enumerate(self.menu_vban.winfo_children())
        ]

    def action_invoke_voicemeeter(self, cmd):
        getattr(self.target.command, cmd)()

    def action_set_voicemeeter(self, cmd, val=True):
        if cmd == "lock":
            self._lock.set(val)
            self._unlock.set(not self._lock.get())
        setattr(self.target.command, cmd, val)

    def load_profile(self, profile):
        self.target.apply_profile(profile)

    def load_defaults(self):
        resp = messagebox.askyesno(
            message="Are you sure you want to Reset values to defaults?\nPhysical strips B1, Virtual strips A1\nMono, Solo, Mute, EQ all OFF"
        )
        if resp:
            self.target.apply_profile("base")

    def always_on_top(self):
        self.parent.attributes("-topmost", self._is_topmost.get())

    def switch_orientation(self, extends_horizontal: bool = True, *args):
        _configuration.extends_horizontal = extends_horizontal
        if extends_horizontal:
            self.menu_extends.entryconfig(0, state="disabled")
            self.menu_extends.entryconfig(1, state="normal")
        else:
            self.menu_extends.entryconfig(1, state="disabled")
            self.menu_extends.entryconfig(0, state="normal")

    def set_submix(self, i):
        if _base_values.submixes != i:
            _base_values.submixes = i
            if self.parent.submix_frame is not None:
                self.parent.submix_frame.teardown()
                self.parent.nav_frame.show_submix()
            for j, var in enumerate(self._selected_bus):
                var.set(i == j)

    def load_theme(self, theme):
        sv_ttk.set_theme(theme)
        _configuration.theme_mode = theme
        self.menu_themes.entryconfig(
            0,
            state=f"{'disabled' if theme == 'light' else 'normal'}",
        )
        self.menu_themes.entryconfig(
            1,
            state=f"{'disabled' if theme == 'dark' else 'normal'}",
        )
        [
            menu.config(bg=f"{'black' if theme == 'dark' else 'white'}")
            for menu in self.winfo_children()
            if isinstance(menu, tk.Menu)
        ]
        self.menu_lock.config(bg=f"{'black' if theme == 'dark' else 'white'}")
        self.menu_profiles_load.config(bg=f"{'black' if theme == 'dark' else 'white'}")
        [
            menu.config(bg=f"{'black' if theme == 'dark' else 'white'}")
            for menu in self.menu_vban.winfo_children()
            if isinstance(menu, tk.Menu)
        ]
        [
            menu.config(bg=f"{'black' if theme == 'dark' else 'white'}")
            for menu in self.menu_layout.winfo_children()
            if isinstance(menu, tk.Menu)
        ]

    def vban_connect(self, i):
        [
            self.menu_vban.entryconfig(j, state="disabled")
            for j, _ in enumerate(self.menu_vban.winfo_children())
            if j != i
        ]

        opts = {}
        opts |= self.vban_config[f"connection-{i+1}"]
        kind_id = opts.pop("kind")
        self.vban = vbancmd.connect(kind_id, **opts)
        # login to vban interface
        self.vban.login()
        # destroy the current App frames
        self.parent._destroy_top_level_frames()
        _base_values.vban_connected = True
        self.vmr.end_thread()
        # build new app frames according to a kind
        kind = kind_get(kind_id)
        self.parent.build_app(kind, self.vban)
        target_menu = getattr(self, f"menu_vban_{i+1}")
        target_menu.entryconfig(0, state="disabled")
        target_menu.entryconfig(1, state="normal")
        self.menu_layout.entryconfig(
            0, state=f"{'normal' if kind.name == 'Potato' else 'disabled'}"
        )

    def vban_disconnect(self, i):
        # destroy the current App frames
        self.parent._destroy_top_level_frames()
        _base_values.vban_connected = False
        # logout of vban interface
        self.vmr.init_thread()
        self.vban.logout()
        # build new app frames according to a kind
        kind = kind_get(self.vmr.type)
        self.parent.build_app(kind, None)
        target_menu = getattr(self, f"menu_vban_{i+1}")
        target_menu.entryconfig(0, state="normal")
        target_menu.entryconfig(1, state="disabled")
        self.menu_layout.entryconfig(
            0, state=f"{'normal' if kind.name == 'Potato' else 'disabled'}"
        )

        self.after(15000, self.enable_vban_menus)

    def documentation(self):
        webbrowser.open_new(r"https://voicemeeter.com/")

    def github(self):
        webbrowser.open_new(r"https://github.com/onyx-and-iris/voicemeeter-compact")

    def onyxandiris(self):
        webbrowser.open_new(r"https://onyxandiris.online")
