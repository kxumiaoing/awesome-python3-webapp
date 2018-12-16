#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ormapping for async webapp.
"""


import logging
import aiomysql


# functions
def log(sql, args = ()):
	logging.info("SQL: %s." % sql)


async def create_pool(loop, **kw):
	logging.info("create database connection...")
	global _pool
	_pool = await aiomysql.create_pool(
		loop = loop,
		host = kw.get("host", "localhost"),
		port = kw.get("port", 3306),
		user = kw["user"],
		password = kw["password"],
		db = kw["database"],
		charset = kw.get("charset", "utf8"),
		autocommit = kw.get("autocommit", True),
		maxsize = kw.get("maxsize", 10),
		minsize = kw.get("minsize", 1)
	)


async def select(sql, args, size = None):
	log(sql)
	async with _pool.get() as conn:
		async with conn.cursor() as cur:
			await cur.execute(sql.replace("?", "%s"), args or ())
			if size:
				rs = cur.fetchmany(size)
			else:
				rs = cur.fetchall()
			logging.info("rows returned: %s" % len(rs))
			return rs


async def execute(sql, args, autocommit = True):
	log(sql)
	async with _pool.get() as conn:
		if not autocommit:
			await conn.begin()
		try:
			async with conn.cursor() as cur:
				await cur.execute(sql.replace("?", "%s"), args or ())
				affected = cur.rowcount
				if not autocommit:
					conn.commit()
				return affected
		except BaseException as e:
			if not autocommit:
				conn.rollback()


def create_arg_string(num):
	args = list()
	for n in range(num):
		args.append("?")
	return ", ".join(args)


# classes
class Field(object):
	def __init__(self, column_name, column_type, primary_key, default):
		self.column_name = column_name
		self.column_type = column_type
		self.primary_key = primary_key
		self.default = default

	def __str__(self):
		return "<%s, %s:%s>" % (self.__class__.__name__, self.column_type, self.column_name)


class StringField(Field):
	def __init__(self, column_name = None, column_type = "varchar(100)", primary_key = False, default = None):
		super().__init__(column_name, column_type, primary_key, default)


class BooleanField(Field):
	def __init__(self, column_name = None, default = False):
		super().__init__(column_name, "boolean", False, default)


class IntegerField(Field):
	def __init__(self, column_name = None, primary_key = False, default = 0):
		super().__init__(column_name, "bigint", primary_key, default)


class FloatField(Field):
	def __init__(self, column_name = None, primary_key = False, default = 0.0):
		super().__init__(column_name, "real", primary_key, default)


class TextField(Field):
	def __init__(self, column_name = None, default = None):
		super().__init__(column_name, "text", False, default)


class ModelMetaclass(type):
	def __new__(cls, name, bases, attrs):
		if name == "Model":
			return super().__new__(cls, name, bases, attrs)
		table_name = attrs.get("__table__", None) or name
		logging.info("found model: %s (table: %s)." % (name, table_name))
		mappings = dict()
		fields = list()
		primary_key = None
		for k, v in attrs.items():
			if isinstance(v, Field):
				logging.info("	found mapping:%s ==> %s." % (k, v))
				if v.column_name is None:
					v.column_name = k
				mappings[k] = v
				if v.primary_key:
					if primary_key:
						raise AttributeError("Duplicated primary key for field: %s." % k)
					primary_key = k
				else:
					fields.append(k)
		if not primary_key:
			raise AttributeError("Primary key not found for table: %s" % table_name)
		for k in mappings:
			attrs.pop(k)
		column_list = list(map(lambda f: "%s" % mappings.get(f).column_name, fields))
		primary_column = mappings.get(primary_key).column_name
		insert_list = list(map(lambda c: "`%s`" % c, column_list))
		insert_list.append("`%s`" % primary_column)
		insert_string = ", ".join(insert_list)
		update_string = ", ".join(map(lambda r: "`%s` = ?" % r, column_list))
		select_list = list(map(lambda t: "`%s` %s" % t, zip(column_list, fields)))
		select_list.append("`%s` %s" % (primary_column, primary_key))
		select_string = ", ".join(select_list)
		attrs["__table__"] = table_name
		attrs["__mappings__"] = mappings
		attrs["__fields__"] = fields
		attrs["__primary_key__"] = primary_key
		attrs["__insert__"] = "insert into `%s`(%s) values(%s)" % (table_name, insert_string, create_arg_string(len(fields) + 1))
		attrs["__delete__"] = "delete from `%s` where `%s` = ?" % (table_name, primary_column)
		attrs["__update__"] = "update `%s` set %s where `%s` = ?" % (table_name, update_string, primary_column)
		attrs["__select__"] = "select %s from `%s`" % (select_string, table_name)
		return super().__new__(cls, name, bases, attrs)


class Model(dict, metaclass = ModelMetaclass):
	def __init__(self, **kw):
		super().__init__(**kw)

	def __setattr__(self, name, value):
		self[name] = value

	def __getattr__(self, name):
		try:
			return self[name]
		except KeyError:
			raise AttributeError("'Model' object has no attribute '%s'." % name)

	def _get_value(self, name):
		return getattr(self, name, None)

	def _get_value_or_default(self, name):
		value = getattr(self, name, None)
		if value is None:
			field = self.__mappings__[name]
			if field and field.default is not None:
				value = field.default() if callable(field.default) else field.default
				logging.info("using default value for %s:%s" % (name, str(value)))
		return value

	async def save(self):
		args = list(map(self._get_value_or_default, self.__fields__))
		args.append(self._get_value_or_default(self.__primary_key__))
		rows = await execute(self.__insert__, args)
		if rows != 1:
			logging.warning("failed to insert record: affected rows: %s." % rows)

	async def remove(self):
		rows = await execute(self.__delete__, [self._get_value(self.__primary_key__)])
		if rows != 1:
			logging.warning("failed to remove by primary key: affected rows: %s." % rows)

	async def update(self):
		args = list(map(self._get_value, self.__fields__))
		args.append(self._get_value(self.__primary_key__))
		rows = await execute(self.__update__, args)
		if rows != 1:
			logging.warning("failed to update by primary key: affected rows: %s" % rows)

	@classmethod
	async def findall(cls, args = None, **kw):
		"""
		find objects by causes.
		"""
		sql = [cls.__select__]
		where = kw.get("where", None)
		if where:
			sql.append("where")
			sql.append(where)
		order_by = kw.get("order_by", None)
		if order_by:
			sql.append("order by")
			sql.append(cls.__mappings__[order_by].column_name)
		if args is None:
			args = []
		limit = kw.get("limit", None)
		if limit:
			sql.append("limit")
			if isinstance(limit, int):
				sql.append("?")
				args.append(limit)
			elif isinstance(limit, tuple) and len(limit) == 2:
				sql.append("?, ?")
				args.extend(limit)
			else:
				raise ValueError("Invalid limit value: %s" % str(limit))
		rs = await select(" ".join(sql), args)
		if rs:
			fields = cls.__fields__.copy()
			fields.append(cls.__primary_key__)
			return [cls(**(zip(fields, r))) for r in rs]
		else:
			return None

	@classmethod
	async def find(cls, pk):
		sql = "%s where `%s` = ?" % (cls.__select__, cls.__mappings__[cls.__primary_key__].column_name)
		rs = await select(sql, [pk], 1)
		if rs:
			fields = cls.__fields__.copy()
			fields.append(cls.__primary_key__)
			return cls(**(zip(fields, rs[0])))
		else:
			return None

	@classmethod
	async def findcount(cls):
		sql = "select count(1) c from `%s`" % cls.__table__
		rs = await select(sql)
		if rs:
			return rs[0][0]
		else:
			return 0