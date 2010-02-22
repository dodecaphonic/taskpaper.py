class TaskList:
    def __init__(self):
        self.projects = []
    
    def add_project(self, project):
        self.projects.append(project)

    def get_archive(self):
        archive = filter(lambda p: p.name == 'Archive', self.projects)
        if len(archive) == 0:
            archive = Project('Archive')
            self.projects.append(archive)
        return archive

    def __str__(self):
        return "".join([str(p) for p in self.projects])
        
class Project:
    def __init__(self, name):
        self.name     = name
        self.children = []

    def add_note(self, note):
        self.children.append(note)
        
    def add_task(self, task):
        self.children.append(task)

    def remove_note(self, note):
        self.children.remove(note)
    
    def remove_task(self, task):
        self.children.remove(task)

    def __str__(self):
        return "%s:\n%s" % (self.name,
                            "\n".join([str(c) for c in self.children]))

class Content:
    def __init__(self, text=None, tags=[]):
        self.text = text
        self.tags = tags
        self.done = "done" in [t.name for t in tags]

    def is_done(self):
        return self.done

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

    def is_project(self, text):
        return self.project.match(text) != None

    def is_task(self, text):
        return self.task.match(text) != None

    def parse(self, filename):
        task_list = TaskList()
        project   = None
        note      = None
        
        for line in open(filename):
            is_project = self.project.match(line)
            if is_project:
                project = Project(is_project.groups()[0])
                task_list.add_project(project)
            else:
                is_task = self.task.match(line)
                if is_task:
                    project.add_task(self.parse_task(is_task.groups()[0]))
                else:
                    note = Note(line.strip() or "\n")
                    project.add_note(note)

        return task_list

    def parse_task(self, text):
        parts = text.split("@")
        return Task(parts[0].strip(),
                    [self.parse_tag(tag) for tag in parts[1:len(parts)]])
    
    def parse_tag(self, tag):
        tag, annotations = re.match("(\w+)(?:\((.*?)\))?", tag.strip()).groups()
        if annotations is None:
            return Tag(tag, [])
        else:
            return Tag(tag, annotations.split(" "))
