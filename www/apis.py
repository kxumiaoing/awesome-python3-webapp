#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
api definitions.
"""


# classes
class APIError(Exception):
	"""
	the base APIError which contains error(required), data(optional) and message(optional).
	"""
	def __init__(self, error, data = "", message = ""):
		super().__init__(message)
		self.error = error
		self.data = data
		self.message = message


class APIValueError(APIError):
	"""
	indicate the input value has error or invalid. the data specifies the error field of input form.
	"""
	def __init__(self, error, field, message = ""):
		super().__init__("value: invalid", field, message)


class APIResourceNotFound(APIError):
	"""
	indicate the resource not found. the data specifies the resource name.
	"""
	def __init__(self, error, field, message = ""):
		super().__init__("value: notfound", field, message)


class APIPermissionError(APIError):
	"""
	indicate the api has no permission.
	"""
	def __init__(self, message = ""):
		super().__init__("permission: forbidden", "permission", message)