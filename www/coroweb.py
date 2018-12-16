#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
coroutinal web framwork.
"""


import inspect
import logging
import os
from urllib import parse
from aiohttp import web
from apis import APIError


# functions
def get(path):
	"""
	defined decorator @get("/path")
	"""
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kw):
			return func(*args, **kw)
		wrapper.__method__ = "GET"
		wrapper.__route__ = path
		return wrapper
	return decorator


def post(path):
	"""
	defined decorator @post("/path")
	"""
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kw):
			return func(*args, **kw)
		wrapper.__method__ = "POST"
		wrapper.__route__ = path
		return wrapper
	return decorator


def parse_raw_handler(fn):
	"""
	1.check funciton fn whether has the 'request' parameter who is the last POSITIONAL_OR_KEYWORD type parameter.
		for example:
			fn(a,b,c,request, *args, d, **kw) is valid. because
				a,b,c --> POSITIONAL_OR_KEYWORD
				*args --> VAR_POSITIONAL
				d --> KEYWORD_ONLY
				**kw --> VAR_KEYWORD
	2.check function fn whether has VAR_KEYWORD(like kw defined in (**kw)) type parameters.
	3.check function fn whether has KEYWORD_ONLY(like a defined in (*,a) or (*args,b)) type parameter.
	4.get name of all named parameters.
	5.get name of all named parameters who have no default value.
	"""
	has_request_arg = False
	has_var_kw_arg = False
	has_name_kw_arg = False
	named_args = []
	required_args = []
	sig = inspect.signature(fn)
	valid_types = [inspect.Parameter.VAR_POSITIONAL,inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.VAR_KEYWORD]
	for name, param in sig.parameters.items():
		if name == "request":
			has_request_arg = True
			continue
		if has_request_arg and (param.kind not in valid_types):
			raise ValueError("'request' parameter must be the last POSITIONAL_OR_KEYWORD type parameter in function: %s%s" % (fn.__name__, str(sig)))
		if param.kind == inspect.Parameter.VAR_KEYWORD:
			has_var_kw_arg = True
		elif param.kind == inspect.Parameter.KEYWORD_ONLY:
			has_name_kw_arg = True
			named_args.append(name)
			if param.default == inspect.Parameter.default:
				required_args.append(name)
	return tuple(has_request_arg, has_var_kw_arg, has_name_kw_arg, named_args, required_args)


# classes
class RequestHandler(object):
	"""
	parse request and check whether is valid then call raw url handler.
	"""
	def __init__(self, app, fn):
		self._app = app
		self._func = fn
		self._has_request_arg, self._has_var_kw_arg, self._has_named_kw_arg, self._named_kw_args, self._required_kw_args = parse_raw_handler(fn)

	async def __call__(self, request):
		kw = None
		if self._has_var_kw_arg or self._has_named_kw_arg:
			# if raw url handler has input parameters, the smart handler(self) must extract the input parameters from request.
			# for post method
			if request.method == "POST":
				if not request.content_type:
					# a post request must has explicit content-type.
					return web.HTTPBadRequest("Missing Content-Type.")
				content_type = request.content_type.lower()
				if content_type.startswith("application/json"):
					# json input for post request
					params = await request.json()
					if not isinstance(params, dict):
						return web.HTTPBadRequest("Json body must be object.")
					kw = params
				elif content_type.startswith("application/x-www-form-urlencoded") or content_type.startswith("multipart/form-data"):
					# form input for post request.
					params = await request.post()
					kw = dict(**params)
				else:
					# unsupport other content-type for post request
					return web.HTTPBadRequest("Unsupported Content-Type: %s" % content_type)
			# for get request
			if request.method == "GET":
				query_string = request.query_string
				if query_string:
					kw = dict()
					for k, v in parse.parse_qs(query_string):
						kw[k] = v[0]
		if kw is None:
			# extract input parameter from url.
			kw = dict(**request.match_info)
		else:
			if not self._has_var_kw_arg and self._named_kw_args:
				# if only need KEYWORD_ONLY type parameters. it can discard unknown input.
				copy = dict()
				for name in self._named_kw_args:
					if name in kw:
						copy[name] = kw[name]
				kw = copy
			for k, v in request.match_info.items():
				# extract input parameter from url.
				if k in kw:
					logging.warning("Duplicate arg name in url and kw args: %s." % name)
				kw[k] = v
		if self._has_request_arg:
			# raw url handler maybe need the raw request.
			kw["request"] = request
		# check the explicit parameters which raw url handler needs.
		if self._required_kw_args:
			for name in self._required_kw_args:
				if not name in kw:
					return web.HTTPBadRequest("Missing argument: %s" % name)
		logging.info("call with args: %s" % str(kw))
		try:
			return await self._func(**kw)
		except APIError as e:
			return dict(error = e.error, data = e.data, message = e.message)


def add_static(app):
	path = os.path.join(os.path.dirname(__file__), "static")
	app.router.add_route("/static/", path)
	logging.info("add static: %s ==> %s" % ("static", path))


def add_route(app, fn, method = None, path = None):
	if method is None:
		method = getattr(fn, "__method__", None)
	if path is None:
		path = getattr(fn, "__route__", None)
	if method is None or path is None:
		raise ValueError("@get or @post not defined in %s." % str(fn))
	if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
		fn = asyncio.coroutine(fn)
	logging.info("add route: %s %s ==> %s%s" % (method, path, fn.__name__, str(inspect.signature(fn))))
	app.router.add_route(method, path, RequestHandler(fn))


def add_routes(app, module_name):
	index = module_name.rfind(".")
	if index == (-1):
		mod = __import__(module_name, globals(), locals())
	else:
		name = module_name[index + 1:]
		mod = __import__(module_name[:index], globals(), locals(), [name])
	for attr in dir(mod):
		if attr.startswith("_"):
			continue
		fn = getattr(mod, attr)
		if callable(fn):
			method = getattr(fn, "__method__", None)
			path = getattr(fn, "__route__", None)
			if method and path:
				add_route(app, fn, method, path)