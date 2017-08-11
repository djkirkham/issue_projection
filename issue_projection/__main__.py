import datetime
import logging
import os
import pprint

import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.log
import tornado.web


tornado.log.enable_pretty_logging()


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world ({})".format(datetime.datetime.now().isoformat()))

class PayloadHandler(tornado.web.RequestHandler):
    def post(self):
        headers = self.request.headers
        event = headers.get('X-GitHub-Event', None)
        print(event)
        if event == 'issues':
            payload = tornado.escape.json_decode(self.request.body)
            user = payload['sender']['login']
            action = payload['action']
            issue_number = payload['issue']['number']
            issue_title = payload['issue']['title']
            timestamp = payload['issue']['updated_at']
            print('{user} {action} issue #{number} "{title}" at {timestamp}.'
                    .format(user=user, action=action, number=issue_number,
                            title=issue_title, timestamp=timestamp))

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
