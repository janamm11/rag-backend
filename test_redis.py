# import os
# import redis
# from dotenv import load_dotenv

# load_dotenv()

# r = redis.Redis(
#     host=os.getenv("REDIS_HOST"),
#     port=int(os.getenv("REDIS_PORT")),
#     decode_responses=True,
#     username=os.getenv("REDIS_USERNAME"),
#     password=os.getenv("REDIS_PASSWORD"),
# )

# r.set("test", "hello")   set->  stores one value. rpush -> builds a list of values., 
 # lrange-> Give me the items from index 0 to the end ...GET → get one value

# result = r.get("test")

# print(result)

# now, testing whether Redis can store multiple messages in order:
import os
import redis
from dotenv import load_dotenv

load_dotenv()

r = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    decode_responses=True,
    username=os.getenv("REDIS_USERNAME"),
    password=os.getenv("REDIS_PASSWORD"),
)

session_id = "session_123"

r.rpush(session_id, "User: Hello")
r.rpush(session_id, "AI: Hi! How can I help?")
r.rpush(session_id, "User: Tell me about internships")

messages = r.lrange(session_id, 0, -1)

print(messages)