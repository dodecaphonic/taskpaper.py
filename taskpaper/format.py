import re

class Container:
    def __init__(self):
        self.children = []

    def get_children(self):
        return self.children

    def add_child(self, child, after=None):
        if after:
            idx = self.children.index(after)
            self.children.insert(idx, after)
        else:
            self.children.append(child)

    def add_task(self, task, after=None):
        self.add_child(task, after)

    def add_note(self, note, after=None):
        self.add_child(note, after)
        
    def remove_child(self, child):
        self.children.remove(child)
        
    def remove_note(self, note):
        self.remove_child(note)
    
    def remove_task(self, task):
        self.remove_child(task)
        
    def __str__(self):
        return "".join([str(p) for p in self.children])
        
class TaskList(Container):
    def add_project(self, project, after=None):
        self.add_child(project, after)

    def remove_project(self, project):
        self.remove_child(project)

    def get_archive(self):
        archive = filter(lambda p: p.name == "Archive", self.children)
        if len(archive) == 0:
            archive = Project("Archive")
            self.add_project(archive)
        return archive

class Content:
    def __init__(self, text=None, tags=[], nesting=0):
        self.text = text
        self.tags = tags
        self.done = "done" in [t.name for t in tags]
        self.nesting = nesting

    def get_nesting(self):
        return self.nesting
    
    def set_nesting(self, nesting):
        self.nesting = nesting or 0
        
    def set_text(self, text):
        self.text = text

    def get_text(self):
        return self.text

    def set_done(self, done=True):
        self.done = done
        
    def is_done(self):
        return self.done
    
class Project(Container, Content):
    def __init__(self, name, tags=[], nesting=0):
        Container.__init__(self)
        Content.__init__(self, name, tags, nesting)

    def get_name(self):
        return self.get_text()

    def __str__(self):
        return "%s:\n%s" % (self.get_name(),
                            "\n".join([str(c) for c in self.children]))

class Task(Content):                          
    def __str__(self):
        return "- %s %s" % (self.text,
                            " ".join([str(tag) for tag in self.tags]))

class Note(Content):
    def __str__(self):
        return self.text

class Tag:
    def __init__(self, name, annotations=[]):
        self.name = name
        self.annotations = annotations
    
    def __str__(self):
        if len(self.annotations) > 0:
            return "@%s(%s)" % (self.name, " ".join(self.annotations))
        else:
            return "@%s" % (self.name, )
        
class Parser:
    def __init__(self):
        self.project = re.compile("(.*?):\s*$")
        self.task = re.compile("^\s*-\s+(.*)")
        self.tag  = re.compile("(@(\w+)(?:\((.*?)\))?)")

    def is_project(self, text):
        return self.project.match(text) != None

    def is_task(self, text):
        return self.task.match(text) != None

    def find_tags(self, task):
        tags = self.tag.findall(task)
        return [Tag(tag, (annotations and annotations.split(" ")) or []) for _, tag, annotations in tags]

    def parse(self, filename):
        task_list = TaskList()
        project   = None
        note      = None
        
        for line in open(filename):
            if self.is_project(line):
                project = self.parse_project(line)
                task_list.add_project(project)
            else:
                if self.is_task(line):
                    project.add_task(self.parse_task(line))
                else:
                    note = Note(line.strip() or "\n")
                    project.add_note(note)

        return task_list

    def parse_project(self, text):
        return Project(self.project.match(text).groups()[0])

    def parse_task(self, text):
        parts = self.task.match(text).groups()[0].split("@")
        return Task(parts[0].strip(), self.find_tags(text))
    
    def parse_tag(self, tag):
        tag, annotations = re.match("(\w+)(?:\((.*?)\))?", tag.strip()).groups()
        return Tag(tag, (annotations and annotations.split(" ")) or [])

