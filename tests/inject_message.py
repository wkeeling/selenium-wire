"""This addon will inject a message in the form of an html comment
 at the end of the html body.
 """

from mitmproxy import ctx, http

COMMENT = 'This passed through a {} proxy'  # mode subsituted via injectmode option


class AddMessage:

    def load(self, loader):
        loader.add_option(
            name='injectmode',
            typespec=str,
            default='http',
            help="Specify the mode of operation - either 'http' or 'socks'.",
        )

    def response(self, flow: http.HTTPFlow) -> None:
        comment = COMMENT.format(ctx.options.injectmode)
        flow.response.content = flow.response.content.replace(
            b'</body>', b'<!-- %s --></body>' % comment.encode('utf-8')
        )


addons = [
    AddMessage()
]
