import os, sys

sys.path.append(os.path.dirname(__file__))

from controllers.ES9038Q2M import DAC_9038Q2M_Control
from flexx import app, event, ui, flx


class TreeWithControls(flx.TreeWidget):
    """Adds a key press handler to allow controlling the TreeWidget with
    the arrow keys, space, and enter.
    """

    def init(self, py):
        self.py = py

    @flx.emitter
    def key_down(self, e):
        """Overload key_down emitter to prevent browser scroll."""
        ev = self._create_key_event(e)
        if ev.key.startswith("Arrow"):
            e.preventDefault()
        return ev

    @flx.reaction("key_down")
    def _handle_highlighting(self, *events):
        for ev in events:
            if ev.modifiers:
                continue
            if ev.key == "Escape":
                self.highlight_hide()
            elif ev.key == " ":
                if self.max_selected == 0:  # space also checks if no selection
                    self.highlight_toggle_checked()
                else:
                    self.highlight_toggle_selected()
            elif ev.key == "Enter":
                self.highlight_toggle_checked()
            elif ev.key == "ArrowRight":
                item = self.highlight_get()
                if item and item.items:
                    item.collapsed = None
            elif ev.key == "ArrowLeft":
                item = self.highlight_get()
                if item and item.items:
                    item.collapsed = True
            elif ev.key == "ArrowDown":
                self.highlight_show(1)
            elif ev.key == "ArrowUp":
                self.highlight_show(-1)

    @flx.reaction("children**.checked", "children**.selected", "children**.collapsed")
    def on_event(self, *events):
        self.send_data(events)

    @event.action
    def send_data(self, data):
        self.py.on_tree_select(data)

    @event.action
    def clear(self):
        for c in self.get_all_items():
            c.dispose()


class WebFrontend(app.JsComponent):
    def init(self, py):
        self.py = py
        with flx.VBox():
            flx.Label(style="background:#cfc;", wrap=1, text="")
            with flx.HSplit(flex=1):
                with flx.VBox(
                    style="border:1px solid #777;",
                ):
                    flx.Label(text="Properties Tree")
                    self.tree = TreeWithControls(py, flex=1, max_selected=1)
                with flx.VBox(style="border:1px solid #777;"):
                    flx.Label(text="Property", style="")
                    with flx.VBox(flex=1):
                        with flx.VBox(flex=1, style=""):
                            self.combo = ui.ComboBox(editable=True, options=())
                            self.field = ui.LineEdit(placeholder_text="type here")
                        with flx.VBox(flex=5):
                            flx.Label(text="Info", style="")
                            self.info = flx.Label(
                                text="", style="white-space: pre-line;"
                            )
                    with flx.VBox(style="border:1px solid #777;", flex=1):
                        flx.Label(text="Raw", style="")
                        self.rawLabel = flx.Label(
                            text="", style="white-space: pre-line;"
                        )
            self.update_btn = ui.Button(text="Update", style="width: 100px;")

    @event.action
    def update_combo(self, options, active_idx):
        if len(options) > 0:
            self.field.apply_style("display:none;")
            self.combo.set_options(options)
            self.combo.set_selected_index(active_idx)
            self.combo.apply_style("display: inline-block;")
        else:
            self.combo.apply_style("display:none;")
            self.field.set_text(str(active_idx))
            self.field.apply_style("display: inline-block;")

    @event.action
    def update_raw(self, text):
        self.rawLabel.set_text(text)
        self.rawLabel.apply_style("white-space: pre-line;")

    @event.action
    def tree_recursive(self, top, e):
        with top:
            if isinstance(e, dict):
                for n, v in e.items():
                    with flx.TreeItem(text=n) as top2:
                        self.tree_recursive(top2, v)
            elif isinstance(e, list):
                for e0 in e:
                    flx.TreeItem(title=str(e0), css_class="selectItem")
            else:
                flx.TreeItem(title=str(e), css_class="selectItem")

    @event.action
    def update_tree(self, treeDict):
        self.tree.clear()
        self.tree_recursive(self.tree, treeDict)

    @event.action
    def update_info(self, text):
        self.info.set_text(text)
        self.info.apply_style("white-space: pre-line;")

    @flx.reaction("combo.user_selected")
    def update_selected_index(self, *events):
        self.py.on_dropdown_change(events)

    @flx.reaction("field.user_text")
    def update_field(self, *events):
        self.py.on_dropdown_change(events)

    @flx.reaction("update_btn.pointer_click")
    def update_btn_clicked(self, *events):
        self.py.update_i2c()


class ControlApp(app.PyComponent):
    def init(self, mappers, locked):
        self.mappers = mappers
        self.locked = locked
        self.widget = WebFrontend(self)
        self.autoupdate = False

        self.widget.update_tree(
            {
                "{0}: {1}".format(
                    ", ".join(map(str, self.mappers[0].get(r).registers)), r
                ): self.mappers[0]
                .get(r)
                .mnemonicNames
                for r in self.mappers[0].registerNames
            }
        )
        self.currentSelect = None

    @event.action
    def on_tree_select(self, data):
        select = (
            data[-1]["source"].parent.text.split(": ", 1)[1],
            data[-1]["source"].title,
        )
        register = self.mappers[0].get(select[0])
        mnemonic = register.get(select[1])
        self.currentSelect = select

        self.widget.update_combo(
            mnemonic.possible_values,
            mnemonic.possible_values.index(mnemonic.value)
            if len(mnemonic.possible_values) > 0
            else mnemonic.value,
        )
        self.widget.update_info(mnemonic.description)
        self.widget.update_raw(str(register))

    @event.action
    def on_dropdown_change(self, data):
        for m in self.mappers:
            if self.currentSelect not in self.locked and (
                (self.currentSelect[0], "*") not in self.locked
            ):
                mnemonic = m.get(self.currentSelect[0]).get(self.currentSelect[1])
                if len(mnemonic.possible_values) > 0:
                    setattr(
                        m.get(self.currentSelect[0]),
                        self.currentSelect[1],
                        data[0]["key"],
                    )
                elif isinstance(mnemonic.value, float):
                    setattr(
                        m.get(self.currentSelect[0]),
                        self.currentSelect[1],
                        float(data[0]["new_value"]),
                    )
                elif isinstance(mnemonic.value, int):
                    setattr(
                        m.get(self.currentSelect[0]),
                        self.currentSelect[1],
                        int(data[0]["new_value"]),
                    )

    @event.action
    def update_i2c(self):
        for m in self.mappers:
            m.i2c_update()


if __name__ == "__main__":
    lock_settings = [("Mixing, Serial Data and Automute Configuration", "*")]
    mappers = [DAC_9038Q2M_Control(0x48), DAC_9038Q2M_Control(0x49)]
    for m in mappers:
        m.i2c_init()
        # m.data_init(
        #     r"/env/nfs/dataServer/Private_Data/Projects/Hobbies/HIFI-Zuhause/DAC/Tuning/SABER_Controller/save.p"
        # )
    flx_app = flx.App(ControlApp, mappers, lock_settings)
    # app.launch("app", title="ES9038Control")  # to run as a desktop app
    app.create_server(host="", port=5000, backend="tornado")
    flx_app.launch("browser")  # to open in the browser
    flx.run()  # mainloop will exit when the