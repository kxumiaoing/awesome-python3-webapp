#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import logging
import orm
from models import User

logging.basicConfig(level = logging.INFO)


async def est_insert(loop):
	await orm.create_pool(loop = loop, user = "www", password = "www", database = "awesome")
	u = User(name = 'Test', email = 'test@example.com', password = '1234567890', image = 'about:blank')
	await u.save()
	print(u)


def main():
	loop = asyncio.get_event_loop()
	loop.run_until_complete(est_insert(loop))


if __name__ == '__main__':
	main()