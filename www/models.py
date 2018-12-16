#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
models for async webapp.
"""


import time
import uuid
from orm import Model, StringField, BooleanField, FloatField, TextField


# functions
def next_id():
	return "%015d%s00" % (int(time.time() * 1000), uuid.uuid4().hex)


# classes
class User(Model):
	__table__ = "users"

	id = StringField(column_type = "varchar(50)", primary_key = True, default = next_id)
	email = StringField(column_type = "varchar(50)")
	password = StringField(column_type = "varchar(50)")
	admin = BooleanField()
	name = StringField(column_type = "varchar(50)")
	image = StringField(column_type = "varchar(500)")
	created_at = FloatField(default = time.time)


class Blog(Model):
	__table__ = "blogs"

	id = StringField(column_type = "varchar(50)", primary_key = True, default = next_id)
	user_id = StringField(column_type = "varchar(50)")
	user_name = StringField(column_type = "varchar(50)")
	user_image = StringField(column_type = "varchar(500)")
	name = StringField(column_type = "varchar(50)")
	summary = StringField(column_type = "varchar(200)")
	content = TextField()
	created_at = FloatField(default = time.time)


class Comment(Model):
	__table__ = "comments"

	id = StringField(column_type = "varchar(50)", primary_key = True, default = next_id)
	blog_id = StringField(column_type = "varchar(50)")
	user_id = StringField(column_type = "varchar(50)")
	user_name = StringField(column_type = "varchar(50)")
	user_image = StringField(column_type = "varchar(500)")
	content = TextField()
	created_at = FloatField(default = time.time)
