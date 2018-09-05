import redis
import constants as c

r = redis.StrictRedis(host=c.REDIS_HOST, port=c.REDIS_PORT, db=c.REDIS_DB)


def get_key_by_chat_id(chat_id):
    key = '{prefix}:{chat_id}'.format(prefix=c.REDIS_PREFIX, chat_id=chat_id)
    return key


def get_categories_key_by_chat_id(chat_id):
    key = '{prefix}:{chat_id}:categories'.format(prefix=c.REDIS_PREFIX, chat_id=chat_id)
    return key


def get_user_data(chat_id):
    key = get_key_by_chat_id(chat_id)

    user_data = r.hgetall(key)

    return user_data


def get_user_field(chat_id, field):
    key = get_key_by_chat_id(chat_id)

    return r.hget(key, field)


def set_user_state(chat_id, state):
    key = get_key_by_chat_id(chat_id)
    field = 'state'
    value = state

    r.hset(key, field, value)


def set_user_field(chat_id, field, value):
    key = get_key_by_chat_id(chat_id)

    r.hset(key, field, value)


def update_category_id(chat_id):
    key = get_key_by_chat_id(chat_id)
    field = '__category_id'
    value_to_increment = 1

    return r.hincrby(key, field, value_to_increment)


def add_user_category(chat_id, category_name):
    key = get_categories_key_by_chat_id(chat_id)
    field = update_category_id(chat_id)
    value = category_name

    r.hset(key, field, value)


def remove_user_category(chat_id, category_id):
    key = get_categories_key_by_chat_id(chat_id)
    field = category_id

    r.hdel(key, field)


def get_user_categories(chat_id):
    key = get_categories_key_by_chat_id(chat_id)

    data = r.hgetall(key)

    return [{'id': key, 'title': value} for key, value in data.items()]
