import gtk
import re
import os
import sys
from datetime import datetime
from taskpaperconfig import get_data_path

Project, Task, Note = 0, 1, 2

class Taskpaper:
    def __init__(self):
        # These regexes determine what type of content is being input.
        self.project = re.compile("\s*(?!-)(.*?):")
        self.task = re.compile("^\s*-\s+(.*)")
        self.tag  = re.compile("(@(\w+)(?:\((.*?)\))?)")

        self.current_file = self.open_most_recent_file()
        self.changed      = False   # Have tasks been changed?
        self.user_action  = False
        ui_filename = os.path.join(get_data_path(), "ui", "Taskpaper.ui")
        self.builder      = gtk.Builder()
        self.builder.add_from_file(ui_filename)
        self.window       = self.builder.get_object("taskpaper")
        self.task_view    = self.builder.get_object("taskView")
        self.builder.connect_signals(self, None)
        self.window.show_all()
        self.previous_entity = None # Last parsed entity type
        self.create_formatting_tags(self.task_view.get_buffer())
        self.undo = []
        self.redo = []
        #self.indenting = {}

    def open_most_recent_file(self):
        """
        Opens file last worked on. If nothing was being done (what a shame,
        considering), returns None.
        """
        pass

    def on_clear_search_box(self, *args):
        self.builder.get_object("search").set_text("")
        
    def create_formatting_tags(self, buffer):
        buffer.create_tag("project", font="Sans Bold 14", foreground="black")
        buffer.create_tag("task", foreground="black")
        buffer.create_tag("note", foreground="grey"),
        buffer.create_tag("done", font="Sans Italic", foreground="darkgrey",
                          strikethrough="true"),
        buffer.create_tag("tag", font="Sans Italic 10", foreground="darkgrey")

    def quit(self, *args):
        gtk.main_quit()

    def on_taskView_key_press_event(self, textview, event):
        key_name = gtk.gdk.keyval_name(event.keyval)
        if key_name == "Tab":
            return True

        return False

    def add_tag_to_entry(self, text):
        buffer = self.task_view.get_buffer()
        iter = buffer.get_iter_at_mark(buffer.get_insert())
        iter.forward_to_line_end()
        buffer.insert(iter, " " + text)

    def on_insert_date(self, *w):
        self.add_tag_to_entry("@date(%s)" %
                              (datetime.now().strftime("%Y-%m-%d"), ))
        
    def on_tagToday_activate(self, *w):
        self.add_tag_to_entry("@today")
        
    def on_tagDone_activate(self, *w):
        self.add_tag_to_entry("@done")

    def insert_text(self, buffer, iter, text, length):
        if self.user_action:
            self.undo.append(("insert_text", iter.get_offset(),
                              iter.get_offset() +
                                len(re.findall(".", text)), text))
            self.redo = []

        self.set_changed(True)
        
    def delete_text(self, buffer, start, end):
        if self.user_action:
            text = buffer.get_text(start, end)
            self.undo.append(("delete_range", start.get_offset(),
                              end.get_offset(), text))
        self.set_changed(True)

    def on_copy_text(self, *w):
        self.task_view.get_buffer().copy_clipboard(gtk.clipboard_get())

    def on_cut_text(self, *w):
        self.task_view.get_buffer().cut_clipboard(gtk.clipboard_get(),
                                  self.task_view.get_editable())

    def on_paste_text(self, *w):
        clipboard = gtk.clipboard_get()
        clipboard.request_text(self.format_text_from_clipboard)

    def format_text_from_clipboard(self, clipboard, text, data):
        buffer = self.task_view.get_buffer()
        buffer.insert_at_cursor(text)

    def on_taskView_insert_at_cursor(self, *w):
        print w
        
    def begin_user_action(self, *w):
        self.user_action = True

    def end_user_action(self, *w):
        self.user_action = False

    def undo(self, w):
        if len(self.undo) == 0:
            return
        
        action = self.undo.pop()
        buffer = self.task_view.get_buffer()
        start_iter = None
        
        if action[0] == "insert_text":
            start_iter = buffer.get_iter_at_offset(action[1])
            end_iter   = buffer.get_iter_at_offset(action[2])
            buffer.delete(start_iter, end_iter)
        elif action[0] == "delete_range":
            start_iter = buffer.get_iter_at_offset(action[1])
            buffer.insert(start_iter, action[3])
            
        self.iter_on_screen(start_iter, "insert")
        self.redo.append(action)

    def redo(self, w):
        if len(self.redo) == 0:
            return

        action = self.redo.pop()
        buffer = self.task_view.get_buffer()
        start_iter = None
        
        if action[0] == "insert_text":
            start_iter = buffer.get_iter_at_offset(action[1])
            end_iter = buffer.get_iter_at_offset(action[2])
            buffer.insert(start_iter, action[3])
        elif action[0] == "delete_range":
            start_iter = buffer.get_iter_at_offset(action[1])
            end_iter = buffer.get_iter_at_offset(action[2])
            buffer.delete(start_iter, end_iter)
        self.iter_on_screen(start_iter, "insert")
        self.undo.append(action)

    def iter_on_screen(self, iter, mark_str):
        buffer = self.task_view.get_buffer()
        self.task_view.scroll_mark_onscreen(buffer.get_mark(mark_str))
    
    def on_taskView_key_release_event(self, textview, event):
        buffer = textview.get_buffer()
        curr   = buffer.get_iter_at_mark(buffer.get_insert())
        key_name = gtk.gdk.keyval_name(event.keyval)

        if key_name in ("Return", "KP_Enter"):
            if self.previous_entity in (Project, Task):
                buffer.insert_at_cursor("- ")
        elif not key_name in ("Down", "Up", "Left", "Right"):
            self.apply_formatting(buffer, curr)
        return False

    def apply_formatting(self, buffer, iter):
        line_number = iter.get_line()
        start = buffer.get_iter_at_line(iter.get_line())
        end   = buffer.get_iter_at_line(iter.get_line())
        end.forward_to_line_end()
        buffer.remove_all_tags(start, end)
        text  = buffer.get_slice(start, end)

        if self.is_project(text):
            self.previous_entity = Project
            buffer.apply_tag_by_name("project", start, end)
        else:
            if self.is_task(text):
                self.previous_entity = Task
                buffer.apply_tag_by_name("task", start, end)
            else:
                self.previous_entity = Note
                buffer.apply_tag_by_name("note", start, end)
        if self.is_entry_done(text):
            done_end = buffer.get_iter_at_line(start.get_line())
            while done_end.get_char() != "@": done_end.forward_char()
            done_end.backward_char() # unnecessary, TODO: make it decent
            buffer.apply_tag_by_name("done", start, done_end)

    def is_project(self, text):
        return self.project.match(text) != None
        
    def is_task(self, text):
        return self.task.match(text) != None

    def is_entry_done(self, text):
        return "done" in self.find_tags(text)

    def find_tags(self, text):
        return [tag for _, tag, annotations in self.tag.findall(text)]

    def load_tasks_file(self, filename):
        tasks = open(filename).read()
        buffer = self.task_view.get_buffer()
        buffer.set_text(tasks)
        for line in range(buffer.get_line_count()):
            iter = buffer.get_iter_at_line(line)
            self.apply_formatting(buffer, iter)
        self.current_file = filename
        self.set_changed(False)
        
    def set_changed(self, changed=False):
        filename = None
        if self.current_file:
            filename = os.path.split(self.current_file)[-1]
        else:
            filename = "Untitled"
            
        if changed:
            self.window.set_title("* %s" % (filename, ))
        else:
            self.window.set_title("%s" % (filename, ))
        self.changed = changed

    def on_archive_done_tasks(self, w):
        buffer = self.task_view.get_buffer()
        iter   = buffer.get_start_iter()
        removed = []
        
        while not iter.is_end():
            line_end = buffer.get_iter_at_line(iter.get_line())
            line_end.forward_to_line_end()
            text = buffer.get_slice(iter, line_end)
            if self.is_task(text) and self.is_task_done(text):
                project = self.find_closest_project(buffer, iter)
                removed.append((project, text))
                line = iter.get_line() 
                buffer.delete(iter, line_end)
                iter = buffer.get_iter_at_line(line - 1)
            iter.forward_line()

        archive_iter = self.get_archive_insertion_point()
        
        for project, task in removed:
            text = task
            if project: text = "%s @project(%s)" % (text, project, )
            buffer.insert(archive_iter, text)
        
    def mark_as_done(self, task):
        # TODO: update view
        pass

    def get_archive_insertion_point(self):
        return self.task_view.get_buffer().get_end_iter()

    def find_closest_project(self, buffer, iter):
        while not iter.is_start():
            iter.backward_line()
            line_end = buffer.get_iter_at_line(iter.get_line())
            line_end.forward_to_line_end()
            text = buffer.get_slice(iter, line_end)
            if self.is_project(text):
                project = self.project.match(text).groups()[0]
                return project
        return None

    def on_open_tasks(self, *item):
        if self.changed:
            pass #
        else:
            pass
        self.builder.get_object("openFile").show_all()

    def on_save_tasks(self, *item):
        if self.current_file:
            self.save_tasks_file(self.current_file)
        else:
            dialog = self.builder.get_object("saveFile")
            dialog.show_all()

    def save_tasks_file(self, filename):
        buffer = self.task_view.get_buffer()
        text = buffer.get_text(buffer.get_start_iter(),
                               buffer.get_end_iter())
        file = open(filename, "w")
        file.write(text)
        file.close()
        self.current_file = filename
        self.set_changed(False)
        
    def on_save_as_new_tasks(self, *item):
        print item

    def cancel_dialog(self, dialog):
        dialog.hide()

    def perform_dialog_action(self, dialog):
        buffer = self.task_view.get_buffer()
        dlg_name = dialog.get_name()
        if dlg_name == "saveFile":
            self.save_tasks_file(dialog.get_filename())
        elif dlg_name == "openFile":
            self.load_tasks_file(dialog.get_filename())
        dialog.hide()

if __name__ == "__main__":
    tp = Taskpaper()
    if len(sys.argv) > 1: tp.load_tasks_file(sys.argv[1])
    gtk.main()
