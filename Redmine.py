import json
import urllib.request

import sublime
import sublime_plugin


class RedmineManager():
    def __init__(self):
        self.settings = {}
        settings = sublime.load_settings('Redmine.sublime-settings')
        self.settings['username'] = settings.get('username')
        self.settings['password'] = settings.get('password')
        self.settings['api_key'] = settings.get('api_key')
        self.settings['auth_via_api_key'] = settings.get('auth_via_api_key')
        self.settings['redmine_url'] = settings.get('redmine_url')
        self.settings['redmine_user_id'] = settings.get('redmine_user_id')

    def list_stuff_to_do(self):
        if self.settings['auth_via_api_key']:
            url = "%s/projects/%s/issues.json?assigned_to_id=%s&key=%s" % (
                   self.settings['redmine_url'],
                   self.project_id,
                   self.settings["redmine_user_id"],
                   self.settings["api_key"]
                )
            print(url)
            request = urllib.request.Request(url)
            response = urllib.request.urlopen(request)
            data = json.loads(response.read().decode())
            issues = data["issues"]
            return issues
        else:
            request = urllib.request.Request(self.settings['redmine_url'] +
                                             "/issues.json?assigned_to_id=" +
                                             self.settings["redmine_user_id"])
            auth_handler = urllib.request.HTTPBasicAuthHandler()
            auth_handler.add_password("Redmine API",
                                      self.settings["redmine_url"],
                                      self.settings["username"],
                                      self.settings["password"])
            opener = urllib.request.build_opener(auth_handler)
            urllib.request.install_opener(opener)
            response = urllib.request.urlopen(request)
            data = json.loads(response.read().decode())
            issues = data["issues"]
            return issues

    def list_projects(self):
        if self.settings['auth_via_api_key']:
            url = (self.settings['redmine_url'] +
                   "/projects.json?key=" +
                   self.settings['api_key'])
            request = urllib.request.Request(url)
            response = urllib.request.urlopen(request)
            data = json.loads(response.read().decode())
            projects = data['projects']
            return projects
        else:
            return []


class GetProjectsCommand(sublime_plugin.WindowCommand):
    def __init__(self, *a, **ka):
        super(GetProjectsCommand, self).__init__(*a, **ka)
        self.projects = None
        self.project_names = []

    def on_select(self, picked):
        if picked == -1:
            return
        project_id = self.projects[picked]["identifier"]
        self.window.run_command('get_issues', {"project_id": project_id})
        self.projects = None

    def async_load(self):
        self.projects = self.manager.list_projects()
        for project in self.projects:
            project_entry = []
            project_entry.append(project["name"])
            project_entry.append("id: %s - %s" % (project["id"],
                                                  project["identifier"]))
            self.project_names.append(project_entry)
        self.window.show_quick_panel(self.project_names, self.on_select)

    def run(self):
        self.manager = RedmineManager()
        sublime.set_timeout_async(self.async_load, 0)


class GetIssuesCommand(sublime_plugin.WindowCommand):
    def __init__(self, *a, **ka):
        super(GetIssuesCommand, self).__init__(*a, **ka)
        self.issues = None
        self.issue_names = []

    def on_done(self, picked):
        if picked == -1:
            return
        issue = self.issues[picked]
        url = (self.manager.settings['redmine_url'] + "/issues/" +
               str(issue["id"]))
        self.window.run_command('open_url', {'url': url})

    def async_load(self):
        self.issues = self.manager.list_stuff_to_do()
        for issue in self.issues:
            issue_entry = []
            issue_entry.append(issue["subject"] + " (" + str(issue["id"]) +
                               ")")
            issue_entry.append("%s %s" % (issue["project"]["name"],
                                          issue["description"][0:85]))
            self.issue_names.append(issue_entry)
        self.window.show_quick_panel(self.issue_names, self.on_done)

    def run(self, *args, **ka):
        self.manager = RedmineManager()

        self.issues = None
        self.issue_names = []

        self.manager.project_id = ka["project_id"]
        sublime.set_timeout_async(self.async_load, 0)
