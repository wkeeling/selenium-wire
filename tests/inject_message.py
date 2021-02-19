"""This addon will inject a message in the form of an html comment
 at the end of the html body.
 """

from mitmproxy import ctx, http


class InjectMessage:

    def load(self, loader):
        loader.add_option(
            name='message',
            typespec=str,
            default='http',
            help="Specify the message to inject.",
        )

    def response(self, flow: http.HTTPFlow) -> None:
        flow.response.content = flow.response.content.replace(
            b'</body>', b'<!-- %s --></body>' % ctx.options.message.encode('utf-8')
        )


addons = [
    InjectMessage()
]
