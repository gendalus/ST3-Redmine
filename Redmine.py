import json
from datetime import datetime
import urllib.request

import sublime
import sublime_plugin
# from pprint import pprint


class RedmineProject():
    def __init__(self, base_url, api_key, project_name):
        # vars needed for the fetch
        self.url = base_url
        self.key = api_key
        self.identifier = project_name
        self.enabled_modules = []
        self.enabled_modules_names = []
        self.fetch()

    def fetch(self):
        # implementing auth key only for planio
        url = "%s/projects/%s.json?key=%s&include=enabled_modules" % (
               self.url,
               self.identifier,
               self.key
            )
        request = urllib.request.Request(url)
        response = urllib.request.urlopen(request)
        data = json.loads(response.read().decode())

        project = data['project']

        self.id = project['id']
        self.name = project['name']
        self.parent = project['parent']['name']
        self.status = project['status']
        self.description = project['description']
        self.homepage = project['homepage']
        self.created_on = project['created_on']
        self.updated_on = project['updated_on']

        modules = project['enabled_modules']
        for module in modules:
            self.enabled_modules.append(module['name'])
            if module['name'] == "issue_tracking":
                self.enabled_modules_names.append("Issues")
            elif module['name'] == "news":
                self.enabled_modules_names.append("News")
            elif module['name'] == "files":
                self.enabled_modules_names.append("Files")
            elif module['name'] == "wiki":
                self.enabled_modules_names.append("Wiki")
            elif module['name'] == "repository":
                self.enabled_modules_names.append("Repository")
            elif module['name'] == "boards":
                self.enabled_modules_names.append("Boards")
            elif module['name'] == "calendar":
                self.enabled_modules_names.append("Calendar")
            elif module['name'] == "gantt":
                self.enabled_modules_names.append("Gantt")
            elif module['name'] == "agile":
                self.enabled_modules_names.append("Agile")
            elif module['name'] == "documents":
                self.enabled_modules_names.append("Documents")
            elif module['name'] == "crm":
                self.enabled_modules_names.append("CRM")
            # UI feedback when there's a possibility missing
            else:
                self.enabled_modules_names.append("ERROR")


class RedmineIssue():
    def __init__(self, base_url, api_key, issue_id):
        self.url = "%s/issues/%s.json?key=%s" % (base_url,
                                                 issue_id,
                                                 api_key)
        self.fetch()

    def fetch(self):
        request = urllib.request.Request(self.url)
        response = urllib.request.urlopen(request)
        data = json.loads(response.read().decode())

        issue = data['issue']
        self.id = issue['id']

        for item in issue:
            if type(issue[item]).__name__ != "dict":
                # setting attributes so you can call issue['subject']
                # with self.subject
                setattr(self, item, issue[item])
            else:
                # setting attributes so you can call issue['category']
                # with self.category and its id with self.category_id
                setattr(self, item, issue[item]['name'])
                setattr(self, "%s_id" % item, issue[item]['id'])

    def change_status(self, status):
        if status not in [0, 1, 2]:
            return
        if status == 0 and self.status_id != 1:
            new_state_id = 1
        if status == 1 and self.status_id != 2:
            new_state_id = 2
        if status == 2 and self.status_id != 4:
            new_state_id = 4

        load = '{"issue": {"status_id": %d} }' % new_state_id
        load = str.encode(load)
        headers = {"Content-Type": "application/json;"}
        req = urllib.request.Request(url=self.url,
                                     data=load,
                                     headers=headers,
                                     method='PUT')
        response = response = urllib.request.urlopen(req)
        http_code = response.getcode()
        if http_code != 200:
            sublime.error_message("Status change failed")


class RedmineWiki():
    def __init__(self, base_url, api_key, project_name):
        self.url = base_url
        self.key = api_key
        self.identifier = project_name
        print(self.identifier)

        self.page_list = self.fetch_page_list()

    def fetch_page_list(self):
        page_list = []

        url = "%s/projects/%s/wiki/index.json?key=%s" % (self.url,
                                                         self.identifier,
                                                         self.key)
        request = urllib.request.Request(url)
        response = urllib.request.urlopen(request)
        data = json.loads(response.read().decode())
        pages = data['wiki_pages']

        for page in pages:
            page_list.append({"title": page['title'],
                              "change_date": page['updated_on']})

        return page_list


class RedmineWikiPage():
    def __init__(self, base_url, api_key, project_id, page_name):
        self.url = base_url
        self.key = api_key
        self.project_id = project_id
        self.name = page_name
        self.page_text = ""
        self.fetch()

    def fetch(self):
        url = "%s/projects/%s/wiki/%s.json?key=%s" % (self.url,
                                                      self.project_id,
                                                      self.name,
                                                      self.key)
        request = urllib.request.Request(url)
        response = urllib.request.urlopen(request)
        data = json.loads(response.read().decode())
        page = data['wiki_page']
        self.page_text = page['text']

    def text(self, text=None):
        if text is None:
            return self.page_text
        else:
            pass


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
        self.settings['show_project_name'] = settings.get('show_project_name')

    def list_stuff_to_do(self):
        if self.settings['auth_via_api_key']:
            url = "%s/projects/%s/issues.json?assigned_to_id=%s&key=%s" % (
                   self.settings['redmine_url'],
                   self.project_id,
                   self.settings["redmine_user_id"],
                   self.settings["api_key"]
                )
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
        self.window.run_command('get_project', {"project_id": project_id})
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


class GetProjectCommand(sublime_plugin.WindowCommand):
    def __init__(self, *a, **ka):
        super(GetProjectCommand, self).__init__(*a, **ka)
        self.project = None

    def on_select(self, picked):
        if picked == -1:
            return
        picked_item = self.project.enabled_modules[picked]

        if picked_item == "issue_tracking":
            self.window.run_command('get_issues',
                                    {"project_id": self.project.identifier})
        elif picked_item == "wiki":
            self.window.run_command('get_wiki',
                                    {"project_id": self.project.identifier})
        else:
            pass

    def async_load(self):
        self.project = RedmineProject(self.manager.settings['redmine_url'],
                                      self.manager.settings['api_key'],
                                      self.manager.project_id)
        self.window.show_quick_panel(self.project.enabled_modules_names,
                                     self.on_select)

    def run(self, *a, **ka):
        self.manager = RedmineManager()
        self.manager.project_id = ka['project_id']
        sublime.set_timeout_async(self.async_load, 0)


class GetWikiCommand(sublime_plugin.WindowCommand):
    def __init__(self, *a, **ka):
        super(GetWikiCommand, self).__init__(*a, **ka)
        self.wiki = None
        self.wiki_pages = None

    def on_select(self, picked):
        if picked == -1:
            return
        selected_title = self.wiki_pages[picked]['title']
        self.window.run_command('open_page',
                                {"project_id": self.manager.project_id,
                                 "page_name": selected_title})

    def async_load(self):
        # still missing the inicators for parents in ui
        self.wiki = RedmineWiki(self.manager.settings['redmine_url'],
                                self.manager.settings['api_key'],
                                self.manager.project_id)
        self.wiki_pages = self.wiki.page_list
        pages_to_display = []
        for page in self.wiki_pages:
            date_str = page['change_date'][0:19]
            change_date = datetime.strptime(date_str,
                                            "%Y-%m-%dT%H:%M:%S")
            change_string = "Last Change: "
            change_string += change_date.strftime("%d.%m.%y. %H:%M")
            pages_to_display.append([page['title'],
                                     change_string])
        self.window.show_quick_panel(pages_to_display, self.on_select)

    def run(self, *a, **ka):
        self.manager = RedmineManager()
        self.manager.project_id = ka['project_id']
        sublime.set_timeout_async(self.async_load, 0)


class GetIssuesCommand(sublime_plugin.WindowCommand):
    def __init__(self, *a, **ka):
        super(GetIssuesCommand, self).__init__(*a, **ka)
        self.issues = None
        self.issue_names = []

    def on_select(self, picked):
        if picked == -1:
            return
        issue = self.issues[picked]

        self.window.run_command('get_issue', {'issue_id': issue['id']})

    def async_load(self):
        self.issues = self.manager.list_stuff_to_do()
        for issue in self.issues:
            issue_entry = []
            issue_entry.append("%s (%d)" % (issue['subject'], issue['id']))

            if self.manager.settings['show_project_name']:
                issue_entry.append(issue['project']['name'])

            issue_entry.append("Status: %s - Priorität: %s" % (
                               issue['status']['name'],
                               issue['priority']['name']))

            issue_entry.append(issue["description"][0:85])

            self.issue_names.append(issue_entry)
        self.window.show_quick_panel(self.issue_names, self.on_select)

    def run(self, *args, **ka):
        self.manager = RedmineManager()

        self.issues = None
        self.issue_names = []

        self.manager.project_id = ka["project_id"]
        sublime.set_timeout_async(self.async_load, 0)


class GetIssueCommand(sublime_plugin.WindowCommand):
    def __init__(self, *a, **ka):
        super(GetIssueCommand, self).__init__(*a, **ka)
        self.issue = None
        self.attr_list = []
        self.change = None

    def on_change(self, picked):
        if self.change == "status":
            self.issue.change_status(picked)

    def on_select(self, picked):
        self.change = self.attr_list[picked]

        if self.change == "status":
            panel_items = ["Offen", "In Bearbeitung", "Erledigt"]
            self.window.show_quick_panel(panel_items, self.on_change)

    def async_load(self):
        self.issue = RedmineIssue(self.manager.settings['redmine_url'],
                                  self.manager.settings['api_key'],
                                  self.issue_id)

        issue_attr = dir(self.issue)
        attr_excludes = ["url", "key", "fetch", "id", "identifier",
                         "change_status"]
        for item in issue_attr:
            if "__" not in item and item not in attr_excludes:
                if "_id" not in item:
                    self.attr_list.append(item)
        self.attr_list = sorted(self.attr_list)

        panel_items = []
        for item in self.attr_list:
            name = item.replace("_", " ")
            name = name.title()

            sub_line = str(getattr(self.issue, item))

            if "_on" in item:
                i_date = sub_line[0:19]
                i_date = datetime.strptime(i_date,
                                           "%Y-%m-%dT%H:%M:%S")
                sub_line = i_date.strftime("%d.%m.%y. %H:%M")

            if "_date" in item:
                i_date = datetime.strptime(sub_line, "%Y-%m-%d")
                sub_line = i_date.strftime("%d.%m.%y.")

            if item == "done_ratio":
                sub_line = "%s%%" % sub_line

            panel_items.append([name, sub_line])

        self.window.show_quick_panel(panel_items, self.on_select)

    def run(self, *a, **ka):
        self.issue_id = ka['issue_id']
        self.manager = RedmineManager()
        sublime.set_timeout_async(self.async_load, 0)


class OpenPageCommand(sublime_plugin.WindowCommand):
    def run(self, *a, **ka):
        self.manager = RedmineManager()
        project_id = ka['project_id']
        page_name = ka['page_name']
        wiki_page = RedmineWikiPage(self.manager.settings['redmine_url'],
                                    self.manager.settings['api_key'],
                                    project_id,
                                    page_name)

        v = self.window.new_file()
        v.set_syntax_file("Packages/Textile/Textile.tmLanguage")
        v.set_name("%s Wiki: %s" % (project_id, wiki_page.name))
        self.window.run_command('insert_text', {"text": wiki_page.text()})


class InsertTextCommand(sublime_plugin.TextCommand):
    def run(self, edit, text):
        if "\r" in text:
            text = text.replace("\r", "")
        self.view.insert(edit, 0, text)
