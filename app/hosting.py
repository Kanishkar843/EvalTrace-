def database_url(value):
    if value.startswith('postgres://'):return value.replace('postgres://','postgresql+psycopg://',1)
    if value.startswith('postgresql://'):return value.replace('postgresql://','postgresql+psycopg://',1)
    return value
