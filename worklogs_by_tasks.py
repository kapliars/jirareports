#!/usr/bin/env python
# -W ignore::DeprecationWarning
# Suppress all deprecation warnings (not recommended for development)
import warnings
warnings.simplefilter('ignore', DeprecationWarning)

import sys

from common import JiraConnection

if len(sys.argv) < 2:
    print "Provide version name"
    sys.exit(1)

jira = JiraConnection()
(auth, client, project_name) = (jira.auth, jira.client, jira.project_name)

project = client.getProjectByKey(auth, project_name)

issue_types = {}
for t in client.getSubTaskIssueTypesForProject(auth, project.id):
    issue_types[t.id] = t
for t in client.getIssueTypesForProject(auth, project.id):
    issue_types[t.id] = t

version = sys.argv[1]

def build_tasks_hierarchy():
    issues = client.getIssuesFromJqlSearch(auth, 'project = %s and fixVersion = %s' % (project_name, version),
        jira.int_arg(1000))
    hierarchy = {}
    for issue in issues:
        if not issue_types[issue.type].subTask:
            children = client.getIssuesFromJqlSearch(auth, 'parent = "%s"' % issue.key, jira.int_arg(100))
            for child in children:
                hierarchy[child.key] = issue
                if child.fixVersions[0].name != version:
                    print "Warning: Sub-task %s (%s) is not assigned to version %s" % (child.key, child.summary, version)
    return hierarchy

def get_top_level_issue(issue):
    return issues_hierarchy[issue.key] if issue.key in issues_hierarchy else issue

class IssueStat(object):
    def __init__(self, issue):
        self.issue = issue
        self.time_spent = 0
    def log_work(self, worklog):
        self.time_spent += worklog.timeSpentInSeconds
    def issue_num(self):
        return int(self.issue.key.split('-')[1])


issues_hierarchy = build_tasks_hierarchy()
issues = client.getIssuesFromJqlSearch(auth, 'project = %s and fixVersion = %s' % (project_name, version),
    jira.int_arg(1000))

stats = {}
for issue in issues:
    top_level_issue = get_top_level_issue(issue)

    if not top_level_issue.key in stats:
        s = IssueStat(top_level_issue)
        stats[top_level_issue.key] = s
    else:
        s = stats[top_level_issue.key]

    worklogs = client.getWorklogs(auth, issue.key)
    for l in worklogs:
        s.log_work(l)

print "Work logged by top level issue"

items = stats.values()
items.sort(lambda i1, i2: cmp(i1.issue_num(), i2.issue_num()))
for s in items:
    if s.time_spent > 0:
        print "%s\t%s\t%s\t%s" % (s.issue.key, issue_types[s.issue.type].name, s.time_spent / 3600.0, s.issue.summary)
