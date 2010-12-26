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
        self.project = re.compile("\s*(?!-)(.*?):\s*$")
        self.task = re.compile("^\s*-\s+(.*)")
        self.tag  = re.compile("(@(\w+)(?:\((.*?)\))?)")
        self.changed      = False   # Have tasks been changed?
        self.user_action  = False
        ui_filename = os.path.join(get_data_path(), "ui", "Taskpaper.ui")
        self.builder      = gtk.Builder()
        self.builder.add_from_file(ui_filename)
        self.window       = self.builder.get_object("taskpaper")
        self.task_view    = self.builder.get_object("taskView")
        self.create_formatting_tags(self.get_current_buffer())
        self.current_file = self.open_most_recent_file()
        self.builder.connect_signals(self, None)
        self.window.show_all()
        self.previous_entity = None # Last parsed entity type
        self.undo = []
        self.redo = []

    def open_most_recent_file(self):
        """
        Opens file last worked on. If nothing was being done (what a shame,
        considering), returns None.
        """
        try:
            prefs = os.path.join(os.path.expanduser("~"), ".taskpaper")
            filename = None
            with open(prefs) as last:
                filename = last.read().strip()
                self.load_tasks_file(filename)
            return filename
        except:
            return None

    def on_clear_search_box(self, *args):
        self.builder.get_object("search").set_text("")
        
    def create_formatting_tags(self, buffer):
        buffer.create_tag("project", font="Sans Bold 14", foreground="black")
        buffer.create_tag("task", foreground="black")
        buffer.create_tag("note", foreground="darkgrey"),
        buffer.create_tag("done", font="Sans Italic", foreground="darkgrey",
                          strikethrough="true"),
        buffer.create_tag("tag", font="Sans Bold 10", foreground="darkgrey")

    def quit(self, *args):
        if self.current_file:
            with open(os.path.join(os.path.expanduser("~"),
                                   ".taskpaper"), "w") as last:
                last.write(self.current_file)
        gtk.main_quit()

    def on_taskView_key_press_event(self, textview, event):
        key_name = gtk.gdk.keyval_name(event.keyval)
        if key_name == "Tab":
            return True

        return False

    def get_current_buffer(self):
        return self.task_view.get_buffer()

    def add_tag_to_entry(self, text):
        buffer = self.get_current_buffer()
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

    def text_changed(self, buffer, start, end):
        self.apply_formatting(buffer, start, end)
        self.set_changed(True)

    def insert_text(self, buffer, iter, text, length):
        if self.user_action:
            self.undo.append(("insert_text", iter.get_offset(),
                              iter.get_offset() +
                                len(re.findall(".", text)), text))
            self.redo = []

        offset_iter = buffer.get_iter_at_offset(iter.get_offset() + length)
        self.text_changed(buffer, iter, offset_iter)
        
    def delete_text(self, buffer, start, end):
        if self.user_action:
            text = buffer.get_text(start, end)
            self.undo.append(("delete_range", start.get_offset(),
                              end.get_offset(), text))

        self.text_changed(buffer, start, end)

    def on_copy_text(self, *w):
        self.get_current_buffer().copy_clipboard(gtk.clipboard_get())

    def on_cut_text(self, *w):
        self.get_current_buffer().cut_clipboard(gtk.clipboard_get(),
                                  self.task_view.get_editable())

    def on_paste_text(self, *w):
        clipboard = gtk.clipboard_get()
        clipboard.request_text(self.format_text_from_clipboard)

    def format_text_from_clipboard(self, clipboard, text, data):
        buffer = self.get_current_buffer()
        buffer.insert_at_cursor(text)

    def on_taskView_insert_at_cursor(self, *w):
        pass
        
    def begin_user_action(self, *w):
        self.user_action = True

    def end_user_action(self, *w):
        self.user_action = False

    def undo(self, w):
        if len(self.undo) == 0:
            return
        
        action = self.undo.pop()
        buffer = self.get_current_buffer()
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
        buffer = self.get_current_buffer()
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
        buffer = self.get_current_buffer()
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

    def apply_formatting(self, buffer, start_iter, end_iter=None):
        line_number = start_iter.get_line()
        lines = []
        
        if end_iter:
            if start_iter.get_line() == end_iter.get_line():
                lines.append(line_number)
            else:
                lines = range(start_iter.get_line(), end_iter.get_line() + 1)
        else:
            lines.append(line_number)
        
        for line_number in lines:
            start = buffer.get_iter_at_line(line_number)
            end   = buffer.get_iter_at_line(line_number)
            end.forward_to_line_end()
            buffer.remove_all_tags(start, end)
            text = buffer.get_slice(start, end)
            
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

            before_tags = buffer.get_iter_at_line(start.get_line())
            while before_tags.get_char() != "@" and not before_tags.equal(end):
                before_tags.forward_char()
            before_tags.backward_char()
            
            if self.is_entry_done(text):
                buffer.apply_tag_by_name("done", start, before_tags)

            before_tags.forward_char()
            iter = before_tags
            tag_begin = None
            
            while not iter.equal(end):
                char = iter.get_char()
                if char == "@":
                    tag_begin = iter
                elif char == " " and tag_begin:
                    buffer.apply_tag_by_name("tag", tag_begin, iter)
                    tag_begin = None
                iter.forward_char()

    def create_project_map(self):
        buffer = self.get_current_buffer()
        iter = buffer.get_start_iter()
        self.projects = {}
        
        while not iter.is_end():
            text = self.get_text_from_line(iter)
            if self.is_project(text):
                project_name = self.project.match(text).groups()[0]
                self.projects[iter.get_line()] = project_name

        return self.projects
                    
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
        buffer = self.get_current_buffer()
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
        buffer = self.get_current_buffer()
        iter   = buffer.get_start_iter()
        removed = []

        last_valid = iter.get_line()
        
        while not iter.is_end():
            text = self.get_text_from_line(iter)
            project = self.find_closest_project(buffer, iter)
            print project, text
            if project != "Archive" and self.is_entry_done(text):
                line = iter.get_line() 
                line_end = buffer.get_iter_at_line(line)
                line_end.forward_to_line_end()
                removed.append((project, text))
                buffer.delete(iter, line_end)
                iter = buffer.get_iter_at_line(last_valid)

            last_valid = iter.get_line()
            iter.forward_line()

        archive_iter = self.get_archive_insertion_point()

        for project, task in removed:
            text = task
            if project: text = "%s @project(%s)" % (text, project, )
            buffer.insert(archive_iter, "\n" + text)

    def get_archive_insertion_point(self):
        buffer = self.get_current_buffer()
        iter   = buffer.get_start_iter()
        line   = None
        
        while not iter.is_end():
            text = self.get_text_from_line(iter)
            if re.match("Archive", text) or line != None:
                line = iter.get_line()
            iter.forward_line()

        if line:
            iter.forward_to_line_end()
            buffer.insert(iter, "\n")
        else:
            iter = buffer.get_end_iter()
            buffer.insert(iter, "\n\nArchive:")

        return buffer.get_end_iter()

    def get_text_from_line(self, iter):
        """
        Gets text from the line pointed at by `iter`.
        Arguments:
        - `iter`: gtk.TextIter whose line will be used
        """
        buffer     = iter.get_buffer()
        line_start = buffer.get_iter_at_line(iter.get_line())
        line_end   = buffer.get_iter_at_line(iter.get_line())
        line_end.forward_to_line_end()
        
        return buffer.get_slice(line_start, line_end)

    def find_closest_project(self, buffer, iter):
        project_iter = buffer.get_iter_at_line(iter.get_line())
        while not project_iter.is_start():
            text = self.get_text_from_line(project_iter)
            if self.is_project(text):
                project = self.project.match(text).groups()[0]
                return project
            project_iter.backward_line()

        return None

    def on_open_tasks(self, *item):
        if self.changed:
            pass
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
        buffer = self.get_current_buffer()
        text = buffer.get_text(buffer.get_start_iter(),
                               buffer.get_end_iter())
        file = open(filename, "w")
        file.write(text)
        file.close()
        self.current_file = filename
        self.set_changed(False)
        
    def on_save_as_new_tasks(self, *item):
        pass

    def cancel_dialog(self, dialog):
        dialog.hide()

    def perform_dialog_action(self, dialog):
        buffer = self.get_current_buffer()
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
