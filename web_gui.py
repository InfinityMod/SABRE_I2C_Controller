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

class FileInput(flx.LineEdit):
    def _create_dom(self):
        global document, FileReader
    
        self.file = document.createElement('input')
        self.file.type = 'file'
        self.file.style = 'display: none'
        self.file.addEventListener('change', self._handle_file)

        node = super()._create_dom()
        node.appendChild(self.file)
        node.style = 'display: none'

        self.reader = FileReader()
        self.reader.onload = self.file_loaded
        return node

    def _handle_file(self):
        self.node.value = self.file.files[0].name
        self.file_selected()

    def select_file(self):
        self.file.click()

    def load(self):
        if self.file.files.length > 0:
            self.reader.readAsText(self.file.files[0])

    @flx.emitter
    def file_loaded(self, event):
        return { 'filedata': event.target.result }

    @flx.emitter
    def file_selected(self):
        return { 'filename': self.node.value }

class WebFrontend(flx.Widget):
    def init(self, py):
        self.py = py
        self.file_name = flx.StringProp('')
        self.file_input = FileInput()
        with flx.VBox():
            flx.Label(style="background:#cfc;", wrap=1, text="")
            with flx.HSplit(flex=1):
                with flx.VBox(style="border:1px solid #777;",):
                    flx.Label(text="Properties Tree")
                    self.tree = TreeWithControls(py, flex=1, max_selected=1)
                with flx.VBox(style="border:1px solid #777;"):
                    flx.Label(text="Property", style="")
                    with flx.VBox(flex=1):
                        with flx.VBox(flex=1, style=""):
                            self.combo = ui.ComboBox(editable=True, options=())
                            self.field = ui.LineEdit(placeholder_text="type here")
                            with flx.HBox(flex=1, style="max-height: 20px;"):
                                self.pick_file = ui.Button(text='...')
                                self.do_upload = ui.Button(text='Upload', disabled=True)
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
            self.update_btn = ui.Button(text="Apply", style="width: 100px;")

    @flx.reaction('file_input.file_selected')
    def handle_file_selected(self, *events):
        self.set_file_to_upload(events[-1]['filename'])
        
    @flx.reaction('file_input.file_loaded')
    def handle_file_loaded(self, *events):
        self.file_loaded(events[-1]['filedata'])

    @flx.reaction('pick_file.pointer_click')
    def on_pick_file(self, *events):
        self.file_input.select_file()

    @flx.reaction('do_upload.pointer_click')
    def on_do_upload(self, *events):
        self.file_input.load()

    @flx.action
    def set_file_to_upload(self, value):
        self.do_upload._mutate_disabled(value == '')
        # self._mutate_file_name(value)
        pass

    @flx.emitter
    def file_loaded(self, data):
        return {'filedata': data }

    #Others
    def field_visibility(self, status):
        if status == False:
            self.field.apply_style("display: none;")
        else:
            self.field.apply_style("display: inline-block;")

    def combo_visibility(self, status):
        if status == False:
            self.combo.apply_style("display:none;")
        else:
            self.combo.apply_style("display: inline-block;")

    @event.action
    def upload_visibility(self, status):
        if status == False:
            self.pick_file.apply_style("display: none;")
            self.do_upload.apply_style("display: none;")
        else:
            self.pick_file.apply_style("display: inline-block;")
            self.do_upload.apply_style("display: inline-block;")

    @event.action
    def update_combo(self, options, active_idx):
        if len(options) > 0:
            self.field_visibility(False)
            self.combo.set_options(options)
            self.combo.set_selected_index(active_idx)
            self.combo_visibility(True)
        else:
            self.combo_visibility(False)
            self.field.set_text(str(active_idx))
            self.field_visibility(True)

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
        self.fir_filter = "fir0"
    
    @flx.reaction('widget.file_loaded')
    def handle_file_upload(self, *events):
        filedata = events[-1]['filedata']
        data = [int(min(1.0, max(-1.0, float(f.replace("\r", ""))))/(1.0/2**24)) for f in filedata.split("\n") if len(f) > 0]
        m.fir_update(data, filter=self.fir_filter)

    @event.action
    def on_tree_select(self, data):
        select = (
            data[-1]["source"].parent.text.split(": ", 1)[1],
            data[-1]["source"].title,
        )
        register = self.mappers[0].get(select[0])
        mnemonic = register.get(select[1])
        self.currentSelect = select

        if self.currentSelect[1] == "prog_coeff_data":
            self.widget.upload_visibility(True)
            self.widget.update_info(mnemonic.description)
            self.widget.update_combo(["fir1", "fir2"], None)
            self.widget.update_raw(str(register))
        else:
            self.widget.upload_visibility(False)
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
                if mnemonic.name == "prog_coeff_data":
                    self.fir_filter = data[0]["key"]
                elif len(mnemonic.possible_values) > 0:
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
        # m.importYaml(
        #     r"C:\Users\webco\Documents\Projects\SABRE_I2C_Controller\configs\device_0x48_config_std.yml"
        # )
        # pass
    flx_app = flx.App(ControlApp, mappers, lock_settings)
    # app.launch("app", title="ES9038Control")  # to run as a desktop app
    app.create_server(host="", port=5000, backend="tornado")
    flx_app.launch("browser")  # to open in the browser
    flx.start()  # mainloop will exit when the
