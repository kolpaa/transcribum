import redis.asyncio as redis
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
