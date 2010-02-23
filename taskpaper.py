import gtk
import re
import format

# TODO:
# - Load, save
# - Line -> structure linking
# - Outlines, document outline
# - Better visuals -- fonts, separators, the shizz
# - Moving text around
# - Search
# - Global entry method (hotkey from anywhere triggers input window)
# - Observable TaskList
# - Nearest project when clicking

class Taskpaper:
    def __init__(self):
        self.parser    = format.Parser()
        self.task_list = format.TaskList()
        self.current_project = None
        self.changed   = False
        self.builder   = gtk.Builder()
        self.builder.add_from_file("taskpaper.glade")
        self.window    = self.builder.get_object("taskpaper")
        self.task_view = self.builder.get_object("taskView")
        self.builder.connect_signals(self, None)
        self.window.show_all()
        self.create_formatting_tags(self.task_view.get_buffer())
        self.object_line = [] # Lists object per line. See text input methods
                              # to know how this is useful.

    def clear_search_box(self, *args):
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

    def before_input(self, textview, event):
        key_name = gtk.gdk.keyval_name(event.keyval)
        if key_name == "Tab":
            print self.task_list
            return True

        return False

    def move_cursor(self, *textview):
        #print "MC: ", textview
        pass

    def insert_text(self, buffer, iter, char, length):
        pass
        #self.apply_formatting(buffer, iter)        

    def delete_text(self, *textview):
        pass

    def after_input(self, textview, event):
        key_name = gtk.gdk.keyval_name(event.keyval)
        buffer = textview.get_buffer()
        curr   = buffer.get_iter_at_mark(buffer.get_insert())
                
        if key_name in ("Return", "KP_Enter"):
            line = curr.get_line()
            note = format.Note()
            
            try:
                current = self.object_line[line]
                self.task_list.add_note(note, after=current)
                self.object_line.insert(line, current)
            except:
                self.object_line.append(note)
                
        elif not key_name in ("Down", "Up", "Left", "Right"):
            self.apply_formatting(buffer, curr)

        return False

    def task_view_clicked(self, click):
        buffer = self.task_view.get_buffer()
        curr = buffer.get_iter_at_mark(buffer.get_insert())
        self.set_current_project(nearest_to=curr.get_line())
    
    def apply_formatting(self, buffer, iter, loading=False):
        line_number = iter.get_line()
        start = buffer.get_iter_at_line(iter.get_line())
        end   = buffer.get_iter_at_line(iter.get_line())
        end.forward_to_line_end()
        buffer.remove_all_tags(start, end)
        text  = buffer.get_slice(start, end)

        if self.is_project(text):
            if not loading:
                project = self.add_project(text, line_number)
                self.set_current_project(project)
            
            buffer.apply_tag_by_name("project", start, end)
        else:
            if self.line_is_project(line_number):
                self.remove_project(line_number)
                self.set_current_project(nearest_to=line_number)
                
            if self.is_task(text):
                buffer.apply_tag_by_name("task", start, end)
                task = None
                
                try:
                    object = self.object_line[line_number]
                    task  = self.parser.parse_task(text)
                    self.object_line[line_number] = task
                    # place = self.current_project.tasks.index(task)
                    # self.current_project.tasks[place] = updated
                    
                except:
                    task = self.parser.parse_task(text)
                    if self.current_project:
                        self.current_project.add_task(task)
                    else:
                        self.task_list.add_task(task)
                    self.object_line.append(task)
                    
                if len([tag for tag in task.tags if tag.name == "done"]) > 0:
                    buffer.apply_tag_by_name("done", start, end)
            else:
                buffer.apply_tag_by_name("note", start, end)

    def line_is_project(self, line_number):
        return isinstance(self.object_line, format.Project)

    def is_project(self, text):
        return self.parser.is_project(text)
        
    def is_task(self, text):
        return self.parser.is_task(text)

    def load_tasks_file(self, filename):
        self.task_list = self.parser.parse(filename)
        buffer = self.task_view.get_buffer()
        buffer.set_text(str(self.task_list))
        for line in range(buffer.get_line_count()):
            self.apply_formatting(buffer, buffer.get_iter_at_line(line), True)

    def create_project(self, project_name):
        project = Project(project_name)
        task_list.add_project(project)
        return project

    def add_project(self, text, line_number):
        return self.parser.parse_project(text)

    def set_current_project(self, project=None, nearest_to=0):
        if project:
            self.current_project = project
        else:
            if nearest_to == 0:
                return self.task_list

    def archive_done_tasks(self):
        archive = self.task_list.get_archive()
        for project in [p for p in self.task_list.projects if p != archive]:
            done_tasks = [t for t in project.children if t.is_done()]
            for t in done_tasks:
                archive.add_task(t)
                project.remove_task(t)
        # TODO: update view
        
    def mark_as_done(self, task):
        # TODO: update view
        pass

    def open_tasks_file(self, *item):
        print item

    def save_tasks_file(self, *item):
        dialog = self.builder.get_object("saveFile")
        dialog.set_transient_for(self.window)
        dialog.show_all()

    def save_as_new_tasks_file(self, *item):
        print item

    def cancel_dialog(self, *widget):
        print widget

    def perform_dialog_action(self, *widget):
        print widget

if __name__ == "__main__":
    tp = Taskpaper()
    tp.load_tasks_file("sample.taskpaper")
    gtk.main()
