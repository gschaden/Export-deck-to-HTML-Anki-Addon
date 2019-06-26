from aqt import mw, utils, browser
from aqt.qt import *
from aqt import editor
from anki import notes
from anki.utils import intTime, ids2str, isWin
import platform
import sys
from os.path import expanduser, join
import os
from pickle import load, dump

template_before="""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
        {{main_style}}
        </style>
    </head>
    <body>
    <div class="tex">
"""

template_after = """
</div>
</body>
</html>
"""

delimiter = "####"

class AddonDialog(QDialog):

    """Main Options dialog"""
    def __init__(self):
        QDialog.__init__(self, parent=mw)
        if os.path.exists('deck_field_dict'):
            try:
                self.map = load(open('deck_field_dict', 'rb'))
            except:
                self.map = {}
        else:
            self.map = {}
        self.path = None
        self.deck = None
        self.fields = {}
        self._setup_ui()


    def _handle_button(self):
        dialog = OpenFileDialog()
        self.path = dialog.filename
        if self.path is not None:
            utils.showInfo("Choose file successful.")


    def _setup_ui(self):
        """Set up widgets and layouts"""
        deck_label = QLabel("Choose deck")
        self.labels = []

        self.deck_selection = QComboBox()
        deck_names = sorted(mw.col.decks.allNames())
        current_deck = mw.col.decks.current()['name']
        deck_names.insert(0, current_deck)
        for i in range(len(deck_names)):
            if deck_names[i] == 'Default':
                deck_names.pop(i)
                break
        self.deck_selection.addItems(deck_names)
        self.deck_selection.currentIndexChanged.connect(self._select_deck)

        self.deck = self.deck_selection.currentText()
        self.field_selections = []
        self._add_field_selection(self.deck)

        self.add_field_button = QPushButton('+')
        self.add_field_button.clicked.connect(self._add_field)
        self.remove_field_button = QPushButton('-')
        self.remove_field_button.clicked.connect(self._remove_field)

        self.grid = QGridLayout()
        self.grid.setSpacing(10)
        self.grid.addWidget(deck_label, 1, 0)
        self.grid.addWidget(self.deck_selection, 1, 1)
        self.grid.addWidget(self.add_field_button, 1, 2)
        self.grid.addWidget(self.remove_field_button, 1, 3)

        self.textbox_label = QLabel('Attached css')
        self.textbox = QTextEdit(self)
        self.textbox.resize(380,60)

        self._layout()

        # Main button box
        button_box = QDialogButtonBox(QDialogButtonBox.Ok
                        | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self._on_reject)

        # Main layout
        l_main = QVBoxLayout()
        l_main.addLayout(self.grid)
        l_main.addWidget(button_box)
        self.setLayout(l_main)
        self.setMinimumWidth(360)
        self.setWindowTitle('Find words and create deck')


    def _layout(self):
        for i, (l, f) in enumerate(zip(self.labels, self.field_selections)):
            self.grid.addWidget(l, 2 + i, 0)
            self.grid.addWidget(f, 2 + i, 1)

        field_cnt = len(self.labels)
        self.grid.addWidget(self.textbox_label, 2 + field_cnt, 0)
        self.grid.addWidget(self.textbox, 2 + field_cnt, 1)


    def _add_field_selection(self, deck):
        if deck in self.map:
            for i, field in enumerate(self.map[deck]):
                self.labels.append(QLabel("Field %d" % (i + 1)))
                field_selection = QComboBox()
                fields = self._select_fields()
                fields.insert(0, field)
                field_selection.addItems(fields)
                self.field_selections.append(field_selection)
        else:
            self.labels.append(QLabel("Field 1"))
            field_selection = QComboBox()
            fields = self._select_fields()
            field_selection.addItems(fields)
            self.field_selections.append(field_selection)


    def _select_fields(self):
        query = 'deck:"{}"'.format(self.deck)
        try:
            card_id = mw.col.findCards(query=query)[0]
        except:
            utils.showInfo("This deck has no cards.")
            return []

        card = mw.col.getCard(card_id)

        note = card.note()
        model = note.model()
        fields = card.note().keys()
        return fields
    

    def _add_field(self):
        field_cnt = len(self.labels)
        field_label = QLabel("Field %d " % (field_cnt))
        field_selection = QComboBox()
        field_selection.addItems(self._select_fields())
        self.grid.addWidget(field_label, field_cnt + 2, 0)
        self.grid.addWidget(field_selection, field_cnt + 2, 1)

        self.grid.removeWidget(self.textbox_label)
        self.grid.removeWidget(self.textbox)

        self.grid.addWidget(self.textbox_label, field_cnt + 3, 0)
        self.grid.addWidget(self.textbox, field_cnt + 3, 1)
        self.field_selections.append(field_selection)
        self.labels.append(field_label)
    

    def _remove_field(self):
        if len(self.labels) <= 1 or len(self.field_selections) <= 1:
            return
        field_label = self.labels.pop()
        field_selection = self.field_selections.pop()
        field_cnt = len(self.labels)
        self.grid.removeWidget(field_label)
        self.grid.removeWidget(field_selection)
        self.grid.removeWidget(self.textbox_label)
        self.grid.removeWidget(self.textbox)
        self.grid.addWidget(self.textbox_label, field_cnt + 2, 0)
        self.grid.addWidget(self.textbox, field_cnt + 2, 1)
        field_label.deleteLater()
        field_selection.deleteLater()


    def _select_deck(self):
        self.deck = self.deck_selection.currentText()
        fields = self._select_fields()
        if len(fields) == 0:
            return
        for label, field in zip(self.labels, self.field_selections):
            self.grid.removeWidget(label)
            self.grid.removeWidget(field)
            label.deleteLater()
            field.deleteLater()
        self.grid.removeWidget(self.textbox_label)
        self.grid.removeWidget(self.textbox)
        self.labels = []
        self.field_selections = []
        self._add_field_selection(self.deck_selection.currentText())
        self._layout()


    def _on_accept(self):
        def convert_to_multiple_choices(value):
            choices = value.split("|")
            letters = "ABCDEFGHIKLMNOP"
            value = "<div>"
            for letter, choice in zip(letters, choices):
                value += '<div>' + "<span><strong>(" + letter + ")&nbsp</strong></span>" + choice.strip() + '</div>'
            return value + "</div>"

        dialog = SaveFileDialog(self.deck)
        path = dialog.filename
        if path == None:
            return
        css_text = str(self.textbox.toPlainText())
        split = css_text.find(delimiter)
        selected_fields = []
        if split != -1:
            selected_fields = css_text[:split].split("\n")
            selected_fields.remove('')
        if len(selected_fields) == 0:
            for field_selection in self.field_selections:
                selected_fields.append(field_selection.currentText())

        ## dump file to save selected fields
        self.map[self.deck] = selected_fields
        dump_file = open('deck_field_dict', 'wb')
        dump(self.map, dump_file)

        css_text = css_text[split+len(delimiter):]
        deck = self.deck_selection.currentText()
        query = 'deck:"{}"'.format(deck)
        cids = mw.col.findCards(query=query)
        if sys.version_info[0] >= 3:
            path = path[0]
        try:
            with open(path, "w") as f:
                edited_template = ""
                for i, cid in enumerate(cids):
                    card = mw.col.getCard(cid)
                    edited_template += """
                        <div><strong>{{id}}</strong></div>
                    """
                    edited_template = edited_template.replace("{{id}}", str(i+1))
                    for fi, field in enumerate(selected_fields):
                        value = card.note()[field]
                        if "|" in value:
                            value = convert_to_multiple_choices(value)
                        if field == "Sentence" and value != "":
                            value += "<br>"
                        edited_template += """
                            <div class="field{{id}}">{{field}}</div>
                        """
                        edited_template = edited_template.replace("{{field}}", value).replace("{{id}}", str(fi + 1))
                    edited_template += '-----------------------------------<br>'
                    #utils.showInfo(str(cid))
                f.write(str(template_before.replace("{{main_style}}", css_text) + edited_template + template_after))
                utils.showInfo("Export to HTML successfully")
        except IOError:
            utils.showInfo("Filename cannot special characters.")


    def _on_reject(self):
        self.close()


class SaveFileDialog(QDialog):

    def __init__(self, filename):
        QDialog.__init__(self, mw)
        self.title='Save File'
        self.left = 10
        self.top = 10
        self.width = 640
        self.height = 480
        self.filename = None
        self.default_filename = filename
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.filename = self._get_file()

    def _get_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        default_filename = self.default_filename.replace('::', '_')
        directory = os.path.join(expanduser("~/Desktop"), default_filename + ".html")
        try:
            path = QFileDialog.getSaveFileName(self, "Save File", directory, "All Files (*)", options=options)
            if path:
                return path
            else:
                utils.showInfo("Cannot open this file.")
        except:
            utils.showInfo("Cannot open this file.")
        return None


def display_dialog():
    dialog = AddonDialog()
    dialog.exec_()
    
action = QAction("Export deck to html", mw)
action.setShortcut("Ctrl+M")
action.triggered.connect(display_dialog)
mw.form.menuTools.addAction(action)