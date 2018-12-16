#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
async web application.
"""


import asyncio
import logging
from aiohttp import web


logging.basicConfig(level = logging.INFO)


# functions
def index(request):
	return web.Response(body = b"<h1>Awesome!!!</h1>", headers = {"Content-Type": "text/html"})


async def init(loop):
	app = web.Application(loop = loop)
	app.router.add_route("GET", "/", index)
	server = await loop.create_server(app.make_handler(), "127.0.0.1", 9000)
	logging.info("server started at http://127.0.0.1:9000...")
	return server


def main():
	loop = asyncio.get_event_loop()
	loop.run_until_complete(init(loop))
	loop.run_forever()


if __name__ == '__main__':
	main()