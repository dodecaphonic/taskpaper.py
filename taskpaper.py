import gtk
import re

class Taskpaper:
    def __init__(self):
        self.patterns  = { "project" : re.compile("(.*?):\s*$"),
                           "task" : re.compile("^\s*-\s+(.*)"),
                           "tags" : re.compile("(@(\w+)(?:\((.*?)\))?)") }
        self.changed   = False
        self.builder   = gtk.Builder()
        self.builder.add_from_file("taskpaper.glade")
        self.window    = self.builder.get_object("taskpaper")
        self.taskList  = self.builder.get_object("taskList")
        self.builder.connect_signals(self, None)
        self.window.show_all()
        self.projects = [] # a list of line indices. Current project
                           # is the nearest preceding line in this list.
        self.create_formatting_tags(self.taskList.get_buffer())
        self.tag_table = {}

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
        
    def received_input(self, textview, event):
        key_name = gtk.gdk.keyval_name(event.keyval)
        if not key_name in ('Down', 'Up', 'Left', 'Right'):
            buffer = textview.get_buffer()
            curr   = buffer.get_iter_at_mark(buffer.get_insert())
            row    = curr.get_line()
            col    = curr.get_line_offset()
            self.apply_formatting(buffer, curr.get_line())
    
    def apply_formatting(self, buffer, line_number):
        start = buffer.get_iter_at_line(line_number)
        end   = buffer.get_iter_at_line(line_number)
        end.forward_to_line_end()
        buffer.remove_all_tags(start, end)
        text  = buffer.get_slice(start, end)
        if self.is_project(text):
            self.mark_as_project(line_number)
            buffer.apply_tag_by_name("project", start, end)
        else:
            if self.line_is_project(line_number):
                self.unmark_as_project(line_number)
                
            if self.is_task(text):
                buffer.apply_tag_by_name("task", start, end)
                tags = self.parse_tags(text, line_number)
                if len([tag for tag in tags if re.match("done", tag[1])]) > 0:
                    buffer.apply_tag_by_name("done", start, end)
            else:
                buffer.apply_tag_by_name("note", start, end)

    def mark_as_project(self, line_number):
        if not line_number in self.projects:
            self.projects.append(line_number)
            
    def line_is_project(self, line_number):
        return line_number in self.projects

    def unmark_as_project(self, line_number):
        self.projects.remove(line_number)
        
    def is_project(self, text):
        return self.patterns["project"].match(text) != None
        
    def is_task(self, text):
        return self.patterns["task"].match(text) != None

    def parse_tags(self, task, line_number):
        tags = self.patterns["tags"].findall(task)
        for _, tag, annotations in tags:
            if not self.tag_table.has_key(tag): self.tag_table[tag] = []
            self.tag_table[tag].append(line_number)
        return [(t[0], t[1]) for t in tags]

    def load_tasks_file(self, filename):
        tasks  = open(filename).read()
        buffer = self.taskList.get_buffer()
        buffer.set_text(tasks)
        for line in range(buffer.get_line_count()):
            self.apply_formatting(buffer, line)

    def create_project(self, project_name):
        project = Project(project_name)
        task_list.add_project(project)
        return project
    
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

if __name__ == "__main__":
    tp = Taskpaper()
    tp.load_tasks_file("sample.taskpaper")
    gtk.main()
