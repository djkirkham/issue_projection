import datetime
import logging
import os
import requests

import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.log
import tornado.web


tornado.log.enable_pretty_logging()

URL = 'https://api.github.com'
API_TOKEN = os.environ['ACCESS_TOKEN']

def get_content(target, accept=None):
    if accept is None:
        accept = 'application/vnd.github.v3+json'
    headers = {'Accept': accept, 'Authorization': 'token {}'.format(API_TOKEN)}
    response = requests.get('{}{}'.format(URL, target), headers=headers)
    response.raise_for_status()
    content = response.json()
    return content

def post_content(target, json, accept=None):
    if accept is None:
        accept = 'application/vnd.github.v3+json'
    headers = {'Accept': accept, 'Authorization': 'token {}'.format(API_TOKEN)}
    response = requests.post('{}{}'.format(URL, target), json=json, headers=headers)
    response.raise_for_status()
    content = response.json()
    return content

def get_projects(user, repo, label=None):
    target = '/repos/{}/{}/projects'.format(user, repo)
    projects = get_content(target, accept='application/vnd.github.inertia-preview+json')
    if label is not None:
        name = '{} project'.format(label.lower())
        for project in projects:
            if project['name'].lower() == name:
                result = project
                break
    else:
        result = projects
    return result


def get_issue(user, repo, number):
    target = '/repos/{}/{}/issues/{}'.format(user, repo, number)
    return get_content(target, accept='application/vnd.github.inertia-preview+json')


def get_project_columns(project):
    target = '/projects/{}/columns'.format(project['id'])
    return get_content(target, accept='application/vnd.github.inertia-preview+json')


def get_columns_issue_urls(columns):
    urls = []
    for column in columns:
        for card in get_project_column_cards(column):
            urls.append(card['content_url'])
    return urls


def get_project_column_cards(column):
    target = '/projects/columns/{}/cards'.format(column['id'])
    cards = get_content(target, accept='application/vnd.github.inertia-preview+json')
    return cards


def post_project_column_cards(column, issues):
    target = '/projects/columns/{}/cards'.format(column['id'])
    for issue in issues:
        logging.info('- START ----------')
        logging.info(issue)
        logging.info('- END   ----------')
        json = {'content_id': issue['id'], 'content_type': 'Issue'}
        response = post_content(target, json, accept='application/vnd.github.inertia-preview+json')


def filter_columns_issues(columns, issues):
    urls = get_columns_issue_urls(columns)
    result = []
    for issue in issues:
        if issue['url'] not in urls:
            result.append(issue)
    return result


def log_labeled_issue(event, payload):
    index = 'issue' if event == 'issues' else 'pull_request'
    user = payload['sender']['login']
    issue_number = payload[index]['number']
    issue_title = payload[index]['title']
    timestamp = payload[index]['updated_at']
    label= payload['label']['name']
    logging.info(
        '{user} labeled {index} #{number} with label {label} '\
        'at {timestamp}.'.format(user=user, number=issue_number, index=index,
                                 title=issue_title, label=label,
                                 timestamp=timestamp))


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world ({})".format(datetime.datetime.now().isoformat()))


class PayloadHandler(tornado.web.RequestHandler):

    def post(self):
        try:
            headers = self.request.headers
            event = headers.get('X-GitHub-Event', None)
            logging.info(event)
            payload = tornado.escape.json_decode(self.request.body)
            logging.info(payload)
            if event in ('issues', 'pull_request'):
                action = payload['action']
                logging.info(action)
                label = 'bug'
                issue_label = payload['label']['name']
                if action == 'labeled' and issue_label == label:
                    log_labeled_issue(event, payload)
                    repo_owner = payload['repository']['owner']['login']
                    repo_name = payload['repository']['name']
                    if event == 'pull_request':
                        number = payload['number']
                        issue = get_issue(repo_owner, repo_name, number)
                    else:
                        issue = payload['issue']
                    project = get_projects(repo_owner, repo_name, label=label)
                    columns = get_project_columns(project)
                    column, = [column for column in columns
                               if column['name'].lower() == 'backlog']
                    issues = filter_columns_issues(columns, [issue])
                    post_project_column_cards(column, issues)
        except Exception as e:
            logging.error(str(e))
            raise

def main():
    application = tornado.web.Application([
        (r"/", MainHandler),
        (r"/payload", PayloadHandler),
    ])
    http_server = tornado.httpserver.HTTPServer(application)
    PORT = os.environ.get('PORT', 8080)
    http_server.listen(PORT)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
