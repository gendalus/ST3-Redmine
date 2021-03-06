import json
from datetime import datetime
import re
import os
import sys
import sublime
import sublime_plugin
sys.path.append(os.path.dirname(__file__))
import requests


def plugin_loaded():
    ''' checking for users settings file '''
    settings = sublime.load_settings("Redmine.sublime-settings")

    user_id = settings.get('redmine_user_id')
    url = settings.get('redmine_url')
    key = settings.get('api_key')

    if not user_id and not url and not key:
        act_window = sublime.active_window()
        settings_path = "$packages/User/Redmine.sublime-settings"
        act_window.run_command("open_file", {"file": settings_path})


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
        r = requests.get(url)
        data = json.loads(r.text)

        project = data['project']

        self.id = project['id']
        self.name = project['name']
        if "parent" in project:
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
        self.change_headers = {"Content-Type": "application/json"}
        self.__fetch()

    def __fetch(self):
        r = requests.get(self.url)
        data = json.loads(r.text)

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

    def change_done_ratio(self, ratio):
        data = json.dumps({"issue": {"done_ratio": ratio}})
        r = requests.put(self.url, data=data, headers=self.change_headers)

        if r.status_code != 200:
            sublime.error_message("Done ratio change failed")

    def change_priority(self, priority):
        data = json.dumps({"issue": {"priority_id": priority}})
        r = requests.put(self.url, data=data, headers=self.change_headers)

        if r.status_code != 200:
            sublime.error_message("Priority change failed")

    def change_status(self, status):
        if status not in [0, 1, 2]:
            return
        if status == 0 and self.status_id != 1:
            new_state_id = 1
        if status == 1 and self.status_id != 2:
            new_state_id = 2
        if status == 2 and self.status_id != 4:
            new_state_id = 4

        data = json.dumps({"issue": {"status_id": new_state_id}})
        r = requests.put(self.url, data=data, headers=self.change_headers)

        if r.status_code != 200:
            sublime.error_message("Status change failed")

    def change_subject(self, subject):
        data = json.dumps({"issue": {"subject": subject}})
        r = requests.put(self.url, data=data, headers=self.change_headers)

        if r.status_code != 200:
            sublime.error_message("Status change failed")


class RedmineWiki():
    def __init__(self, base_url, api_key, project_name):
        self.url = base_url
        self.key = api_key
        self.identifier = project_name

        self.page_list = self.fetch_page_list()

    def fetch_page_list(self):
        page_list = []

        url = "%s/projects/%s/wiki/index.json?key=%s" % (self.url,
                                                         self.identifier,
                                                         self.key)
        r = requests.get(url)
        data = json.loads(r.text)
        pages = data['wiki_pages']

        for page in pages:
            page_list.append({"title": page['title'],
                              "change_date": page['updated_on']})

        return page_list


class RedmineWikiPage():
    def __init__(self, base_url, api_key, project_id, page_name, version=None):
        self.key = api_key
        self.project_id = project_id
        self.name = page_name
        self.url = "%s/projects/%s/wiki/%s.json?key=%s" % (base_url,
                                                           self.project_id,
                                                           self.name,
                                                           self.key)
        self.page_text = ""
        self.version = version
        self.fetch()

    def fetch(self):
        r = requests.get(self.url)
        data = json.loads(r.text)
        page = data['wiki_page']
        self.page_text = page['text']

        if self.version is None:
            self.version = page['version']

    def text(self, text=None):
        if text is None:
            return self.page_text
        elif type(text).__name__ == "dict":
            if self.page_text == text['text']:
                return
            payload = {"text": text['text']}
            print(text)
            if self.version:
                payload['version'] = self.version

            if "comment" in text:
                payload['comments'] = text['comment']

        else:
            if self.page_text == text:
                return
            payload = {"text": text}

        if payload:
            data = json.dumps({"wiki_page": payload})
            headers = {"Content-Type": "application/json"}
            r = requests.put(self.url, data=data, headers=headers)

            if r.status_code != 200:
                sublime.error_message("Saving Failed")


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
        proj_names = settings.get('show_project_name_in_issue_list')
        self.settings['show_project_name'] = proj_names

    def list_stuff_to_do(self):
        if self.settings['auth_via_api_key']:
            url = "%s/projects/%s/issues.json?assigned_to_id=%s&key=%s" % (
                   self.settings['redmine_url'],
                   self.project_id,
                   self.settings["redmine_user_id"],
                   self.settings["api_key"]
                )
            r = requests.get(url)
            data = json.loads(r.text)
            issues = data["issues"]
            return issues
        else:
            url = "%s/issues.json?assigned_to_id=%s" % (
                   self.settings['redmine_url'],
                   self.settings["redmine_user_id"])

            r = requests.get(url, auth=(self.settings['username'],
                                        self.settings['password']))

            data = json.loads(r.text)
            issues = data["issues"]
            return issues

    def list_projects(self):
        projects = None
        if self.settings['auth_via_api_key']:
            url = "%s/projects.json?key=%s" % (self.settings['redmine_url'],
                                               self.settings['api_key'])
            r = requests.get(url)
            data = json.loads(r.text)
            projects = data['projects']
            return projects
        else:
            return []


class GetProjectsCommand(sublime_plugin.WindowCommand):
    def __init__(self, *a, **ka):
        super(GetProjectsCommand, self).__init__(*a, **ka)
        self.projects = None

    def on_select(self, picked):
        if picked == -1:
            return
        project_id = self.projects[picked]["identifier"]
        self.window.run_command('get_project', {"project_id": project_id})
        self.projects = None

    def async_load(self):
        self.projects = self.manager.list_projects()
        self.project_names = []
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
        if picked == -1:
            return

        if self.change == "status":
            self.issue.change_status(picked)

        if self.change == "done_ratio":
            def on_done(ratio_input):
                ratio = None

                try:
                    ratio = int(ratio_input)
                except Exception:
                    pass

                if ratio is None:
                    self.window.show_input_panel("Done ratio",
                                                 "",
                                                 on_done,
                                                 None,
                                                 None)
                else:
                    self.issue.change_done_ratio(ratio)

            if picked == 0:
                self.window.show_input_panel("Done ratio",
                                             "",
                                             on_done,
                                             None,
                                             None)
            else:
                ratio = picked - 1
                self.issue.change_done_ratio(ratio)

        if self.change == "priority":
            priority = [5, 6, 7]
            self.issue.change_priority(priority[picked])

    def on_select(self, picked):
        self.change = self.attr_list[picked]

        if self.change == "status":
            panel_items = ["Offen", "In Bearbeitung", "Erledigt"]
            self.window.show_quick_panel(panel_items, self.on_change)

        if self.change == "subject":
            def on_done(subject):
                self.issue.change_subject(subject)

            self.window.show_input_panel("Subject",
                                         self.issue.subject,
                                         on_done,
                                         None,
                                         None)

        if self.change == "done_ratio":
            panel_items = ["Custom", "0%"]
            for i in range(1, 11):
                panel_items.append("%d0%%" % i)
            self.window.show_quick_panel(panel_items, self.on_change)

        if self.change == "priority":
            panel_items = ["Niedrig", "Normal", "Hoch"]
            self.window.show_quick_panel(panel_items, self.on_change)

    def is_editable(self, item):
        if item == "updated_on":
            return False
        if item == "created_on":
            return False
        if item == "closed_on":
            return False
        return True

    def async_load(self):
        self.issue = RedmineIssue(self.manager.settings['redmine_url'],
                                  self.manager.settings['api_key'],
                                  self.issue_id)

        self.attr_list = []
        issue_attr = dir(self.issue)
        attr_excludes = ["url", "key", "id", "identifier"]
        for item in issue_attr:
            if "change_" not in item:
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

            if not self.is_editable(item):
                sub_line = "%s - %s" % (u"\U0001F512", sub_line)

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
        # setting syntax for identification purpusses
        # it's a copy of textile with an altered name
        v.set_syntax_file("Packages/ST3-Redmine/st3-wiki-page.tmLanguage")
        v.set_name("%s Wiki: %s" % (project_id, wiki_page.name))
        v.set_scratch(True)

        v.set_status("01", "Project: %s" % project_id)
        v.set_status("02", "Wiki page: %s (v. %d)" % (page_name,
                                                      wiki_page.version))

        self.window.run_command('insert_text', {"text": wiki_page.text()})


class ChangeWikiPage(sublime_plugin.WindowCommand):
    def run(self, *a, **ka):
        self.manager = RedmineManager()
        self.project_id = ka['project_id']
        self.page_name = ka['page_name']
        self.version = ka['version']
        self.whole_text = ka['whole_text']
        self.window.show_input_panel("Comment for Wiki Page Change",
                                     "",
                                     self.comment,
                                     None,
                                     None)

    def comment(self, text):
        if text != "":
            self.comment = text
        sublime.set_timeout_async(self.async_write, 0)

    def async_write(self):
        self.wiki = RedmineWikiPage(self.manager.settings['redmine_url'],
                                    self.manager.settings['api_key'],
                                    self.project_id,
                                    self.page_name,
                                    self.version)

        if self.comment:
            self.wiki.text({"text": self.whole_text,
                            "comment": self.comment})
        else:
            self.wiki.text(self.whole_text)


class InsertTextCommand(sublime_plugin.TextCommand):
    def run(self, edit, text):
        if "\r" in text:
            text = text.replace("\r", "")
        self.view.insert(edit, 0, text)


class EventListener(sublime_plugin.EventListener):
    def on_load(self, view):
        file_name = sublime.packages_path() + "/User/Redmine.sublime-settings"
        # is this the settings file?
        if view.file_name() == file_name:
            try:
                settings = sublime.load_settings("Redmine.sublime-settings")

                user_id = settings.get('redmine_user_id')
                url = settings.get('redmine_url')
                key = settings.get('api_key')

                if not user_id and not url and not key:
                    default_settings = open("Redmine.sublime-settings").read()
                    view.run_command("insert_text",
                                     {"text": default_settings})
            except Exception as e:
                raise e

    def on_pre_close(self, view):
        def is_wiki_page(self, view):
            if view.get_status("01")[:9] == "Project: ":
                if view.get_status("02")[:11] == "Wiki page: ":
                    return True

            return False

        if is_wiki_page(self, view):
            whole_text = view.substr(sublime.Region(0, view.size()))

            self.project_id = view.get_status("01")[9:]
            page_title = view.get_status("02")
            pattern = r'(?<=\(v. )(\d+)(?=\)$)'
            self.version = int(re.findall(pattern, page_title)[0])

            pattern = r'(?<=Wiki page: )(.*)(?= \(v. \d+)'
            self.page_name = re.findall(pattern, page_title)[0]

            view.window().run_command("change_wiki_page",
                                      {"project_id": self.project_id,
                                       "page_name": self.page_name,
                                       "version": self.version,
                                       "whole_text": whole_text})

            self.manager = RedmineManager()
            # self.wiki = RedmineWikiPage(self.manager.settings['redmine_url'],
            #                             self.manager.settings['api_key'],
            #                             self.project_id,
            #                             self.page_name,
            #                             self.version)

            # self.wiki.text(whole_text)
